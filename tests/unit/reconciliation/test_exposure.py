from decimal import Decimal

import pytest

from xauusd_agent.broker.observation import PositionObservation
from xauusd_agent.reconciliation.exposure import (
    ExpectedExposure,
    ReconciliationDisposition,
    ReconciliationStatus,
    reconcile_exposure,
)
from xauusd_agent.reconciliation.idempotency import (
    DecisionEnvelope,
    DecisionReservations,
    ReservationDisposition,
)
from xauusd_agent.reconciliation.ledger import ExposureLedger
from xauusd_agent.reconciliation.null_execution import NullExecutionRecord
from xauusd_agent.reconciliation.uncertainty import (
    SubmissionUncertainty,
    UncertaintyResolution,
    UncertaintyState,
)
from xauusd_agent.risk.policy_a import RiskDisposition


def test_zero_exposure_reconciles() -> None:
    result = reconcile_exposure(tuple(), tuple(), tuple())
    assert result.status is ReconciliationStatus.MATCH_ZERO
    assert result.disposition is ReconciliationDisposition.CONTINUE
    assert result.automatic_close_permitted is False


def test_unexpected_exposure_quarantines_without_close() -> None:
    position = PositionObservation("p1", "XAUUSD", "BUY", Decimal("0.01"))
    result = reconcile_exposure(tuple(), (position,), tuple())
    assert result.status is ReconciliationStatus.MISMATCH
    assert result.disposition is ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW
    assert "UNEXPECTED_BROKER_EXPOSURE" in result.reason_codes
    assert result.automatic_close_permitted is False


def test_missing_broker_snapshot_is_unknown_and_quarantines() -> None:
    result = reconcile_exposure(tuple(), None, tuple())
    assert result.status is ReconciliationStatus.UNKNOWN_EXPOSURE
    assert result.disposition is ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW


def test_known_exposure_reconciles_by_exact_identity_and_decimal_volume() -> None:
    expected = (ExpectedExposure("POSITION", "p1", "XAUUSD", "BUY", Decimal("0.01")),)
    observed = (PositionObservation("p1", "XAUUSD", "BUY", Decimal("0.01")),)
    result = reconcile_exposure(expected, observed, tuple())
    assert result.status is ReconciliationStatus.MATCH_KNOWN


def test_submission_uncertainty_cannot_retry_and_is_one_way() -> None:
    uncertainty = SubmissionUncertainty("i1", "2026-10-05T00:00:00Z", "timeout")
    assert uncertainty.retry_permitted is False
    resolved = uncertainty.reconcile(UncertaintyResolution.BROKER_ABSENT)
    assert resolved.state is UncertaintyState.RECONCILED_ABSENT
    assert resolved.retry_permitted is False
    with pytest.raises(ValueError, match="already terminal"):
        resolved.reconcile(UncertaintyResolution.BROKER_PRESENT)
    with pytest.raises(ValueError, match="automatic retry"):
        SubmissionUncertainty("i2", "2026-10-05T00:00:01Z", "timeout", retry_permitted=True)


def test_null_execution_record_enforces_absent_capability_and_zero_actions() -> None:
    record = NullExecutionRecord(
        decision_id="d1",
        decided_at_utc="2026-10-05T00:00:00Z",
        setup_id="s1",
        risk_disposition=RiskDisposition.ALLOW,
        risk_reason_codes=("ALL_FROZEN_CONTROLS_PASS",),
    )
    assert record.execution_capability == "ABSENT"
    assert record.broker_action_count == 0
    with pytest.raises(ValueError) as capability_error:
        NullExecutionRecord(
            decision_id="d2",
            decided_at_utc="2026-10-05T00:00:01Z",
            setup_id="s2",
            risk_disposition=RiskDisposition.REJECT,
            risk_reason_codes=("TEST",),
            execution_capability="PRESENT",
        )
    assert (
        str(capability_error.value)
        == "production-candidate execution capability must be absent"
    )


@pytest.mark.parametrize(
    ("decision_id", "decided_at_utc"),
    [("", "2026-10-05T00:00:00Z"), ("d1", "")],
)
def test_null_execution_record_requires_both_identity_fields(
    decision_id: str, decided_at_utc: str
) -> None:
    with pytest.raises(ValueError) as identity_error:
        NullExecutionRecord(
            decision_id=decision_id,
            decided_at_utc=decided_at_utc,
            setup_id=None,
            risk_disposition=RiskDisposition.REJECT,
            risk_reason_codes=("TEST",),
        )
    assert str(identity_error.value) == "decision identity and UTC time are required"


def test_exposure_ledger_is_deterministic_append_only_and_hash_chained() -> None:
    result = reconcile_exposure(tuple(), tuple(), tuple())
    first = ExposureLedger().record(
        observed_at_utc="2026-10-05T00:00:00Z",
        broker_fingerprint_sha256="a" * 64,
        reconciliation=result,
    )
    repeated = ExposureLedger().record(
        observed_at_utc="2026-10-05T00:00:00Z",
        broker_fingerprint_sha256="a" * 64,
        reconciliation=result,
    )
    second = first.record(
        observed_at_utc="2026-10-05T00:01:00Z",
        broker_fingerprint_sha256="a" * 64,
        reconciliation=result,
    )
    assert first.entries == repeated.entries
    assert first.verify() is True
    assert second.verify() is True
    assert first.entries[0].entry_sha256 == second.entries[1].previous_entry_sha256
    assert first.entries == second.entries[:1]


def test_idempotency_exact_replay_and_collision_are_fail_closed() -> None:
    base = DecisionEnvelope("d1", "a" * 64, "b" * 64, "c" * 64, "d" * 64)
    reservations, new = DecisionReservations().reserve(base)
    unchanged, replay = reservations.reserve(base)
    conflicting = DecisionEnvelope("d1", "e" * 64, "b" * 64, "c" * 64, "d" * 64)
    still_unchanged, conflict = reservations.reserve(conflicting)

    assert new.disposition is ReservationDisposition.NEW
    assert replay.disposition is ReservationDisposition.EXACT_REPLAY
    assert conflict.disposition is ReservationDisposition.CONFLICT_QUARANTINE
    assert unchanged == reservations == still_unchanged
    assert not new.broker_action_permitted
    assert not replay.broker_action_permitted
    assert not conflict.broker_action_permitted


def test_duplicate_broker_identity_is_invalid_not_silently_collapsed() -> None:
    duplicated = (
        PositionObservation("p1", "XAUUSD", "BUY", Decimal("0.01")),
        PositionObservation("p1", "XAUUSD", "BUY", Decimal("0.01")),
    )
    result = reconcile_exposure(tuple(), duplicated, tuple())
    assert result.status is ReconciliationStatus.INVALID_OBSERVATION
    assert result.disposition is ReconciliationDisposition.QUARANTINE_HUMAN_REVIEW
    assert result.reason_codes == ("DUPLICATE_EXPOSURE_IDENTITY",)


def test_non_decimal_observation_quarantines_instead_of_crashing() -> None:
    malformed = PositionObservation("p1", "XAUUSD", "BUY", "0.01")  # type: ignore[arg-type]
    result = reconcile_exposure(tuple(), (malformed,), tuple())
    assert result.status is ReconciliationStatus.INVALID_OBSERVATION
