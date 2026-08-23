"""Offline controlled-evidence oracle for Event Guard source transitions.

The module consumes only normalized Event objects and hash-only source metadata.
It never reads raw source bodies, performs network access, or imports trading APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

from event_guard_oracle import Event, guard_state, parse_dol_ui_schedule_html
from source_conformance import (
    conservative_revision_events,
    coverage_inventory,
    revision_delta,
)

UTC = timezone.utc
SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class SafeFrame:
    """Publishable transition metadata compatible with private-capture summaries."""

    observed_utc: datetime
    source: str
    record_sha256: str
    source_healthy: bool
    events: tuple[Event, ...]

    def __post_init__(self) -> None:
        if self.observed_utc.tzinfo is None:
            raise ValueError("observed_utc must be timezone-aware")
        if not SHA256.fullmatch(self.record_sha256):
            raise ValueError("record_sha256 must be a lowercase SHA-256 digest")
        if any(event.source != self.source for event in self.events):
            raise ValueError("frame contains an event from another source")


@dataclass(frozen=True)
class TransitionEvidence:
    status: str
    reason: str
    revision_kinds: tuple[str, ...]
    effective_events: tuple[Event, ...]
    digest_sha256: str


def _digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def evaluate_transition(previous: SafeFrame, current: SafeFrame) -> TransitionEvidence:
    """Evaluate an append-only transition and retain conservative moved windows."""
    if previous.source != current.source:
        raise ValueError("source changed across transition")
    if current.observed_utc <= previous.observed_utc:
        raise ValueError("observations must be strictly chronological")

    healthy_revision, revisions = revision_delta(
        list(previous.events), list(current.events), current.observed_utc
    )
    effective = tuple(conservative_revision_events(
        list(previous.events), list(current.events), current.observed_utc
    ))
    kinds = tuple(sorted(item.kind for item in revisions))

    if not current.source_healthy:
        status, reason = "LOCKED", "SOURCE_UNHEALTHY"
    elif not healthy_revision:
        status, reason = "LOCKED", "UNEXPLAINED_REVISION"
    else:
        status, reason = "ADMISSIBLE", "TRANSITION_CONFORMING"

    digest = _digest({
        "previous_record_sha256": previous.record_sha256,
        "current_record_sha256": current.record_sha256,
        "observed_utc": current.observed_utc.astimezone(UTC).isoformat(),
        "source": current.source,
        "source_healthy": current.source_healthy,
        "revision_kinds": kinds,
        "effective": [
            (event.source_id, event.scheduled_utc.isoformat(), event.status)
            for event in effective
        ],
        "status": status,
        "reason": reason,
    })
    return TransitionEvidence(status, reason, kinds, effective, digest)


def decision_state(frame: SafeFrame, now: datetime, *, shock_locked: bool = False,
                   normalized: bool = True) -> str:
    """Apply the Event Guard to one safe frame; outage always wins."""
    return guard_state(
        now, list(frame.events), source_healthy=frame.source_healthy,
        shock_locked=shock_locked, normalized=normalized,
    )


def recovery_is_complete(now: datetime, frames: tuple[SafeFrame, ...],
                         all_events: tuple[Event, ...]) -> tuple[bool, str]:
    """A fetch recovery is insufficient until all frozen horizons are covered."""
    healthy_sources = {frame.source for frame in frames if frame.source_healthy}
    coverage_ok, _ = coverage_inventory(now, list(all_events), healthy_sources)
    if not all(frame.source_healthy for frame in frames):
        return False, "SOURCE_UNHEALTHY"
    if not coverage_ok:
        return False, "HORIZON_INCOMPLETE"
    return True, "RECOVERY_CONFORMING"


def dol_holiday_events(html: str, now: datetime, horizon_days: int = 92) -> tuple[Event, ...]:
    """Expose the production DOL parser for a controlled holiday replay."""
    return tuple(parse_dol_ui_schedule_html(html, now, horizon_days=horizon_days))
