"""Prospective seven-frame causality/session audit; no broker or execution.

W1 MT5 bars on the admitted Exness profile start Sunday UTC. 7-day
nominal bar boundaries are NOT Friday last-trade times. Never infer an open
session from a UTC clock or fabricate missing holiday bars. Calendar coverage
must be independently sourced and verified for an actual admission.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe
from xauusd_agent.market.models import _require_utc


@dataclass(frozen=True, slots=True)
class SessionInterval:
    start_utc: datetime
    end_utc: datetime

    def __post_init__(self) -> None:
        _require_utc(self.start_utc, "start_utc")
        _require_utc(self.end_utc, "end_utc")
        if self.end_utc <= self.start_utc:
            raise ValueError("session interval requires positive duration")


@dataclass(frozen=True, slots=True)
class SessionCalendarEvidence:
    broker_session_source_sha256: str
    revision: str
    coverage_start_utc: datetime
    coverage_end_utc: datetime
    open_intervals: tuple[SessionInterval, ...]
    source_verified: bool
    weekly_sunday_utc_anchor_verified: bool

    def __post_init__(self) -> None:
        _require_utc(self.coverage_start_utc, "coverage_start_utc")
        _require_utc(self.coverage_end_utc, "coverage_end_utc")
        if self.coverage_end_utc <= self.coverage_start_utc:
            raise ValueError("calendar coverage invalid")
        if not self.revision.strip():
            raise ValueError("calendar revision required")
        if (
            len(self.broker_session_source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.broker_session_source_sha256)
        ):
            raise ValueError("source SHA-256 required")
        if any(
            a.end_utc > z.start_utc for a, z in zip(
                self.open_intervals, self.open_intervals[1:], strict=False
            )
        ):
            raise ValueError("session intervals overlap or are unsorted")
        if any(
            window.start_utc < self.coverage_start_utc
            or window.end_utc > self.coverage_end_utc
            for window in self.open_intervals
        ):
            raise ValueError("session intervals outside declared coverage")


@dataclass(frozen=True, slots=True)
class ChronologyVerdict:
    accepted: bool
    reasons: tuple[str, ...]
    reviewed_frames: int
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("calendar audit never grants execution")


def _fully_open(
    start: datetime, end: datetime, intervals: Sequence[SessionInterval]
) -> bool:
    return any(i.start_utc <= start and end <= i.end_utc for i in intervals)


def audit_seven_frame_chronology(
    *,
    frames: Mapping[ContextTimeframe, Sequence[ContextBar]],
    as_of: datetime,
    calendar: SessionCalendarEvidence | None,
) -> ChronologyVerdict:
    _require_utc(as_of, "as_of")
    reasons: set[str] = set()
    if calendar is None or not calendar.source_verified:
        reasons.add("OFFICIAL_BROKER_SESSION_SOURCE_UNVERIFIED")
    if calendar is None or not calendar.weekly_sunday_utc_anchor_verified:
        reasons.add("W1_ANCHOR_UNVERIFIED")
    if set(frames) != set(ContextTimeframe):
        reasons.add("SEVEN_FRAME_INCOMPLETE")
    inspected = 0
    for tf in ContextTimeframe:
        series = frames.get(tf, ())
        if not series:
            reasons.add(f"{tf.value}_MISSING")
            continue
        inspected += 1
        if any(x.timeframe != tf or x.symbol != "XAUUSD" for x in series):
            reasons.add(f"{tf.value}_IDENTITY_MISMATCH")
            continue
        if any(
            z.open_time <= a.open_time for a, z in zip(
                series, series[1:], strict=False
            )
        ):
            reasons.add(f"{tf.value}_NOT_STRICTLY_ORDERED")
            continue
        if any(bar.close_time > as_of for bar in series):
            reasons.add(f"{tf.value}_FUTURE_OR_FORMING")
        if calendar is not None:
            if (
                series[0].open_time < calendar.coverage_start_utc
                or series[-1].close_time > calendar.coverage_end_utc
            ):
                reasons.add(f"{tf.value}_CALENDAR_COVERAGE_INSUFFICIENT")
        if tf is ContextTimeframe.W1:
            # A Sunday 00:00 UTC weekly anchor is *observed*, not a
            # claim that the market actually trades on Sundays at 00:00.
            if any(
                x.open_time.weekday() != 6
                or x.open_time.hour != 0
                or x.open_time.minute != 0
                or x.open_time.second != 0
                for x in series
            ):
                reasons.add("W1_BROKER_ANCHOR_CONFLICT")
        for left, right in zip(series, series[1:], strict=False):
            if right.open_time - left.open_time < tf.duration:
                reasons.add(f"{tf.value}_OVERLAP")
                break
            if right.open_time - left.open_time == tf.duration:
                continue
            # W1 is a broker-defined Sunday-to-Sunday logical bucket,
            # never require the weekend itself to be an open session.
            if tf is ContextTimeframe.W1:
                reasons.add("W1_MISSING_LOGICAL_WEEK")
                break
            missing_time = left.open_time + tf.duration
            while missing_time < right.open_time:
                if calendar is None or not calendar.source_verified:
                    reasons.add(f"{tf.value}_GAP_UNCLASSIFIED")
                    break
                if _fully_open(
                    missing_time, missing_time + tf.duration, calendar.open_intervals
                ):
                    reasons.add(f"{tf.value}_MISSING_WHILE_SESSION_OPEN")
                    break
                missing_time += tf.duration
    return ChronologyVerdict(
        accepted=not reasons,
        reasons=tuple(sorted(reasons)),
        reviewed_frames=inspected,
    )
