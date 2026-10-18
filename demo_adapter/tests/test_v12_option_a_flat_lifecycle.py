"""Offline tests: no new risk without owner-attended flat BEFORE overlap end."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from scripts.v12_option_a_flat_lifecycle import (
    FlatBeforeEndSafetyError,
    FlatProof,
    FlatSessionContract,
    review_candidate_entry,
    verify_flat_before_boundary,
)

START = datetime(2026, 10, 20, 12, 30, tzinfo=UTC)
OVERLAP = START + timedelta(hours=1)
END = START + timedelta(hours=4)


def contract() -> FlatSessionContract:
    return FlatSessionContract(
        observation_start_utc=START,
        observation_end_utc=END,
        entry_overlap_start_utc=OVERLAP,
        entry_overlap_end_utc=END,
        broker_eligible_end_utc=END + timedelta(minutes=30),
        flat_reconciliation_lead_seconds=300,
        maximum_planned_position_lifetime_seconds=600,
        anticipated_exit_reconciliation_seconds=120,
    )


def proof() -> FlatProof:
    return FlatProof(
        observed_utc=END - timedelta(minutes=6),
        positions_count=0, pending_orders_count=0,
        cashflow_journal_reconciled=True,
        owned_exposure_attributed=True, broker_identity_reconfirmed=True,
        fresh_source_verified=True, new_entry_locked=True,
        human_owner_exit_supervision_confirmed=True,
    )


def allow(now: datetime, c: FlatSessionContract | None = None) -> object:
    return review_candidate_entry(
        c or contract(), now_utc=now,
        broker_account_and_orders_confirmed_zero=True,
        runtime_guard_and_full_policy_a_verified=True,
        owner_attendance_and_exit_plan_verified=True,
    )


def test_synthetic_eligible_entry_reserves_full_holding_and_exit_budget() -> None:
    out = allow(OVERLAP + timedelta(minutes=10))
    assert out.trading_authorized is False
    assert out.hard_flat_confirmation_deadline_utc == END - timedelta(minutes=5)
    assert out.latest_permitted_entry_utc == END - timedelta(minutes=17)
    assert "NO_DEMO_ENTRY_AUTHORITY" in out.disposition


def test_boundary_is_strict_not_an_excuse_to_hold_into_overlap_end() -> None:
    c = contract()
    with pytest.raises(FlatBeforeEndSafetyError, match="safe exit budget"):
        allow(END - timedelta(minutes=17), c)
    with pytest.raises(FlatBeforeEndSafetyError, match="safe exit budget"):
        allow(END - timedelta(minutes=2), c)
    with pytest.raises(FlatBeforeEndSafetyError, match="safe exit budget"):
        allow(START + timedelta(minutes=2), c)


def test_earlier_broker_end_shortens_flat_cutoff() -> None:
    c = replace(contract(), broker_eligible_end_utc=END - timedelta(minutes=30))
    out = allow(OVERLAP + timedelta(minutes=1), c)
    assert out.hard_flat_confirmation_deadline_utc == END - timedelta(minutes=35)


def test_unknown_broker_positions_and_pending_fail_closed() -> None:
    c = contract()
    for bad in (None, 1, -1):
        with pytest.raises(FlatBeforeEndSafetyError, match="exposure"):
            verify_flat_before_boundary(c, replace(proof(), positions_count=bad))
        with pytest.raises(FlatBeforeEndSafetyError, match="exposure"):
            verify_flat_before_boundary(c, replace(proof(), pending_orders_count=bad))


def test_valid_flat_proof_must_be_timeboxed_and_owner_attended() -> None:
    out = verify_flat_before_boundary(contract(), proof())
    assert "SYNTHETIC_FLATNESS_REVIEW_ONLY" in out


def test_late_zero_exposure_does_not_rewrite_original_deadline() -> None:
    late = replace(proof(), observed_utc=END - timedelta(minutes=4))
    with pytest.raises(FlatBeforeEndSafetyError, match="exit deadline"):
        verify_flat_before_boundary(contract(), late)


@pytest.mark.parametrize(("name", "value"), [
    ("cashflow_journal_reconciled", False),
    ("owned_exposure_attributed", False),
    ("broker_identity_reconfirmed", False),
    ("fresh_source_verified", False),
    ("new_entry_locked", False),
    ("human_owner_exit_supervision_confirmed", False),
])
def test_unverified_flat_proof_quarantines(name: str, value: bool) -> None:
    with pytest.raises(FlatBeforeEndSafetyError, match="unreconciled"):
        verify_flat_before_boundary(contract(), replace(proof(), **{name: value}))


def test_missing_attended_exit_or_full_policy_a_denies_entry() -> None:
    for controls in [
        (False, True, True), (True, False, True), (True, True, False),
    ]:
        with pytest.raises(FlatBeforeEndSafetyError, match="quarantine"):
            review_candidate_entry(
                contract(), now_utc=OVERLAP + timedelta(minutes=20),
                broker_account_and_orders_confirmed_zero=controls[0],
                runtime_guard_and_full_policy_a_verified=controls[1],
                owner_attendance_and_exit_plan_verified=controls[2],
            )


def test_missing_positive_position_lifetime_and_exit_lead_fails_closed() -> None:
    for field in (
        "flat_reconciliation_lead_seconds",
        "maximum_planned_position_lifetime_seconds",
        "anticipated_exit_reconciliation_seconds",
    ):
        with pytest.raises(FlatBeforeEndSafetyError, match="positive"):
            allow(OVERLAP, replace(contract(), **{field: 0}))


def test_overnight_and_rollover_entry_not_possible_via_wrong_session() -> None:
    bad = replace(
        contract(), broker_eligible_end_utc=OVERLAP + timedelta(seconds=2)
    )
    with pytest.raises(FlatBeforeEndSafetyError, match="safe owner-attended entry"):
        allow(OVERLAP, bad)


def test_no_broker_capability_in_flat_evaluator() -> None:
    import inspect

    from scripts import v12_option_a_flat_lifecycle

    source = inspect.getsource(v12_option_a_flat_lifecycle)
    for forbidden in (
        "import MetaTrader5", "order_send(", "order_check(", "order_close(",
        "initialize(", "shutdown(", "subprocess.", "socket.",
    ):
        assert forbidden not in source
