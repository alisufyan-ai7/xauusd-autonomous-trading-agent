"""Experimental, pure H1/M15 XAUUSD advisory candidate; NEVER an execution permit.

This source has no MT5, broker, account, scheduling, model or order interface.
Its output is a strategy hypothesis for testing, not a proven trading edge.
"""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from xauusd_agent.market.models import Bar, Timeframe


class AdvisoryDisposition(StrEnum):
    NO_TRADE = "NO_TRADE"
    CANDIDATE = "CANDIDATE"


class AdvisorySide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class AutonomousDemoAdvisory:
    disposition: AdvisoryDisposition
    reason: str
    side: AdvisorySide | None = None
    reference_entry: Decimal | None = None
    reference_stop: Decimal | None = None
    reference_tp1: Decimal | None = None
    reference_target: Decimal | None = None
    signal_id: str | None = None
    trigger_time_utc: datetime | None = None
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("advisory source can never permit broker execution")
        if self.disposition is AdvisoryDisposition.NO_TRADE and any(
            x is not None for x in (
                self.side, self.reference_entry, self.reference_stop,
                self.reference_tp1, self.reference_target, self.signal_id,
            )
        ):
            raise ValueError("NO_TRADE must not expose executable price parameters")


def _valid_bars(bars: Sequence[Bar], timeframe: Timeframe, now: datetime) -> bool:
    if not bars or any(bar.symbol != "XAUUSD" or bar.timeframe is not timeframe for bar in bars):
        return False
    if any(not bar.is_completed_at(now) for bar in bars):
        return False
    if any(a.open_time >= b.open_time for a, b in zip(bars, bars[1:], strict=False)):
        return False
    # Last windows must be continuous: do not trade into reopened/stale gaps.
    window = 5 if timeframe is Timeframe.H1 else 16
    if len(bars) < window:
        return False
    if any(b.open_time - a.open_time != timeframe.duration
           for a, b in zip(bars[-window:], bars[-window + 1:], strict=False)):
        return False
    return now - bars[-1].close_time <= timeframe.duration


def _ema_last(values: Sequence[Decimal], period: int) -> Decimal:
    current = sum(values[:period], Decimal(0)) / Decimal(period)
    alpha = Decimal(2) / Decimal(period + 1)
    for item in values[period:]:
        current = alpha * item + (Decimal(1) - alpha) * current
    return current


def advise_h1_m15(
    *, h1: Sequence[Bar], m15: Sequence[Bar], observed_at: datetime,
    tick_size: Decimal,
) -> AutonomousDemoAdvisory:
    """Produce one shadow-only momentum proposal from closed bars, otherwise NO_TRADE.

    Experimental fixed-rule baseline: EMA20/EMA50 H1 trend plus a *completed*
    M15 12-bar extreme break; stop at six-bar adverse extreme with 2-tick buffer.
    No broker quote, cost, policy-A, shock or event admission is performed here.
    """
    def blocked(reason: str) -> AutonomousDemoAdvisory:
        return AutonomousDemoAdvisory(AdvisoryDisposition.NO_TRADE, reason)
    if observed_at.tzinfo is None or observed_at.utcoffset() != timedelta(0):
        return blocked("DECISION_TIME_NOT_UTC")
    if tick_size <= 0 or not tick_size.is_finite():
        return blocked("INVALID_TICK_SIZE")
    if len(h1) < 55 or len(m15) < 24:
        return blocked("INSUFFICIENT_COMPLETE_BARS")
    if not _valid_bars(h1, Timeframe.H1, observed_at):
        return blocked("H1_INVALID_OR_STALE")
    if not _valid_bars(m15, Timeframe.M15, observed_at):
        return blocked("M15_INVALID_OR_STALE")
    # Both observations must describe broadly the same XAUUSD price regime.
    if abs(h1[-1].close - m15[-1].close) / h1[-1].close > Decimal("0.02"):
        return blocked("TIMEFRAME_PRICE_DIVERGENCE")
    close = [bar.close for bar in h1]
    fast = _ema_last(close, 20)
    slow = _ema_last(close, 50)
    trigger = m15[-1]
    prior = m15[-13:-1]
    top = max(b.high for b in prior)
    bottom = min(b.low for b in prior)
    width = trigger.high - trigger.low
    if width <= 0:
        return blocked("TRIGGER_BAR_NO_RANGE")
    body_fraction = abs(trigger.close - trigger.open) / width
    if body_fraction < Decimal("0.55"):
        return blocked("TRIGGER_BODY_INSUFFICIENT")
    side: AdvisorySide
    if fast > slow and h1[-1].close > fast and trigger.close > top + tick_size:
        if trigger.close <= trigger.open:
            return blocked("LONG_TRIGGER_NOT_BULLISH")
        side = AdvisorySide.LONG
        stop = min(b.low for b in m15[-6:]) - tick_size * 2
        distance = trigger.close - stop
    elif fast < slow and h1[-1].close < fast and trigger.close < bottom - tick_size:
        if trigger.close >= trigger.open:
            return blocked("SHORT_TRIGGER_NOT_BEARISH")
        side = AdvisorySide.SHORT
        stop = max(b.high for b in m15[-6:]) + tick_size * 2
        distance = stop - trigger.close
    else:
        return blocked("NO_ALIGNED_H1_TREND_M15_BREAKOUT")
    # 0.01 lot / $10k example cap is not a broker risk acceptance.
    if distance <= 2 * tick_size or distance > Decimal("12.00"):
        return blocked("REFERENCE_STOP_GEOMETRY_OUT_OF_BOUNDS")
    entry = trigger.close
    if any(price % tick_size != 0 for price in (entry, stop)):
        return blocked("REFERENCE_LEVEL_OFF_TICK_GRID")
    signed = Decimal(1) if side is AdvisorySide.LONG else Decimal(-1)
    signal_key = (
        f"shadow-advisory-v0.1|XAUUSD|{side.value}|"
        f"{h1[-1].open_time.isoformat()}|{trigger.open_time.isoformat()}|"
        f"{entry}|{stop}"
    )
    return AutonomousDemoAdvisory(
        disposition=AdvisoryDisposition.CANDIDATE,
        reason="EXPERIMENTAL_CLOSED_BAR_SHADOW_PROPOSAL_ONLY",
        side=side,
        reference_entry=entry,
        reference_stop=stop,
        reference_tp1=entry + signed * Decimal("1.5") * distance,
        reference_target=entry + signed * Decimal(2) * distance,
        signal_id=hashlib.sha256(signal_key.encode("ascii")).hexdigest(),
        trigger_time_utc=trigger.close_time.astimezone(UTC),
    )
