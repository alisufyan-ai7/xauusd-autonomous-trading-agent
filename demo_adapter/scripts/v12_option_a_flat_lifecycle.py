"""Pure offline INITIAL-DEMO-ADMIT flat-before-session-end rules.

No MT5 module, no order submission, no automatic close, no owner permit.
Human-attended exit plans and actual broker flatness need later approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


class FlatBeforeEndSafetyError(ValueError):
    """Unknown exposure/deadline => DENY/QUARANTINE, not emergency auto-close."""


@dataclass(frozen=True, slots=True)
class FlatSessionContract:
    observation_start_utc: datetime
    observation_end_utc: datetime
    entry_overlap_start_utc: datetime
    entry_overlap_end_utc: datetime
    broker_eligible_end_utc: datetime
    # Must be separately justified and owner-frozen before any demo activation.
    flat_reconciliation_lead_seconds: int
    maximum_planned_position_lifetime_seconds: int
    anticipated_exit_reconciliation_seconds: int


@dataclass(frozen=True, slots=True)
class PreEntryReview:
    disposition: str
    latest_permitted_entry_utc: datetime
    hard_flat_confirmation_deadline_utc: datetime
    trading_authorized: bool = False


@dataclass(frozen=True, slots=True)
class FlatProof:
    observed_utc: datetime
    positions_count: int | None
    pending_orders_count: int | None
    cashflow_journal_reconciled: bool
    owned_exposure_attributed: bool
    broker_identity_reconfirmed: bool
    fresh_source_verified: bool
    new_entry_locked: bool
    human_owner_exit_supervision_confirmed: bool


def _utc(value: datetime, label: str) -> datetime:
    if (
        type(value) is not datetime or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise FlatBeforeEndSafetyError(label + ": not verified UTC")
    return value.astimezone(UTC)


def _positive(value: int, label: str) -> None:
    if type(value) is not int or value <= 0:
        raise FlatBeforeEndSafetyError(label + ": no approved positive timing reserve")


def _contract(contract: FlatSessionContract) -> tuple[datetime, datetime, datetime]:
    begin = _utc(contract.observation_start_utc, "observation start")
    end = _utc(contract.observation_end_utc, "observation end")
    entry_start = _utc(contract.entry_overlap_start_utc, "entry start")
    entry_end = _utc(contract.entry_overlap_end_utc, "entry end")
    broker_end = _utc(contract.broker_eligible_end_utc, "broker session end")
    if end - begin != timedelta(hours=4):
        raise FlatBeforeEndSafetyError("prospective contiguous 4h observation missing")
    if not begin <= entry_start < entry_end <= end:
        raise FlatBeforeEndSafetyError("entry overlap not contained in observation")
    if broker_end <= entry_start:
        raise FlatBeforeEndSafetyError("broker session already closed")
    for value, key in (
        (contract.flat_reconciliation_lead_seconds, "flat lead"),
        (contract.maximum_planned_position_lifetime_seconds, "planned holding"),
        (contract.anticipated_exit_reconciliation_seconds, "reconcile lead"),
    ):
        _positive(value, key)
    limit = min(entry_end, broker_end)
    flat_by = limit - timedelta(seconds=contract.flat_reconciliation_lead_seconds)
    last_entry = flat_by - timedelta(
        seconds=(
            contract.maximum_planned_position_lifetime_seconds
            + contract.anticipated_exit_reconciliation_seconds
        )
    )
    if last_entry <= entry_start:
        raise FlatBeforeEndSafetyError("no safe owner-attended entry interval")
    return entry_start, last_entry, flat_by


def review_candidate_entry(
    contract: FlatSessionContract,
    *,
    now_utc: datetime,
    broker_account_and_orders_confirmed_zero: bool,
    runtime_guard_and_full_policy_a_verified: bool,
    owner_attendance_and_exit_plan_verified: bool,
) -> PreEntryReview:
    """Conservative timing MATH ONLY; no actual broker order authority."""
    start, last_entry, flat_by = _contract(contract)
    now = _utc(now_utc, "entry decision")
    if not (
        broker_account_and_orders_confirmed_zero is True
        and runtime_guard_and_full_policy_a_verified is True
        and owner_attendance_and_exit_plan_verified is True
    ):
        raise FlatBeforeEndSafetyError("unknown exposure/owner/Policy A: quarantine")
    if now < start or now >= last_entry:
        raise FlatBeforeEndSafetyError("entry outside prospectively safe exit budget")
    return PreEntryReview(
        disposition="SYNTHETIC_MATH_ONLY_NO_DEMO_ENTRY_AUTHORITY",
        latest_permitted_entry_utc=last_entry,
        hard_flat_confirmation_deadline_utc=flat_by,
    )


def verify_flat_before_boundary(
    contract: FlatSessionContract, proof: FlatProof
) -> str:
    """All owned exposure flat and pending orders zero before the boundary.

    Caller is responsible for independent broker source provenance. A local
    checked Boolean or fixture never proves real broker flatness.
    """
    start, _, flat_by = _contract(contract)
    observed = _utc(proof.observed_utc, "flat verification")
    if not start <= observed <= flat_by:
        raise FlatBeforeEndSafetyError("flatness not confirmed before exit deadline")
    if (
        type(proof.positions_count) is not int
        or type(proof.pending_orders_count) is not int
        or proof.positions_count != 0 or proof.pending_orders_count != 0
    ):
        raise FlatBeforeEndSafetyError("unknown or nonzero exposure: quarantine human-only E1")
    if not all((
        proof.cashflow_journal_reconciled is True,
        proof.owned_exposure_attributed is True,
        proof.broker_identity_reconfirmed is True,
        proof.fresh_source_verified is True,
        proof.new_entry_locked is True,
        proof.human_owner_exit_supervision_confirmed is True,
    )):
        raise FlatBeforeEndSafetyError("unreconciled or unverified flat proof: quarantine")
    return "SYNTHETIC_FLATNESS_REVIEW_ONLY_NO_REAL_BROKER_ADMISSION"
