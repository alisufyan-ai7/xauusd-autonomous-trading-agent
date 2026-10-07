"""Bounded end-to-end golden lifecycle slices for all five setup families.

The functions compose raw-bar primitives into advisory candidates only.  They
have no broker, network, model, filesystem, sizing, margin, or order capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Sequence

from feature_oracle import (
    Bar, breakout_bar, brt_retest, confirmation_sequence, fbr_hold_and_confirm,
    fbr_reclaim, moc_compression, moc_trigger, rejection_bar, reward_risk,
    rsr_location, select_rsr_range, tpb_zones,
)


@dataclass(frozen=True)
class SafetyState:
    data_clear: bool = True
    session_clear: bool = True
    spread_clear: bool = True
    volatility_clear: bool = True
    event_clear: bool = True
    exposure_clear: bool = True
    risk_clear: bool = True


@dataclass(frozen=True)
class GoldenCandidate:
    family: str
    direction: str
    state: str
    reason: str
    entry: Decimal | None = None
    stop: Decimal | None = None
    tp1: Decimal | None = None
    final: Decimal | None = None
    expiry_bars: int = 0


def _reject(family: str, direction: str, reason: str) -> GoldenCandidate:
    return GoldenCandidate(family, direction, "NO_TRADE", reason)


def _common(family: str, direction: str, safety: SafetyState) -> GoldenCandidate | None:
    ordered = (
        ("DATA_INVALID", safety.data_clear),
        ("SESSION_BLOCKED", safety.session_clear),
        ("SPREAD_BLOCKED", safety.spread_clear),
        ("VOLATILITY_BLOCKED", safety.volatility_clear),
        ("EVENT_BLOCKED", safety.event_clear),
        ("EXPOSURE_BLOCKED", safety.exposure_clear),
        ("RISK_BLOCKED", safety.risk_clear),
    )
    return next((_reject(family, direction, reason) for reason, clear in ordered if not clear), None)


def _confirming_bar(rejection: Bar, following: Sequence[Bar], direction: str,
                    tick_size: float) -> Bar | None:
    if not confirmation_sequence(rejection, following, direction, tick_size):
        return None
    if direction == "LONG":
        return next(bar for bar in following if bar.close >= rejection.high + tick_size)
    return next(bar for bar in following if bar.close <= rejection.low - tick_size)


def _candidate(family: str, direction: str, entry: float, stop: float,
               tp1: float, final: float, expiry_bars: int) -> GoldenCandidate:
    side = "LONG" if direction == "LONG" else "SHORT"
    entry_d, stop_d, tp1_d, final_d = map(lambda x: Decimal(str(x)), (entry, stop, tp1, final))
    rr1 = reward_risk(entry_d, stop_d, tp1_d, side)
    rrf = reward_risk(entry_d, stop_d, final_d, side)
    if rr1 is None or rrf is None or rr1 < Decimal("1.5") or rrf < Decimal("2.0"):
        return _reject(family, direction, "INSUFFICIENT_RR")
    return GoldenCandidate(family, direction, "PROPOSED", "GOLDEN_SLICE_PASS",
                           entry_d, stop_d, tp1_d, final_d, expiry_bars)


def evaluate_tpb(*, direction: str, regime: str, impulse_start: float,
                 impulse_end: float, location_level: float, level_tol: float,
                 rejection: Bar, following: Sequence[Bar], tick_size: float,
                 stop_buffer: float, tp1: float, final: float,
                 safety: SafetyState = SafetyState()) -> GoldenCandidate:
    family = "TPB"
    blocked = _common(family, direction, safety)
    if blocked:
        return blocked
    required = "UP_TREND" if direction == "LONG" else "DOWN_TREND"
    if regime != required:
        return _reject(family, direction, "REGIME_MISMATCH")
    zones = tpb_zones(impulse_start, impulse_end, direction)
    touched = [bounds for bounds in zones.values()
               if rejection.low <= bounds[1] and rejection.high >= bounds[0]
               and bounds[0] - level_tol <= location_level <= bounds[1] + level_tol]
    if len(touched) != 1:
        return _reject(family, direction, "ZONE_OR_LOCATION_INVALID")
    confirming = _confirming_bar(rejection, following, direction, tick_size)
    if confirming is None:
        return _reject(family, direction, "CONFIRMATION_MISSING")
    lower, upper = touched[0]
    if direction == "LONG":
        entry = max(confirming.close, confirming.high) + tick_size
        stop = min(rejection.low, lower) - stop_buffer
    else:
        entry = min(confirming.close, confirming.low) - tick_size
        stop = max(rejection.high, upper) + stop_buffer
    return _candidate(family, direction, entry, stop, tp1, final, 4)


def evaluate_brt(*, direction: str, regime: str, boundary: float, atr_h1: float,
                 level_tol: float, breakout: Bar, prior_bodies: Sequence[float],
                 adx_now: float, adx_five_bars_ago: float, retest_h1: Sequence[Bar],
                 rejection: Bar, following: Sequence[Bar], tick_size: float,
                 stop_buffer: float, tp1: float, final: float,
                 safety: SafetyState = SafetyState()) -> GoldenCandidate:
    family = "BRT"
    blocked = _common(family, direction, safety)
    if blocked:
        return blocked
    required = "UP_TREND" if direction == "LONG" else "DOWN_TREND"
    if regime != required:
        return _reject(family, direction, "REGIME_MISMATCH")
    if not breakout_bar(breakout, direction=direction, level=boundary, atr_h1=atr_h1,
                        prior_bodies=prior_bodies, adx_now=adx_now,
                        adx_five_bars_ago=adx_five_bars_ago):
        return _reject(family, direction, "BREAKOUT_INVALID")
    if not brt_retest(retest_h1, direction=direction, boundary=boundary,
                      level_tol=level_tol, atr_h1=atr_h1):
        return _reject(family, direction, "RETEST_INVALID")
    confirming = _confirming_bar(rejection, following, direction, tick_size)
    if confirming is None:
        return _reject(family, direction, "CONFIRMATION_MISSING")
    if direction == "LONG":
        entry, stop = confirming.high + tick_size, min(rejection.low, boundary) - stop_buffer
    else:
        entry, stop = confirming.low - tick_size, max(rejection.high, boundary) + stop_buffer
    return _candidate(family, direction, entry, stop, tp1, final, 4)


def evaluate_fbr(*, direction: str, regime: str, boundary: float, atr_h1: float,
                 atr_m15: float, tick_size: float, prior_twenty: Sequence[Bar],
                 breach_to_reclaim: Sequence[Bar], following: Sequence[Bar],
                 stop_buffer: float, tp1: float, final: float,
                 safety: SafetyState = SafetyState()) -> GoldenCandidate:
    family = "FBR"
    blocked = _common(family, direction, safety)
    if blocked:
        return blocked
    if regime not in {"RANGE", "UP_TREND", "DOWN_TREND"}:
        return _reject(family, direction, "REGIME_MISMATCH")
    median_body = median(abs(bar.close - bar.open) for bar in prior_twenty[-20:])
    if not fbr_reclaim(breach_to_reclaim, direction=direction, boundary=boundary,
                       atr_h1=atr_h1, tick_size=tick_size, median_body_20=median_body):
        return _reject(family, direction, "RECLAIM_INVALID")
    reclaim = breach_to_reclaim[-1]
    if not fbr_hold_and_confirm(reclaim, following, direction=direction,
                                boundary=boundary, atr_m15=atr_m15,
                                tick_size=tick_size):
        return _reject(family, direction, "HOLD_OR_CONFIRMATION_INVALID")
    confirming = (next(bar for bar in following if bar.close >= reclaim.high + tick_size)
                  if direction == "LONG" else
                  next(bar for bar in following if bar.close <= reclaim.low - tick_size))
    extreme = min(bar.low for bar in breach_to_reclaim) if direction == "LONG" else max(bar.high for bar in breach_to_reclaim)
    entry = confirming.high + tick_size if direction == "LONG" else confirming.low - tick_size
    stop = extreme - stop_buffer if direction == "LONG" else extreme + stop_buffer
    return _candidate(family, direction, entry, stop, tp1, final, 3)


def evaluate_rsr(*, direction: str, h1_bars: Sequence[Bar], atr_h1: float,
                 level_tol: float, rejection: Bar, following: Sequence[Bar],
                 tick_size: float, stop_buffer: float,
                 safety: SafetyState = SafetyState()) -> GoldenCandidate:
    family = "RSR"
    blocked = _common(family, direction, safety)
    if blocked:
        return blocked
    selected = select_rsr_range(h1_bars, atr_h1=atr_h1, level_tol=level_tol)
    if selected is None or not rsr_location(rejection.close, selected.lower, selected.upper, direction):
        return _reject(family, direction, "RANGE_OR_LOCATION_INVALID")
    confirming = _confirming_bar(rejection, following, direction, tick_size)
    if confirming is None:
        return _reject(family, direction, "CONFIRMATION_MISSING")
    if direction == "LONG":
        entry, stop = confirming.high + tick_size, min(rejection.low, selected.lower) - stop_buffer
        tp1, final = (selected.lower + selected.upper) / 2, selected.upper - level_tol
    else:
        entry, stop = confirming.low - tick_size, max(rejection.high, selected.upper) + stop_buffer
        tp1, final = (selected.lower + selected.upper) / 2, selected.lower + level_tol
    return _candidate(family, direction, entry, stop, tp1, final, 4)


def evaluate_moc(*, direction: str, regime: str, impulse_start: float,
                 impulse_end: float, atr_h1: float, atr_m15: float,
                 prior_twenty: Sequence[Bar], compression: Sequence[Bar],
                 trigger: Bar, rsi14: float, quote_price: float,
                 stop_buffer: float, tp1: float, final: float,
                 safety: SafetyState = SafetyState()) -> GoldenCandidate:
    family = "MOC"
    blocked = _common(family, direction, safety)
    if blocked:
        return blocked
    required = "UP_TREND" if direction == "LONG" else "DOWN_TREND"
    if regime != required:
        return _reject(family, direction, "REGIME_MISMATCH")
    if not moc_compression(compression, prior_twenty, direction=direction,
                           impulse_start=impulse_start, impulse_end=impulse_end,
                           atr_h1=atr_h1, atr_m15=atr_m15):
        return _reject(family, direction, "COMPRESSION_INVALID")
    median_body = median(abs(bar.close - bar.open) for bar in prior_twenty[-20:])
    if not moc_trigger(compression, trigger, direction=direction, atr_m15=atr_m15,
                       median_body_20=median_body, rsi14=rsi14):
        return _reject(family, direction, "TRIGGER_INVALID")
    if abs(quote_price - trigger.close) > 0.15 * atr_m15:
        return _reject(family, direction, "QUOTE_CHASE_BLOCKED")
    boundary = min(bar.low for bar in compression) if direction == "LONG" else max(bar.high for bar in compression)
    stop = boundary - stop_buffer if direction == "LONG" else boundary + stop_buffer
    return _candidate(family, direction, quote_price, stop, tp1, final, 0)
