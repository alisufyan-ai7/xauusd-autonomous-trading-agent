"""Execution-disabled v2 multi-timeframe market context.

Pure data and deterministic NO_TRADE checks. No MT5, OpenAI, network, file,
order, risk, or account operations exist in this module. Does NOT admit
strategy, Event Guard sources, costs, broker risk, or any execution.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from xauusd_agent.market.models import Bar, Quote, Timeframe, _require_utc


class ContextTimeframe(StrEnum):
    W1 = "W1"
    D1 = "D1"
    H4 = "H4"
    H1 = "H1"
    M15 = "M15"
    M5 = "M5"
    M1 = "M1"

    @property
    def duration(self) -> timedelta:
        return {
            ContextTimeframe.W1: timedelta(days=7),
            ContextTimeframe.D1: timedelta(days=1),
            ContextTimeframe.H4: timedelta(hours=4),
            ContextTimeframe.H1: timedelta(hours=1),
            ContextTimeframe.M15: timedelta(minutes=15),
            ContextTimeframe.M5: timedelta(minutes=5),
            ContextTimeframe.M1: timedelta(minutes=1),
        }[self]


# These are conservative engineering *context* warmups, NOT the formal
# Phase0 strategy's 300 H4 / 500 H1 / 1000 M15 eligibility requirement.
_CONTEXT_MIN_BARS = {
    ContextTimeframe.W1: 2,
    ContextTimeframe.D1: 5,
    ContextTimeframe.H4: 8,
    ContextTimeframe.H1: 12,
    ContextTimeframe.M15: 12,
    ContextTimeframe.M5: 12,
    ContextTimeframe.M1: 15,
}
_MAX_AGE = {
    ContextTimeframe.W1: timedelta(days=14),
    ContextTimeframe.D1: timedelta(days=4),
    ContextTimeframe.H4: timedelta(hours=12),
    ContextTimeframe.H1: timedelta(hours=3),
    ContextTimeframe.M15: timedelta(minutes=45),
    ContextTimeframe.M5: timedelta(minutes=15),
    ContextTimeframe.M1: timedelta(minutes=4),
}


@dataclass(frozen=True, slots=True)
class ContextBar:
    timeframe: ContextTimeframe
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    tick_volume: int
    symbol: str = "XAUUSD"

    def __post_init__(self) -> None:
        _require_utc(self.open_time, "bar.open_time")
        if self.symbol != "XAUUSD":
            raise ValueError("context bar requires XAUUSD")
        if not all(
            x.is_finite() and x > 0
            for x in (self.open, self.high, self.low, self.close)
        ):
            raise ValueError("bar prices must be finite and positive")
        if self.high < max(self.open, self.close) or self.low > min(
            self.open, self.close
        ):
            raise ValueError("OHLC is inconsistent")
        if self.tick_volume < 0:
            raise ValueError("tick volume must be non-negative")

    @property
    def close_time(self) -> datetime:
        return self.open_time + self.timeframe.duration


def from_existing_core_bar(bar: Bar) -> ContextBar:
    """Convert the existing H4/H1/M15 read-only model without re-fetching data.

    W1/D1/M5/M1 are intentionally not invented: a new independently verified
    broker observation adapter must supply those exact completed bars later.
    """
    equivalents = {
        Timeframe.H4: ContextTimeframe.H4,
        Timeframe.H1: ContextTimeframe.H1,
        Timeframe.M15: ContextTimeframe.M15,
    }
    return ContextBar(
        timeframe=equivalents[bar.timeframe],
        open_time=bar.open_time,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        tick_volume=bar.tick_volume,
        symbol=bar.symbol,
    )


class ContextStatus(StrEnum):
    NO_TRADE = "NO_TRADE"
    CONTEXT_READY = "CONTEXT_READY"


@dataclass(frozen=True, slots=True)
class MarketContextReview:
    status: ContextStatus
    observed_at: datetime
    reasons: tuple[str, ...]
    required_timeframes: tuple[ContextTimeframe, ...]
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("context can never authorize execution")
        if self.status is ContextStatus.CONTEXT_READY and self.reasons:
            raise ValueError("ready context may not have rejection reasons")


def review_market_context(
    *,
    bars: Mapping[ContextTimeframe, Sequence[ContextBar]],
    quote: Quote | None,
    observed_at: datetime,
    session_clear: bool | None,
    event_clear: bool | None,
    shock_clear: bool | None,
    broker_health_clear: bool | None,
) -> MarketContextReview:
    """Preflight all seven views without granting any trading permission.

    Session/event/shock/health boolean flags MUST come from separate,
    independently verified guards; callers may not infer True from a clock.
    Close-time validation forbids using still-forming bars. Weekend and
    trading-session eligibility remain independent, and unqualified signals
    still require separate setup, broker-risk and owner admission.
    """
    _require_utc(observed_at, "observed_at")
    reasons: list[str] = []
    required = tuple(ContextTimeframe)

    for name, status in (
        ("SESSION", session_clear),
        ("EVENT", event_clear),
        ("SHOCK", shock_clear),
        ("BROKER_HEALTH", broker_health_clear),
    ):
        if status is not True:
            reasons.append(f"{name}_UNKNOWN_OR_BLOCKED")
    if set(bars) != set(required):
        reasons.append("TIMEFRAME_SET_INCOMPLETE")
    for timeframe in required:
        series = bars.get(timeframe, ())
        if len(series) < _CONTEXT_MIN_BARS[timeframe]:
            reasons.append(f"{timeframe.value}_INSUFFICIENT_BARS")
            continue
        if any(b.timeframe is not timeframe or b.symbol != "XAUUSD" for b in series):
            reasons.append(f"{timeframe.value}_MISMATCHED_BAR")
            continue
        # Reject duplicates, out-of-order data and overlapping bar intervals.
        if any(
            earlier.open_time >= later.open_time
            or earlier.close_time > later.open_time
            for earlier, later in zip(series, series[1:], strict=False)
        ):
            reasons.append(f"{timeframe.value}_UNSORTED_OR_OVERLAPPING")
            continue
        if any(b.close_time > observed_at for b in series):
            reasons.append(f"{timeframe.value}_INCOMPLETE_FUTURE_BAR")
            continue
        last_age = observed_at - series[-1].close_time
        if last_age < timedelta(0) or last_age > _MAX_AGE[timeframe]:
            reasons.append(f"{timeframe.value}_STALE")
        # The microstructure windows must be contiguous: gaps cannot be
        # treated as evidence of intraday market structure.
        if timeframe in (
            ContextTimeframe.M1,
            ContextTimeframe.M5,
            ContextTimeframe.M15,
        ) and any(
            b.open_time - a.open_time != timeframe.duration
            for a, b in zip(series[-4:-1], series[-3:], strict=True)
        ):
            reasons.append(f"{timeframe.value}_RECENT_GAP")

    if quote is None:
        reasons.append("QUOTE_UNKNOWN")
    else:
        if quote.symbol != "XAUUSD":
            reasons.append("QUOTE_SYMBOL_MISMATCH")
        if (
            quote.broker_time > observed_at
            or quote.received_time > observed_at
            or quote.received_time < quote.broker_time
            or observed_at - quote.broker_time > timedelta(seconds=5)
        ):
            reasons.append("QUOTE_STALE_OR_CLOCK_CONFLICT")
        micro = bars.get(ContextTimeframe.M1, ())
        if micro and micro[-1].close > 0:
            if abs(quote.midpoint - micro[-1].close) / micro[-1].close > Decimal("0.02"):
                reasons.append("QUOTE_M1_PRICE_DIVERGENCE")

    return MarketContextReview(
        status=ContextStatus.NO_TRADE if reasons else ContextStatus.CONTEXT_READY,
        observed_at=observed_at,
        reasons=tuple(sorted(set(reasons))),
        required_timeframes=required,
    )
