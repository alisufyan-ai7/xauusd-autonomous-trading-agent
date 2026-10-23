"""Conservative OFFLINE pending STOP lifetime guard for official news/session.

A STOP order may fill any time before broker expiry. Checking Event Guard only
at placement is insufficient. This engine requires full agency admission AND
proof that the entire pending lifetime, plus uncertainty margin, avoids each
protected event's pre/post lock. No network/MT5 operations and NO order permit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from xauusd_agent.guards.v2_official_source_gate import (
    VerifiedOfficialSnapshot,
    admit_official_calendar,
)

MAX_PENDING = timedelta(minutes=60)
EXPIRY_SETTLEMENT_MARGIN = timedelta(minutes=1)
_EVENT_LOCK_MINUTES = {
    "TIER_1": (30, 30),
    "TIER_2": (15, 15),
}


@dataclass(frozen=True, slots=True)
class PendingEntryWindowScreen:
    allowed_to_proceed_to_other_gates: bool
    reasons: tuple[str, ...]
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("pending news/session screen is not an order permit")


def screen_pending_entry_window(
    *,
    now: datetime,
    expires_utc: datetime,
    session_verified_through_utc: datetime | None,
    snapshots: tuple[VerifiedOfficialSnapshot, ...],
    shock_locked: bool | None,
    normalized: bool | None,
) -> PendingEntryWindowScreen:
    """Reject unknown/moved/stale/news-overlapping STOP expiry horizon.

    The session_verified_through_utc timestamp MUST be sourced from an
    independently validated broker/official schedule; a future timestamp or
    fake snapshot made by a caller does NOT satisfy source authenticity.
    """
    def reject(reason: str) -> PendingEntryWindowScreen:
        return PendingEntryWindowScreen(False, (reason,))

    for instant in (now, expires_utc):
        if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
            return reject("PENDING_WINDOW_NON_UTC_CLOCK")
    if not now < expires_utc or expires_utc - now > MAX_PENDING:
        return reject("PENDING_WINDOW_INVALID_DURATION")
    if (
        session_verified_through_utc is None
        or session_verified_through_utc.tzinfo is None
        or session_verified_through_utc.utcoffset() != timedelta(0)
        or session_verified_through_utc
        < expires_utc + EXPIRY_SETTLEMENT_MARGIN
    ):
        return reject("PENDING_WINDOW_SESSION_BOUNDARY_UNVERIFIED")
    try:
        admitted = admit_official_calendar(
            observed_at=now,
            snapshots=snapshots,
            shock_locked=shock_locked,
            normalized=normalized,
        )
    except (TypeError, ValueError):
        return reject("PENDING_WINDOW_EVENT_SOURCE_MALFORMED")
    if not admitted.admitted:
        return PendingEntryWindowScreen(
            False, ("PENDING_WINDOW_EVENT_ADMISSION_DENIED", *admitted.reasons)
        )
    all_events = admitted.observation.events
    if all_events is None:
        return reject("PENDING_WINDOW_NO_EVENT_INVENTORY")
    broker_active_through = expires_utc + EXPIRY_SETTLEMENT_MARGIN
    for event in all_events:
        if event.status == "CANCELLED":
            continue
        minutes = _EVENT_LOCK_MINUTES.get(event.tier)
        if minutes is None:
            return reject("PENDING_WINDOW_UNKNOWN_EVENT_TIER")
        pre, post = minutes
        lock_start = event.scheduled_utc - timedelta(minutes=pre)
        lock_end = event.scheduled_utc + timedelta(minutes=post)
        if now < lock_end and broker_active_through > lock_start:
            return PendingEntryWindowScreen(
                False,
                ("PENDING_WINDOW_OVERLAPS_OFFICIAL_EVENT", event.event_id),
            )
    return PendingEntryWindowScreen(True, ())
