"""Offline deterministic oracle for the owner-approved operational policy.

The module has no broker, network, messaging, credential, or order capability.
It evaluates V1/M1/E1/P1/A1 only for Gate 0 specification tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


D = Decimal
VOLUME_CAP = D("0.01")
MIN_MARGIN_LEVEL_PERCENT = D("1000")
MIN_FREE_MARGIN_FRACTION = D("0.90")
INCREMENTAL_MARGIN_STRESS_MULTIPLIER = D("2.0")


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    reason: str


@dataclass(frozen=True)
class MarginInputs:
    projected_equity: Decimal | None
    used_margin_before: Decimal | None
    incremental_margin: Decimal | None
    spread_stress: Decimal | None
    slippage_stress: Decimal | None
    gap_stress: Decimal | None
    cost_stress: Decimal | None


def _valid_decimal(value: Decimal | None, *, positive: bool = False) -> bool:
    if value is None or not isinstance(value, Decimal) or not value.is_finite():
        return False
    return value > 0 if positive else value >= 0


def _state_passes(equity: Decimal, used_margin: Decimal) -> bool:
    if equity <= 0 or used_margin < 0:
        return False
    free_margin = equity - used_margin
    free_ok = free_margin >= MIN_FREE_MARGIN_FRACTION * equity
    level_ok = used_margin == 0 or (equity / used_margin * D("100")) >= MIN_MARGIN_LEVEL_PERCENT
    return free_ok and level_ok


def evaluate_m1(inputs: MarginInputs) -> Verdict:
    """Apply both current and stressed M1 tests; invalid inputs fail closed."""
    if not _valid_decimal(inputs.projected_equity, positive=True):
        return Verdict(False, "MARGIN_INPUT_INVALID")
    for value in (
        inputs.used_margin_before,
        inputs.incremental_margin,
        inputs.spread_stress,
        inputs.slippage_stress,
        inputs.gap_stress,
        inputs.cost_stress,
    ):
        if not _valid_decimal(value):
            return Verdict(False, "MARGIN_INPUT_INVALID")

    equity = inputs.projected_equity
    used_before = inputs.used_margin_before
    incremental = inputs.incremental_margin
    stresses = (
        inputs.spread_stress,
        inputs.slippage_stress,
        inputs.gap_stress,
        inputs.cost_stress,
    )
    assert equity is not None and used_before is not None and incremental is not None
    assert all(value is not None for value in stresses)

    current_used = used_before + incremental
    if not _state_passes(equity, current_used):
        return Verdict(False, "M1_CURRENT_THRESHOLD_FAILED")

    stressed_equity = equity - sum((value for value in stresses if value is not None), D("0"))
    stressed_used = used_before + INCREMENTAL_MARGIN_STRESS_MULTIPLIER * incremental
    if not _state_passes(stressed_equity, stressed_used):
        return Verdict(False, "M1_STRESSED_THRESHOLD_FAILED")
    return Verdict(True, "M1_PASS")


def evaluate_v1(
    candidate_volume: Decimal | None,
    *,
    broker_min: Decimal | None,
    broker_step: Decimal | None,
    account_validated_cap: Decimal | None,
) -> Verdict:
    values = (candidate_volume, broker_min, broker_step, account_validated_cap)
    if any(not _valid_decimal(value, positive=True) for value in values):
        return Verdict(False, "VOLUME_INPUT_INVALID")
    assert all(value is not None for value in values)
    candidate = candidate_volume
    minimum = broker_min
    step = broker_step
    account_cap = account_validated_cap
    assert candidate is not None and minimum is not None and step is not None and account_cap is not None
    cap = min(VOLUME_CAP, account_cap)
    if minimum > cap:
        return Verdict(False, "BROKER_MINIMUM_EXCEEDS_V1_CAP")
    if candidate < minimum or candidate > cap:
        return Verdict(False, "V1_CAP_FAILED")
    if (candidate - minimum) % step != 0:
        return Verdict(False, "VOLUME_GRID_FAILED")
    return Verdict(True, "V1_PASS")


def combined_new_risk_gate(*, v1: Verdict, m1: Verdict, other_governor_limits_clear: bool) -> Verdict:
    """M1/V1 are necessary only; neither can override another Governor limit."""
    if not v1.accepted:
        return v1
    if not m1.accepted:
        return m1
    if other_governor_limits_clear is not True:
        return Verdict(False, "OTHER_RISK_GOVERNOR_LIMIT_FAILED")
    return Verdict(True, "POLICY_TEST_PASS_NOT_TRADE_AUTHORITY")


def emergency_e1(condition_present: bool) -> dict[str, object]:
    return {
        "block_new_risk": condition_present,
        "preserve_evidence": condition_present,
        "critical_alert": condition_present,
        "read_only_reconcile": condition_present,
        "broker_requests": (),
        "automatic_unknown_close": False,
    }


def p1_can_create_new_epoch(
    *,
    human_authorized: bool,
    minimum_hold_complete: bool,
    reconciliation_complete: bool,
    diagnostics_pass: bool,
    alert_acknowledged: bool,
    fresh_preflight_pass: bool,
    old_intent_terminal: bool,
) -> bool:
    return all((
        human_authorized,
        minimum_hold_complete,
        reconciliation_complete,
        diagnostics_pass,
        alert_acknowledged,
        fresh_preflight_pass,
        old_intent_terminal,
    ))


def a1_critical_alert(*, acknowledged_at_minute: int | None) -> dict[str, object]:
    if acknowledged_at_minute is not None and acknowledged_at_minute < 0:
        raise ValueError("acknowledgement minute must be non-negative")
    last = 15 if acknowledged_at_minute is None else min(acknowledged_at_minute, 15)
    repeats = tuple(range(0, last + 1, 5))
    return {
        "local_audit": True,
        "channels": ("EMAIL", "TELEGRAM_PUSH"),
        "repeat_minutes": repeats,
        "ack_deadline_minutes": 15,
        "acknowledged_in_time": acknowledged_at_minute is not None and acknowledged_at_minute <= 15,
        "risk_authority_restored": False,
    }
