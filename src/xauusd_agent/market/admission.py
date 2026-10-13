"""Fail-closed admission of one coherent, completed market information set."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType

from .models import UTC_EPOCH, Bar, Quote, Timeframe, _require_utc


class AdmissionState(StrEnum):
    READY = "READY"
    UNKNOWN = "UNKNOWN"
    LOCK = "LOCK"


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    state: AdmissionState
    reasons: tuple[str, ...]

    @property
    def admitted(self) -> bool:
        return self.state is AdmissionState.READY


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    quote_max_age: timedelta = timedelta(seconds=2)
    quote_future_tolerance: timedelta = timedelta(milliseconds=250)
    broker_clock_tolerance: timedelta = timedelta(seconds=5)
    completed_bar_delay: timedelta = timedelta(seconds=30)
    minima: Mapping[Timeframe, int] | None = None

    def __post_init__(self) -> None:
        minima = self.minima or {
            Timeframe.H4: 300,
            Timeframe.H1: 500,
            Timeframe.M15: 1_000,
        }
        if any(value <= 0 for value in minima.values()) or set(minima) != set(Timeframe):
            raise ValueError("minima must define positive counts for H4, H1, and M15")
        if min(
            self.quote_max_age,
            self.quote_future_tolerance,
            self.broker_clock_tolerance,
            self.completed_bar_delay,
        ) < timedelta(0):
            raise ValueError("admission durations cannot be negative")
        object.__setattr__(self, "minima", MappingProxyType(dict(minima)))


DEFAULT_ADMISSION_POLICY = AdmissionPolicy()


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    decision_time: datetime
    quote: Quote | None
    bars: Mapping[Timeframe, tuple[Bar, ...]]
    known_breaks: Mapping[Timeframe, frozenset[tuple[datetime, datetime]]]
    account_symbol_known: bool | None
    precision_known: bool | None
    session_state_known: bool | None

    def __post_init__(self) -> None:
        _require_utc(self.decision_time, "decision_time")
        object.__setattr__(
            self,
            "bars",
            MappingProxyType({key: tuple(value) for key, value in self.bars.items()}),
        )
        object.__setattr__(
            self,
            "known_breaks",
            MappingProxyType({key: frozenset(value) for key, value in self.known_breaks.items()}),
        )


def _series_reasons(
    bars: Sequence[Bar],
    *,
    timeframe: Timeframe,
    decision_time: datetime,
    minimum: int,
    known_breaks: frozenset[tuple[datetime, datetime]],
    completed_bar_delay: timedelta,
) -> list[str]:
    prefix = timeframe.value
    reasons: list[str] = []
    if len(bars) < minimum:
        reasons.append(f"{prefix}_WARMUP_MISSING")
    previous: Bar | None = None
    for bar in bars:
        if bar.timeframe is not timeframe or bar.symbol != "XAUUSD":
            reasons.append(f"{prefix}_IDENTITY_MISMATCH")
            continue
        elapsed = bar.open_time - UTC_EPOCH
        if elapsed % timeframe.duration != timedelta(0):
            reasons.append(f"{prefix}_BAR_TIME_MISALIGNED")
        if not bar.is_completed_at(decision_time):
            reasons.append(f"{prefix}_FORMING_BAR_PRESENT")
        if previous is not None:
            if bar.open_time <= previous.open_time:
                reasons.append(f"{prefix}_TIMESTAMP_NONMONOTONIC")
            elif (
                bar.open_time != previous.close_time
                and (previous.close_time, bar.open_time) not in known_breaks
            ):
                reasons.append(f"{prefix}_UNEXPLAINED_GAP")
        previous = bar
    if bars:
        elapsed = decision_time - UTC_EPOCH
        periods = elapsed // timeframe.duration
        expected_latest_close = UTC_EPOCH + periods * timeframe.duration
        if expected_latest_close > decision_time:
            expected_latest_close -= timeframe.duration
        if bars[-1].close_time != expected_latest_close:
            missing_interval = (bars[-1].close_time, expected_latest_close)
            if missing_interval not in known_breaks:
                reasons.append(f"{prefix}_LATEST_COMPLETED_BAR_MISSING")
        if (
            timeframe is Timeframe.M15
            and decision_time - expected_latest_close > completed_bar_delay
        ):
            reasons.append("M15_DECISION_WINDOW_MISSED")
    return reasons


def admit_market_snapshot(
    snapshot: MarketSnapshot, policy: AdmissionPolicy = DEFAULT_ADMISSION_POLICY
) -> AdmissionDecision:
    """Return READY only when every frozen input prerequisite is demonstrably present."""
    reasons: list[str] = []
    unknown = False
    for field, value in (
        ("ACCOUNT_SYMBOL_UNKNOWN", snapshot.account_symbol_known),
        ("PRICE_PRECISION_UNKNOWN", snapshot.precision_known),
        ("SESSION_STATE_UNKNOWN", snapshot.session_state_known),
    ):
        if value is not True:
            reasons.append(field)
            unknown = True

    quote = snapshot.quote
    if quote is None:
        reasons.append("QUOTE_MISSING")
        unknown = True
    else:
        age = snapshot.decision_time - quote.received_time
        if age > policy.quote_max_age:
            reasons.append("QUOTE_STALE")
        if age < -policy.quote_future_tolerance:
            reasons.append("QUOTE_FUTURE_DATED")
        if abs(quote.received_time - quote.broker_time) > policy.broker_clock_tolerance:
            reasons.append("QUOTE_CLOCK_INCOHERENT")

    assert policy.minima is not None
    for timeframe in Timeframe:
        series = snapshot.bars.get(timeframe)
        if series is None:
            reasons.append(f"{timeframe.value}_SERIES_MISSING")
            unknown = True
            continue
        reasons.extend(
            _series_reasons(
                series,
                timeframe=timeframe,
                decision_time=snapshot.decision_time,
                minimum=policy.minima[timeframe],
                known_breaks=snapshot.known_breaks.get(timeframe, frozenset()),
                completed_bar_delay=policy.completed_bar_delay,
            )
        )

    if not reasons:
        return AdmissionDecision(AdmissionState.READY, ())
    state = AdmissionState.UNKNOWN if unknown else AdmissionState.LOCK
    return AdmissionDecision(state, tuple(dict.fromkeys(reasons)))
