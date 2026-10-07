from dataclasses import replace
from decimal import Decimal

import pytest

from xauusd_agent.risk.policy_a import (
    ExposureKnowledge,
    PolicyAInput,
    RiskDisposition,
    evaluate_policy_a,
)


@pytest.fixture
def passing_input() -> PolicyAInput:
    return PolicyAInput(
        symbol="XAUUSD",
        requested_volume_lots=Decimal("0.01"),
        account_equity=Decimal("10000"),
        account_free_margin=Decimal("10000"),
        account_margin_used=Decimal("0"),
        incremental_margin=Decimal("100"),
        current_adverse_cost=Decimal("5"),
        stressed_adverse_cost=Decimal("10"),
        exposure=ExposureKnowledge.CONFIRMED_ZERO,
        fingerprint_matches=True,
        protective_stop_present=True,
    )


def test_exact_v1_boundary_and_both_m1_projections_pass(
    passing_input: PolicyAInput,
) -> None:
    result = evaluate_policy_a(passing_input)
    assert result.disposition is RiskDisposition.ALLOW
    assert result.reason_codes == ("ALL_FROZEN_CONTROLS_PASS",)
    assert result.current_projected_margin_level_percent == Decimal("9995")
    assert result.stressed_projected_margin_level_percent == Decimal("4995")


def test_v1_over_cap_rejects(passing_input: PolicyAInput) -> None:
    result = evaluate_policy_a(
        replace(passing_input, requested_volume_lots=Decimal("0.0100000001"))
    )
    assert result.disposition is RiskDisposition.REJECT
    assert "V1_VOLUME_CAP_EXCEEDED" in result.reason_codes


@pytest.mark.parametrize("value", [None, Decimal("NaN"), Decimal("Infinity")])
def test_missing_or_nonfinite_input_quarantines(
    passing_input: PolicyAInput, value: Decimal | None
) -> None:
    result = evaluate_policy_a(replace(passing_input, incremental_margin=value))
    assert result.disposition is RiskDisposition.QUARANTINE
    assert result.reason_codes == ("INVALID_INCREMENTAL_MARGIN",)


def test_unknown_exposure_quarantines_and_never_assumes_zero(
    passing_input: PolicyAInput,
) -> None:
    result = evaluate_policy_a(replace(passing_input, exposure=ExposureKnowledge.UNKNOWN))
    assert result.disposition is RiskDisposition.QUARANTINE
    assert result.reason_codes == ("UNKNOWN_EXPOSURE",)


def test_known_existing_exposure_rejects_new_risk(passing_input: PolicyAInput) -> None:
    result = evaluate_policy_a(replace(passing_input, exposure=ExposureKnowledge.CONFIRMED_NONZERO))
    assert result.disposition is RiskDisposition.REJECT
    assert "EXISTING_EXPOSURE_REJECT_NEW_RISK" in result.reason_codes


def test_stressed_two_x_incremental_margin_is_binding(
    passing_input: PolicyAInput,
) -> None:
    data = replace(
        passing_input,
        account_equity=Decimal("1000"),
        account_free_margin=Decimal("1000"),
        incremental_margin=Decimal("100"),
        current_adverse_cost=Decimal("0"),
        stressed_adverse_cost=Decimal("0"),
    )
    result = evaluate_policy_a(data)
    assert result.current_projected_margin_level_percent == Decimal("1000")
    assert result.stressed_projected_margin_level_percent == Decimal("500")
    assert result.disposition is RiskDisposition.REJECT
    assert "M1_STRESSED_MARGIN_LEVEL_BELOW_1000_PERCENT" in result.reason_codes


def test_free_margin_ratio_uses_projected_equity(passing_input: PolicyAInput) -> None:
    data = replace(
        passing_input,
        account_equity=Decimal("10000"),
        account_free_margin=Decimal("9200"),
        incremental_margin=Decimal("150"),
        current_adverse_cost=Decimal("100"),
        stressed_adverse_cost=Decimal("200"),
    )
    result = evaluate_policy_a(data)
    assert result.disposition is RiskDisposition.REJECT
    assert "M1_STRESSED_FREE_MARGIN_BELOW_90_PERCENT_EQUITY" in result.reason_codes


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("symbol", "EURUSD", "SYMBOL_NOT_XAUUSD"),
        ("fingerprint_matches", False, "BROKER_FINGERPRINT_UNKNOWN_OR_MISMATCH"),
        ("protective_stop_present", False, "PROTECTIVE_STOP_UNKNOWN_OR_ABSENT"),
    ],
)
def test_envelope_and_identity_are_fail_closed(
    passing_input: PolicyAInput, field: str, value: object, reason: str
) -> None:
    result = evaluate_policy_a(replace(passing_input, **{field: value}))
    expected = RiskDisposition.REJECT if field == "symbol" else RiskDisposition.QUARANTINE
    assert result.disposition is expected
    assert reason in result.reason_codes
