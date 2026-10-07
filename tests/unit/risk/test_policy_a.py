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


@pytest.mark.parametrize(
    ("field", "expected_reason"),
    [
        ("requested_volume_lots", "INVALID_REQUESTED_VOLUME_LOTS"),
        ("account_equity", "INVALID_ACCOUNT_EQUITY"),
        ("account_free_margin", "INVALID_ACCOUNT_FREE_MARGIN"),
        ("account_margin_used", "INVALID_ACCOUNT_MARGIN_USED"),
        ("incremental_margin", "INVALID_INCREMENTAL_MARGIN"),
        ("current_adverse_cost", "INVALID_CURRENT_ADVERSE_COST"),
        ("stressed_adverse_cost", "INVALID_STRESSED_ADVERSE_COST"),
    ],
)
def test_every_scalar_identity_is_exact_and_missing_fails_closed(
    passing_input: PolicyAInput, field: str, expected_reason: str
) -> None:
    result = evaluate_policy_a(replace(passing_input, **{field: None}))
    assert result == result.__class__(
        policy="POLICY_A_V1_M1",
        disposition=RiskDisposition.QUARANTINE,
        reason_codes=(expected_reason,),
        requested_volume_lots=(
            None if field == "requested_volume_lots" else Decimal("0.01")
        ),
    )


def test_non_decimal_scalar_quarantines_without_attribute_error(
    passing_input: PolicyAInput,
) -> None:
    result = evaluate_policy_a(replace(passing_input, account_equity="10000"))  # type: ignore[arg-type]
    assert result.disposition is RiskDisposition.QUARANTINE
    assert result.reason_codes == ("INVALID_ACCOUNT_EQUITY",)


@pytest.mark.parametrize("symbol", [None, "", "   ", 7])
def test_invalid_symbol_forms_quarantine_exactly(
    passing_input: PolicyAInput, symbol: object
) -> None:
    result = evaluate_policy_a(replace(passing_input, symbol=symbol))  # type: ignore[arg-type]
    assert result.disposition is RiskDisposition.QUARANTINE
    assert result.reason_codes == ("INVALID_SYMBOL",)


@pytest.mark.parametrize("exposure", [None, "UNKNOWN"])
def test_invalid_exposure_type_quarantines_exactly(
    passing_input: PolicyAInput, exposure: object
) -> None:
    result = evaluate_policy_a(replace(passing_input, exposure=exposure))  # type: ignore[arg-type]
    assert result.disposition is RiskDisposition.QUARANTINE
    assert result.reason_codes == ("UNKNOWN_EXPOSURE",)


@pytest.mark.parametrize(
    ("changes", "reasons"),
    [
        ({"symbol": "EURUSD"}, ("SYMBOL_NOT_XAUUSD",)),
        ({"requested_volume_lots": Decimal("0")}, ("VOLUME_NOT_POSITIVE",)),
        ({"requested_volume_lots": Decimal("0.0100001")}, ("V1_VOLUME_CAP_EXCEEDED",)),
        ({"account_equity": Decimal("0")}, ("EQUITY_NOT_POSITIVE",)),
        ({"account_free_margin": Decimal("-1")}, ("INVALID_ACCOUNT_MARGIN_STATE",)),
        ({"account_margin_used": Decimal("-1")}, ("INVALID_ACCOUNT_MARGIN_STATE",)),
        ({"incremental_margin": Decimal("0")}, ("INCREMENTAL_MARGIN_NOT_POSITIVE",)),
        ({"current_adverse_cost": Decimal("-1")}, ("ADVERSE_COST_NEGATIVE",)),
        (
            {"stressed_adverse_cost": Decimal("-1")},
            ("ADVERSE_COST_NEGATIVE", "STRESSED_COST_BELOW_CURRENT_COST"),
        ),
        (
            {"current_adverse_cost": Decimal("2"), "stressed_adverse_cost": Decimal("1")},
            ("STRESSED_COST_BELOW_CURRENT_COST",),
        ),
        (
            {"exposure": ExposureKnowledge.CONFIRMED_NONZERO},
            ("EXISTING_EXPOSURE_REJECT_NEW_RISK",),
        ),
    ],
)
def test_every_static_rejection_boundary_and_code_is_exact(
    passing_input: PolicyAInput, changes: dict[str, object], reasons: tuple[str, ...]
) -> None:
    result = evaluate_policy_a(replace(passing_input, **changes))  # type: ignore[arg-type]
    assert result.policy == "POLICY_A_V1_M1"
    assert result.disposition is RiskDisposition.REJECT
    assert result.reason_codes == reasons
    assert result.requested_volume_lots == changes.get(
        "requested_volume_lots", Decimal("0.01")
    )
    assert result.current_projected_equity is None


@pytest.mark.parametrize(
    ("changes", "expected_reason"),
    [
        (
            {
                "account_equity": Decimal("5"),
                "account_free_margin": Decimal("1000"),
                "current_adverse_cost": Decimal("5"),
                "stressed_adverse_cost": Decimal("5"),
            },
            "M1_CURRENT_INSOLVENT_OR_UNDEFINED",
        ),
        (
            {
                "account_equity": Decimal("1000"),
                "account_free_margin": Decimal("950"),
                "incremental_margin": Decimal("100"),
                "current_adverse_cost": Decimal("1"),
                "stressed_adverse_cost": Decimal("1"),
            },
            "M1_CURRENT_FREE_MARGIN_BELOW_90_PERCENT_EQUITY",
        ),
        (
            {
                "account_equity": Decimal("10"),
                "account_free_margin": Decimal("1000"),
                "current_adverse_cost": Decimal("0"),
                "stressed_adverse_cost": Decimal("10"),
            },
            "M1_STRESSED_INSOLVENT_OR_UNDEFINED",
        ),
    ],
)
def test_projection_insolvency_boundaries_are_not_relaxed(
    passing_input: PolicyAInput, changes: dict[str, Decimal], expected_reason: str
) -> None:
    result = evaluate_policy_a(replace(passing_input, **changes))
    assert result.disposition is RiskDisposition.REJECT
    assert expected_reason in result.reason_codes


