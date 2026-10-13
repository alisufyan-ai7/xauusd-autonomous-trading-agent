from __future__ import annotations

from datetime import UTC, datetime, timedelta

from xauusd_agent.guards import (
    EventGuardState,
    EventObservation,
    ProtectedEvent,
    evaluate_event_guard,
)

EVENT_TIME = datetime(2026, 10, 8, 12, 30, tzinfo=UTC)
EVENT = ProtectedEvent("bls-cpi", EVENT_TIME, "TIER_1")


def observation(now: datetime, **overrides) -> EventObservation:
    arguments = {
        "observed_utc": now,
        "events": (EVENT,),
        "source_healthy": True,
        "sources_agree": True,
        "coverage_complete": True,
        "shock_locked": False,
        "normalized": True,
    }
    arguments.update(overrides)
    return EventObservation(**arguments)


def test_frozen_tier_one_boundaries_are_half_open_and_deterministic() -> None:
    assert (
        evaluate_event_guard(observation(EVENT_TIME - timedelta(minutes=31))).state
        is EventGuardState.HEALTHY
    )
    assert (
        evaluate_event_guard(observation(EVENT_TIME - timedelta(minutes=30))).state
        is EventGuardState.PRE_LOCK
    )
    assert evaluate_event_guard(observation(EVENT_TIME)).state is EventGuardState.EVENT_ACTIVE
    assert (
        evaluate_event_guard(observation(EVENT_TIME + timedelta(seconds=1))).state
        is EventGuardState.POST_LOCK
    )
    assert (
        evaluate_event_guard(observation(EVENT_TIME + timedelta(minutes=30))).state
        is EventGuardState.HEALTHY
    )


def test_missing_health_or_inventory_is_unknown() -> None:
    missing = evaluate_event_guard(observation(EVENT_TIME, source_healthy=None))
    assert missing.state is EventGuardState.UNKNOWN
    assert missing.reasons == ("SOURCE_HEALTH_UNKNOWN",)
    inventory = evaluate_event_guard(observation(EVENT_TIME, events=None))
    assert inventory.state is EventGuardState.UNKNOWN


def test_disagreement_uncertain_event_and_shock_all_block() -> None:
    disagreement = evaluate_event_guard(observation(EVENT_TIME, sources_agree=False))
    assert disagreement.state is EventGuardState.SOURCE_UNHEALTHY
    shock = evaluate_event_guard(observation(EVENT_TIME, shock_locked=True))
    assert shock.state is EventGuardState.SHOCK_LOCK
    tentative = ProtectedEvent("fed-tentative", EVENT_TIME, "TIER_2", "TENTATIVE")
    uncertain = evaluate_event_guard(observation(EVENT_TIME, events=(tentative,)))
    assert uncertain.state is EventGuardState.SOURCE_UNHEALTHY
    assert uncertain.blocking_event_ids == ("fed-tentative",)


def test_normalization_pending_survives_nominal_window() -> None:
    decision = evaluate_event_guard(
        observation(EVENT_TIME + timedelta(minutes=30), normalized=False)
    )
    assert decision.state is EventGuardState.NORMALIZATION_PENDING
    assert not decision.entry_allowed
