"""Causal TPB research detection from completed H4/H1/M15 candles.

This is a *technical research hypothesis*, not frozen P0-SETUPS-001
acceptance: broker cost/spread, all swing-location alternatives, first-touch
tracking, every cancellation rule and full historical replay still need
independent implementation/evidence. All outputs are SHADOW ONLY; never
turn this result directly into a broker order.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from statistics import median

from xauusd_agent.features.indicators import adx, atr, confirmed_swings, ema
from xauusd_agent.features.v2_market_context import (
    ContextBar,
    ContextStatus,
    ContextTimeframe,
    MarketContextReview,
)
from xauusd_agent.market.models import Bar, Timeframe


class TPBResearchStatus(StrEnum):
    NO_TRADE = "NO_TRADE"
    TECHNICAL_HYPOTHESIS = "TECHNICAL_HYPOTHESIS"


@dataclass(frozen=True, slots=True)
class TPBResearchFinding:
    status: TPBResearchStatus
    reason: str
    direction: str | None = None
    entry: Decimal | None = None
    stop: Decimal | None = None
    tp1: Decimal | None = None
    target: Decimal | None = None
    hypothesis_id: str | None = None
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("TPB research has no execution capability")
        if self.status is TPBResearchStatus.NO_TRADE and any(
            x is not None for x in (
                self.direction, self.entry, self.stop, self.tp1,
                self.target, self.hypothesis_id,
            )
        ):
            raise ValueError("NO_TRADE contains no actionable levels")


def _old_bars(
    frames: Mapping[ContextTimeframe, Sequence[ContextBar]],
    timeframe: ContextTimeframe,
) -> tuple[Bar, ...]:
    older = {
        ContextTimeframe.H4: Timeframe.H4,
        ContextTimeframe.H1: Timeframe.H1,
        ContextTimeframe.M15: Timeframe.M15,
    }[timeframe]
    return tuple(
        Bar(
            symbol=bar.symbol, timeframe=older, open_time=bar.open_time,
            open=bar.open, high=bar.high, low=bar.low,
            close=bar.close, tick_volume=bar.tick_volume,
        )
        for bar in frames.get(timeframe, ())
    )


def _last(values: Sequence[Decimal | None]) -> Decimal | None:
    return values[-1] if values else None


def detect_tpb_research(
    *, context: MarketContextReview,
    frames: Mapping[ContextTimeframe, Sequence[ContextBar]],
    tick_size: Decimal,
) -> TPBResearchFinding:
    """Detect a strictly bounded TPB subcase using only completed bar facts.

    Does not represent a full frozen strategy, risk PASS or Event Guard PASS.
    Full eligibility requires the independent Phase0 setup evaluator.
    """
    def reject(reason: str) -> TPBResearchFinding:
        return TPBResearchFinding(TPBResearchStatus.NO_TRADE, reason)

    if context.status is not ContextStatus.CONTEXT_READY:
        return reject("CONTEXT_NOT_READY")
    if not tick_size.is_finite() or tick_size <= 0:
        return reject("INVALID_TICK_SIZE")
    h4, h1, m15 = (
        _old_bars(frames, ContextTimeframe.H4),
        _old_bars(frames, ContextTimeframe.H1),
        _old_bars(frames, ContextTimeframe.M15),
    )
    # Frozen required warmups; the context reviewer has smaller engineering
    # minimums and is NOT a substitute for this strategy requirement.
    if len(h4) < 300 or len(h1) < 500 or len(m15) < 1_000:
        return reject("FROZEN_STRATEGY_WARMUP_INSUFFICIENT")
    if any(b.close_time > context.observed_at for b in (h4[-1], h1[-1], m15[-1])):
        return reject("FORMING_BAR")
    if any(
        earlier.open_time >= later.open_time
        for series in (h4, h1, m15)
        for earlier, later in zip(series, series[1:], strict=False)
    ):
        return reject("BAR_ORDER_INVALID")

    atr_h1 = atr(h1)
    atr_m15 = atr(m15)
    latest_h1_atr, latest_m15_atr = _last(atr_h1), _last(atr_m15)
    if (
        latest_h1_atr is None or latest_h1_atr <= 0
        or latest_m15_atr is None or latest_m15_atr <= 0
    ):
        return reject("ATR_UNAVAILABLE")
    previous_atr = [value for value in atr_h1[-101:-1] if value is not None]
    if len(previous_atr) < 100:
        return reject("ATR_HISTORY_INCOMPLETE")
    if latest_h1_atr >= Decimal("1.80") * median(previous_atr):
        return reject("HIGH_VOLATILITY_REGIME")

    fast = ema([b.close for b in h4], 20)
    slow = ema([b.close for b in h4], 50)
    strength, plus_di, minus_di = adx(h4)
    if any(
        x is None for x in (
            fast[-1], fast[-6], slow[-1], strength[-1],
            plus_di[-1], minus_di[-1],
        )
    ):
        return reject("H4_TREND_UNAVAILABLE")
    ef = fast[-1]
    es = slow[-1]
    ad = strength[-1]
    plus = plus_di[-1]
    minus = minus_di[-1]
    assert ef is not None and es is not None and ad is not None
    assert plus is not None and minus is not None and fast[-6] is not None
    if ad < Decimal("20"):
        return reject("H4_ADX_INSUFFICIENT")
    if ef > es and ef > fast[-6] and plus > minus:
        direction, sign = "LONG", Decimal(1)
    elif ef < es and ef < fast[-6] and plus < minus:
        direction, sign = "SHORT", Decimal(-1)
    else:
        return reject("NO_H4_TREND")

    structure = h1[-120:]
    highs, lows = confirmed_swings(structure)
    if len(highs) < 2 or len(lows) < 2:
        return reject("H1_CONFIRMED_SWINGS_MISSING")
    tolerance = max(tick_size * 3, latest_h1_atr * Decimal("0.10"))
    high_new, high_old = structure[highs[-1]].high, structure[highs[-2]].high
    low_new, low_old = structure[lows[-1]].low, structure[lows[-2]].low
    if direction == "LONG" and not (
        high_new > high_old + tolerance and low_new > low_old + tolerance
    ):
        return reject("UPTREND_STRUCTURE_NOT_CONFIRMED")
    if direction == "SHORT" and not (
        high_new < high_old - tolerance and low_new < low_old - tolerance
    ):
        return reject("DOWNTREND_STRUCTURE_NOT_CONFIRMED")

    # Only use a completed, strictly confirmed directional H1 impulse.
    last_index = highs[-1] if direction == "LONG" else lows[-1]
    anchors = lows if direction == "LONG" else highs
    prior = [idx for idx in anchors if idx < last_index]
    if not prior:
        return reject("IMPULSE_ORIGIN_MISSING")
    origin_index = prior[-1]
    duration = last_index - origin_index
    if not 3 <= duration <= 24:
        return reject("IMPULSE_DURATION_INVALID")
    if direction == "LONG":
        origin, extreme = structure[origin_index].low, structure[last_index].high
    else:
        origin, extreme = structure[origin_index].high, structure[last_index].low
    travel = abs(extreme - origin)
    if travel < Decimal("1.5") * latest_h1_atr:
        return reject("IMPULSE_MAGNITUDE_INSUFFICIENT")
    closes = [b.close for b in structure[origin_index:last_index + 1]]
    traversed = sum(
        (abs(a - z) for a, z in zip(closes, closes[1:], strict=False)),
        Decimal(0),
    )
    if traversed <= 0 or travel / traversed < Decimal("0.45"):
        return reject("IMPULSE_EFFICIENCY_INSUFFICIENT")
    if direction == "LONG" and any(
        b.close < origin - tolerance
        for b in structure[origin_index:last_index + 1]
    ):
        return reject("ORIGIN_INVALIDATED")
    if direction == "SHORT" and any(
        b.close > origin + tolerance
        for b in structure[origin_index:last_index + 1]
    ):
        return reject("ORIGIN_INVALIDATED")

    # Restrict this first research variant to Zone A with H1 EMA20
    # confluence. Zone B, original first-touch accounting and other
    # independently valid H1 structural levels remain unimplemented.
    ema_h1 = ema([b.close for b in h1], 20)[-1]
    if ema_h1 is None:
        return reject("H1_EMA_UNAVAILABLE")
    zone_a = extreme - sign * travel * Decimal("0.382")
    zone_b = extreme - sign * travel * Decimal("0.500")
    zone_low, zone_high = min(zone_a, zone_b), max(zone_a, zone_b)
    if not zone_low - tolerance <= ema_h1 <= zone_high + tolerance:
        return reject("ZONE_A_NO_EMA_CONFLUENCE")

    recent = m15[-4:]
    trigger = recent[-1]
    rejection = recent[-2]
    if not (zone_low <= rejection.low <= zone_high or
            zone_low <= rejection.high <= zone_high):
        return reject("ZONE_A_REJECTION_NOT_AT_LOCATION")
    width = rejection.high - rejection.low
    if width <= 0:
        return reject("M15_REJECTION_ZERO_RANGE")
    body = abs(rejection.close - rejection.open)
    if direction == "LONG":
        wick = min(rejection.close, rejection.open) - rejection.low
        location = (rejection.close - rejection.low) / width
        confirmation = trigger.close > rejection.high + tick_size
        entry = max(trigger.close, trigger.high) + tick_size
        stop = min(rejection.low, zone_low) - max(tick_size * 3, latest_m15_atr / 4)
    else:
        wick = rejection.high - max(rejection.close, rejection.open)
        location = (rejection.high - rejection.close) / width
        confirmation = trigger.close < rejection.low - tick_size
        entry = min(trigger.close, trigger.low) - tick_size
        stop = max(rejection.high, zone_high) + max(tick_size * 3, latest_m15_atr / 4)
    if wick < body or location < Decimal("0.65") or not confirmation:
        return reject("M15_REJECTION_AND_CONFIRMATION_MISSING")
    risk = sign * (entry - stop)
    tp1 = extreme
    target = origin + sign * travel * Decimal("1.272")
    if risk <= 0 or sign * (tp1 - entry) < risk * Decimal("1.5"):
        return reject("TP1_REWARD_RISK_INSUFFICIENT")
    if sign * (target - entry) < risk * Decimal(2):
        return reject("FINAL_REWARD_RISK_INSUFFICIENT")
    if risk < max(3 * tick_size, latest_m15_atr / 4) or risk > 2 * latest_h1_atr:
        return reject("REFERENCE_STOP_DISTANCE_INVALID")
    # Reference prices are intentionally not MT5 executable prices; do not
    # round or submit them without the broker's admitted tick/stop/cost maths.
    identifying = (
        "v2-tpb-research-zone-a|"
        f"{direction}|{structure[origin_index].open_time.isoformat()}|"
        f"{structure[last_index].open_time.isoformat()}|"
        f"{trigger.open_time.isoformat()}|{entry}|{stop}"
    )
    return TPBResearchFinding(
        TPBResearchStatus.TECHNICAL_HYPOTHESIS,
        "UNQUALIFIED_TPB_ZONE_A_RESEARCH_ONLY",
        direction=direction,
        entry=entry,
        stop=stop,
        tp1=tp1,
        target=target,
        hypothesis_id=hashlib.sha256(identifying.encode("ascii")).hexdigest(),
    )
