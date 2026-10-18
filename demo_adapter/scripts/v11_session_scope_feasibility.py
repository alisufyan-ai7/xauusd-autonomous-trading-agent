"""OFFLINE ONLY: published center-hour feasibility and proposed evidence scope.

The source window labels are not instrument-specific Exness trading permission,
broker liquidity attestations, live Event Guard clearance or trade permits.
No network/MT5/file IO. Frozen v1.1 execution guard is NOT modified.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class CenterInterval:
    start_utc: datetime
    end_utc: datetime

    def __post_init__(self) -> None:
        if (
            self.start_utc.tzinfo is None
            or self.end_utc.tzinfo is None
            or self.start_utc.utcoffset() != timedelta(0)
            or self.end_utc.utcoffset() != timedelta(0)
            or self.end_utc <= self.start_utc
        ):
            raise ValueError("center interval not valid UTC")

    @property
    def duration_minutes(self) -> int:
        seconds = (self.end_utc - self.start_utc).total_seconds()
        if seconds % 60:
            raise ValueError("non-minute-aligned center interval")
        return int(seconds // 60)


@dataclass(frozen=True)
class SessionComparison:
    season: str
    published_overlap: CenterInterval
    published_overlap_minutes: int
    four_hours_fully_inside_published_overlap_possible: bool
    proposed_observation: CenterInterval
    proposed_observation_contains_entire_overlap: bool
    minutes_of_observation_inside_published_overlap: int
    proposed_entry_regime: str
    external_source_verified: bool
    owner_session_scope_amendment_adopted: bool
    trading_or_capture_authorized: bool


def _interval(date: str, beginning: str, ending: str) -> CenterInterval:
    a = datetime.fromisoformat(f"{date}T{beginning}:00+00:00")
    b = datetime.fromisoformat(f"{date}T{ending}:00+00:00")
    return CenterInterval(a.astimezone(UTC), b.astimezone(UTC))


def intersection(a: CenterInterval, b: CenterInterval) -> CenterInterval | None:
    start = max(a.start_utc, b.start_utc)
    end = min(a.end_utc, b.end_utc)
    return CenterInterval(start, end) if start < end else None


def published_exness_center_comparison(
    date: str, season: str
) -> SessionComparison:
    """Mechanical comparison of literal Exness public generic center table.

    Dates identify only the comparison day. They do NOT verify an applicable
    instrument-specific schedule or Event Guard on that date.
    """
    if season == "US_SUMMER":
        london = _interval(date, "08:00", "16:30")
        new_york = _interval(date, "13:30", "20:00")
        proposed = _interval(date, "12:30", "16:30")
    elif season == "US_WINTER":
        london = _interval(date, "08:00", "16:30")
        new_york = _interval(date, "14:30", "21:00")
        proposed = _interval(date, "12:30", "16:30")
    else:
        raise ValueError("unrecognized published Exness season")
    overlap = intersection(london, new_york)
    if overlap is None:
        raise ValueError("no published trading-center overlap")
    part = intersection(proposed, overlap)
    inside = 0 if part is None else part.duration_minutes
    return SessionComparison(
        season=season,
        published_overlap=overlap,
        published_overlap_minutes=overlap.duration_minutes,
        four_hours_fully_inside_published_overlap_possible=(
            overlap.duration_minutes >= 240
        ),
        proposed_observation=proposed,
        proposed_observation_contains_entire_overlap=(
            proposed.start_utc <= overlap.start_utc
            and overlap.end_utc <= proposed.end_utc
        ),
        minutes_of_observation_inside_published_overlap=inside,
        proposed_entry_regime="OVERLAP_ONLY_WITH_FUTURE_INSTRUMENT_AND_EVENT_GUARDS",
        external_source_verified=False,
        owner_session_scope_amendment_adopted=False,
        trading_or_capture_authorized=False,
    )