def test_exact_margin_and_free_margin_thresholds_pass_but_one_unit_below_rejects(
    passing_input: PolicyAInput,
) -> None:
    exact = replace(
        passing_input,
        account_equity=Decimal("1000"),
        account_free_margin=Decimal("1100"),
        incremental_margin=Decimal("50"),
        current_adverse_cost=Decimal("0"),
        stressed_adverse_cost=Decimal("0"),
    )
    exact_result = evaluate_policy_a(exact)
    assert exact_result.stressed_projected_margin_level_percent == Decimal("1000")
    assert "M1_STRESSED_MARGIN_LEVEL_BELOW_1000_PERCENT" not in exact_result.reason_codes

    below = evaluate_policy_a(replace(exact, account_equity=Decimal("999")))
    assert "M1_STRESSED_MARGIN_LEVEL_BELOW_1000_PERCENT" in below.reason_codes

    free_exact = evaluate_policy_a(
        replace(
            passing_input,
            account_equity=Decimal("1000"),
            account_free_margin=Decimal("1000"),
            incremental_margin=Decimal("100"),
            current_adverse_cost=Decimal("0"),
            stressed_adverse_cost=Decimal("0"),
        )
    )
    assert "M1_CURRENT_FREE_MARGIN_BELOW_90_PERCENT_EQUITY" not in free_exact.reason_codes
    free_below = evaluate_policy_a(replace(passing_input, account_free_margin=Decimal("999.99")))
    assert "M1_CURRENT_FREE_MARGIN_BELOW_90_PERCENT_EQUITY" in free_below.reason_codes


def test_small_positive_margin_denominators_remain_defined(
    passing_input: PolicyAInput,
) -> None:
    result = evaluate_policy_a(
        replace(
            passing_input,
            incremental_margin=Decimal("0.1"),
            account_margin_used=Decimal("0"),
            current_adverse_cost=Decimal("0"),
            stressed_adverse_cost=Decimal("0"),
        )
    )
    assert result.disposition is RiskDisposition.ALLOW
    assert result.current_projected_margin_level_percent == Decimal("10000000")
    assert result.stressed_projected_margin_level_percent == Decimal("5000000")


@pytest.mark.parametrize(
    ("free_margin", "expected_current_free"),
    [(Decimal("1"), Decimal("0")), (Decimal("1.5"), Decimal("0.5"))],
)
def test_nonnegative_current_free_margin_is_ratio_checked_not_called_insolvent(
    passing_input: PolicyAInput,
    free_margin: Decimal,
    expected_current_free: Decimal,
) -> None:
    result = evaluate_policy_a(
        replace(
            passing_input,
            account_equity=Decimal("10"),
            account_free_margin=free_margin,
            incremental_margin=Decimal("1"),
            current_adverse_cost=Decimal("0"),
            stressed_adverse_cost=Decimal("0"),
        )
    )
    assert result.current_projected_free_margin == expected_current_free
    assert "M1_CURRENT_INSOLVENT_OR_UNDEFINED" not in result.reason_codes
    assert "M1_CURRENT_FREE_MARGIN_BELOW_90_PERCENT_EQUITY" in result.reason_codes


def test_exact_current_margin_level_threshold_is_admitted(
    passing_input: PolicyAInput,
) -> None:
    result = evaluate_policy_a(
        replace(
            passing_input,
            account_equity=Decimal("10"),
            account_free_margin=Decimal("100"),
            incremental_margin=Decimal("1"),
            current_adverse_cost=Decimal("0"),
            stressed_adverse_cost=Decimal("0"),
        )
    )
    assert result.current_projected_margin_level_percent == Decimal("1000")
    assert result.reason_codes == ("M1_STRESSED_MARGIN_LEVEL_BELOW_1000_PERCENT",)


def test_zero_stressed_free_margin_is_ratio_checked_not_called_insolvent(
    passing_input: PolicyAInput,
) -> None:
    result = evaluate_policy_a(
        replace(
            passing_input,
            account_equity=Decimal("10"),
            account_free_margin=Decimal("2"),
            incremental_margin=Decimal("1"),
            current_adverse_cost=Decimal("0"),
            stressed_adverse_cost=Decimal("0"),
        )
    )
    assert result.stressed_projected_free_margin == Decimal("0")
    assert "M1_STRESSED_INSOLVENT_OR_UNDEFINED" not in result.reason_codes
    assert "M1_STRESSED_FREE_MARGIN_BELOW_90_PERCENT_EQUITY" in result.reason_codes


def test_exact_stressed_free_margin_ratio_threshold_is_admitted(
    passing_input: PolicyAInput,
) -> None:
    result = evaluate_policy_a(
        replace(
            passing_input,
            account_equity=Decimal("100"),
            account_free_margin=Decimal("110"),
            incremental_margin=Decimal("10"),
            current_adverse_cost=Decimal("0"),
            stressed_adverse_cost=Decimal("0"),
        )
    )
    assert result.stressed_projected_free_margin == Decimal("90")
    assert result.reason_codes == ("M1_STRESSED_MARGIN_LEVEL_BELOW_1000_PERCENT",)
