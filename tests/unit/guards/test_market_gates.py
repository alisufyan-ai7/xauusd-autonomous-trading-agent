from __future__ import annotations

from datetime import UTC, datetime

from xauusd_agent.guards import (
    GateDecision,
    GateState,
    SessionObservation,
    ShockObservation,
    combine_gates,
    evaluate_session_gate,
    evaluate_shock_gate,
)

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def session(**overrides) -> SessionObservation:
    values = {
        "observed_utc": NOW,
        "schedule_current": True,
        "weekly_boundary_known": True,
        "holiday_override_known": True,
        "scheduled_open": True,
        "broker_reports_open": True,
        "seconds_to_break": 3_600,
        "required_buffer_seconds": 900,
    }
    values.update(overrides)
    return SessionObservation(**values)


def shock(**overrides) -> ShockObservation:
    values = {
        "observed_utc": NOW,
        "calibration_available": True,
        "quote_fresh": True,
        "metric_complete": True,
        "shock_detected": False,
        "normalized": True,
        "normalization_samples": 3,
    }
    values.update(overrides)
    return ShockObservation(**values)


def test_session_and_holiday_evidence_must_be_complete() -> None:
    assert evaluate_session_gate(session()).state is GateState.CLEAR
    incomplete = evaluate_session_gate(session(holiday_override_known=None))
    assert incomplete.state is GateState.UNKNOWN
    closed = evaluate_session_gate(session(scheduled_open=False, broker_reports_open=False))
    assert closed.state is GateState.LOCK
    disagree = evaluate_session_gate(session(broker_reports_open=False))
    assert disagree.state is GateState.LOCK


def test_shock_lock_and_three_sample_normalization_are_fail_closed() -> None:
    assert evaluate_shock_gate(shock()).state is GateState.CLEAR
    assert evaluate_shock_gate(shock(calibration_available=None)).state is GateState.UNKNOWN
    assert evaluate_shock_gate(shock(shock_detected=True)).state is GateState.LOCK
    pending = evaluate_shock_gate(shock(normalized=False, normalization_samples=2))
    assert pending == GateDecision(GateState.LOCK, ("NORMALIZATION_PENDING",))


def test_combined_gate_precedence_is_lock_then_unknown_then_clear() -> None:
    clear = GateDecision(GateState.CLEAR, ())
    unknown = GateDecision(GateState.UNKNOWN, ("MISSING",))
    locked = GateDecision(GateState.LOCK, ("BLOCK",))
    assert combine_gates([clear, unknown]).state is GateState.UNKNOWN
    combined = combine_gates([unknown, locked])
    assert combined.state is GateState.LOCK
    assert combined.reasons == ("MISSING", "BLOCK")
    assert combine_gates([]).state is GateState.UNKNOWN
