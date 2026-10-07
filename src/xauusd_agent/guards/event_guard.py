"""Pure Event Guard over supplied, already-captured official-source observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from xauusd_agent.market.models import _require_utc


class EventGuardState(StrEnum):
    HEALTHY = "HEALTHY"
    PRE_LOCK = "PRE_LOCK"
    EVENT_ACTIVE = "EVENT_ACTIVE"
    POST_LOCK = "POST_LOCK"
    NORMALIZATION_PENDING = "NORMALIZATION_PENDING"
    SHOCK_LOCK = "SHOCK_LOCK"
    SOURCE_UNHEALTHY = "SOURCE_UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ProtectedEvent:
    event_id: str
    scheduled_utc: datetime
    tier: str
    status: str = "SCHEDULED"

    def __post_init__(self) -> None:
        _require_utc(self.scheduled_utc, "scheduled_utc")
        if not self.event_id:
            raise ValueError("event_id is required")
        if self.tier not in {"TIER_1", "TIER_2"}:
            raise ValueError("unknown event tier")
        if self.status not in {"SCHEDULED", "CANCELLED", "SUSPENDED", "TENTATIVE"}:
            raise ValueError("unknown event status")


@dataclass(frozen=True, slots=True)
class EventObservation:
    observed_utc: datetime
    events: tuple[ProtectedEvent, ...] | None
    source_healthy: bool | None
    sources_agree: bool | None
    coverage_complete: bool | None
    shock_locked: bool | None
    normalized: bool | None

    def __post_init__(self) -> None:
        _require_utc(self.observed_utc, "observed_utc")
        if self.events is not None:
            object.__setattr__(self, "events", tuple(self.events))


@dataclass(frozen=True, slots=True)
class EventGuardDecision:
    state: EventGuardState
    reasons: tuple[str, ...]
    blocking_event_ids: tuple[str, ...] = ()

    @property
    def entry_allowed(self) -> bool:
        return self.state is EventGuardState.HEALTHY


_WINDOWS = {
    "TIER_1": (timedelta(minutes=30), timedelta(minutes=30)),
    "TIER_2": (timedelta(minutes=15), timedelta(minutes=15)),
}


def evaluate_event_guard(observation: EventObservation) -> EventGuardDecision:
    if observation.events is None:
        return EventGuardDecision(EventGuardState.UNKNOWN, ("EVENT_INVENTORY_MISSING",))
    incomplete = []
    for name, value in (
        ("SOURCE_HEALTH_UNKNOWN", observation.source_healthy),
        ("SOURCE_AGREEMENT_UNKNOWN", observation.sources_agree),
        ("COVERAGE_UNKNOWN", observation.coverage_complete),
        ("SHOCK_STATE_UNKNOWN", observation.shock_locked),
        ("NORMALIZATION_UNKNOWN", observation.normalized),
    ):
        if value is None:
            incomplete.append(name)
    if incomplete:
        return EventGuardDecision(EventGuardState.UNKNOWN, tuple(incomplete))
    if observation.source_healthy is not True:
        return EventGuardDecision(EventGuardState.SOURCE_UNHEALTHY, ("SOURCE_UNHEALTHY",))
    if observation.sources_agree is not True:
        return EventGuardDecision(EventGuardState.SOURCE_UNHEALTHY, ("SOURCE_DISAGREEMENT",))
    if observation.coverage_complete is not True:
        return EventGuardDecision(EventGuardState.SOURCE_UNHEALTHY, ("COVERAGE_INCOMPLETE",))
    if observation.shock_locked is True:
        return EventGuardDecision(EventGuardState.SHOCK_LOCK, ("SHOCK_LOCK",))
    uncertain = tuple(
        sorted(
            event.event_id
            for event in observation.events
            if event.status in {"TENTATIVE", "SUSPENDED"}
        )
    )
    if uncertain:
        return EventGuardDecision(
            EventGuardState.SOURCE_UNHEALTHY,
            ("EVENT_TIME_UNCERTAIN",),
            uncertain,
        )
    active: list[tuple[EventGuardState, str]] = []
    for event in observation.events:
        if event.status == "CANCELLED":
            continue
        pre, post = _WINDOWS[event.tier]
        start, end = event.scheduled_utc - pre, event.scheduled_utc + post
        now = observation.observed_utc
        if start <= now < event.scheduled_utc:
            active.append((EventGuardState.PRE_LOCK, event.event_id))
        elif now == event.scheduled_utc:
            active.append((EventGuardState.EVENT_ACTIVE, event.event_id))
        elif event.scheduled_utc < now < end:
            active.append((EventGuardState.POST_LOCK, event.event_id))
        elif now >= end and observation.normalized is not True:
            active.append((EventGuardState.NORMALIZATION_PENDING, event.event_id))
    if active:
        priority = {
            EventGuardState.EVENT_ACTIVE: 0,
            EventGuardState.PRE_LOCK: 1,
            EventGuardState.POST_LOCK: 2,
            EventGuardState.NORMALIZATION_PENDING: 3,
        }
        chosen = min((state for state, _ in active), key=priority.__getitem__)
        identifiers = tuple(sorted(event_id for state, event_id in active if state is chosen))
        return EventGuardDecision(chosen, (chosen.value,), identifiers)
    return EventGuardDecision(EventGuardState.HEALTHY, ())
