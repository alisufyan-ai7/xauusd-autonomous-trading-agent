"""Fail-closed official-source event normalization, strictly offline.

Actual fetch/parsing/rights and observed-availability evidence must precede
creation of VerifiedOfficialSnapshot. No live calendar data or paid API is
accessed here. Existing Event Guard remains authoritative over entry locks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from xauusd_agent.guards.event_guard import (
    EventObservation,
    ProtectedEvent,
    evaluate_event_guard,
)
from xauusd_agent.market.models import _require_utc

_AGENCY_DOMAINS = {
    "BLS": "bls.gov",
    "BEA": "bea.gov",
    "FED": "federalreserve.gov",
    "CENSUS": "census.gov",
    "DOL": "dol.gov",
}
_REQUIRED = frozenset(_AGENCY_DOMAINS)


@dataclass(frozen=True, slots=True)
class VerifiedOfficialSnapshot:
    agency: str
    source_host: str
    raw_sha256: str
    parser_version: str
    captured_utc: datetime
    valid_through_utc: datetime
    event_horizon_utc: datetime
    rights_for_local_processing_verified: bool
    parser_schema_verified: bool
    authoritative_release_coverage_verified: bool
    revision_conflicts_absent: bool
    events: tuple[ProtectedEvent, ...]

    def __post_init__(self) -> None:
        _require_utc(self.captured_utc, "captured_utc")
        _require_utc(self.valid_through_utc, "valid_through_utc")
        _require_utc(self.event_horizon_utc, "event_horizon_utc")
        if self.agency not in _AGENCY_DOMAINS:
            raise ValueError("agency not in frozen official allowlist")
        allowed = _AGENCY_DOMAINS[self.agency]
        if not (
            self.source_host == allowed
            or self.source_host.endswith("." + allowed)
        ):
            raise ValueError("source is not on the official agency domain")
        if len(self.raw_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.raw_sha256
        ):
            raise ValueError("exact raw source hash required")
        if not self.parser_version or self.valid_through_utc < self.captured_utc:
            raise ValueError("invalid source parser/validity window")
        if len({x.event_id for x in self.events}) != len(self.events):
            raise ValueError("duplicate official event IDs")


def checked_new_york_release_time(local: datetime) -> datetime:
    """Reject nonexistent/ambiguous DST clocks, never guess UTC offsets."""
    if local.tzinfo is not None:
        raise ValueError("local release time must be naive agency wall clock")
    ny = ZoneInfo("America/New_York")
    a = local.replace(tzinfo=ny, fold=0)
    b = local.replace(tzinfo=ny, fold=1)
    if a.utcoffset() != b.utcoffset():
        raise ValueError("ambiguous or nonexistent DST release time")
    utc = a.astimezone(UTC)
    if utc.astimezone(ny).replace(tzinfo=None) != local:
        raise ValueError("invalid local release time")
    return utc


@dataclass(frozen=True, slots=True)
class OfficialEventAdmission:
    admitted: bool
    reasons: tuple[str, ...]
    observation: EventObservation
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("official event admission grants no broker authority")


def admit_official_calendar(
    *,
    observed_at: datetime,
    snapshots: tuple[VerifiedOfficialSnapshot, ...],
    shock_locked: bool | None,
    normalized: bool | None,
) -> OfficialEventAdmission:
    _require_utc(observed_at, "observed_at")
    reasons = []
    if {s.agency for s in snapshots} != _REQUIRED:
        reasons.append("OFFICIAL_AGENCY_COVERAGE_INCOMPLETE")
    if len(snapshots) != len({s.agency for s in snapshots}):
        reasons.append("DUPLICATE_AGENCY_SNAPSHOT")
    all_events: list[ProtectedEvent] = []
    for snap in snapshots:
        if (
            not snap.rights_for_local_processing_verified
            or not snap.parser_schema_verified
            or not snap.authoritative_release_coverage_verified
            or not snap.revision_conflicts_absent
        ):
            reasons.append(f"{snap.agency}_SOURCE_UNVERIFIED")
        if snap.captured_utc > observed_at or snap.valid_through_utc < observed_at:
            reasons.append(f"{snap.agency}_STALE_OR_FUTURE_CAPTURE")
        if snap.event_horizon_utc < observed_at + timedelta(hours=48):
            reasons.append(f"{snap.agency}_HORIZON_INCOMPLETE")
        all_events.extend(snap.events)
    if len({x.event_id for x in all_events}) != len(all_events):
        reasons.append("CROSS_AGENCY_EVENT_ID_COLLISION")
    observation = EventObservation(
        observed_utc=observed_at,
        events=tuple(all_events) if not reasons else None,
        source_healthy=not reasons,
        sources_agree=not reasons,
        coverage_complete=not reasons,
        shock_locked=shock_locked,
        normalized=normalized,
    )
    decision = evaluate_event_guard(observation)
    if not decision.entry_allowed:
        reasons.append("DETERMINISTIC_EVENT_LOCK:" + decision.state.value)
    return OfficialEventAdmission(not reasons, tuple(sorted(set(reasons))), observation)
