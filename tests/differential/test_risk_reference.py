from decimal import Decimal, localcontext

from hypothesis import given
from hypothesis import strategies as st

from xauusd_agent.risk.policy_a import (
    ExposureKnowledge,
    PolicyAInput,
    RiskDisposition,
    evaluate_policy_a,
)


@given(
    equity=st.integers(min_value=1, max_value=1_000_000),
    free_margin=st.integers(min_value=0, max_value=1_000_000),
    margin_used=st.integers(min_value=0, max_value=100_000),
    incremental_margin=st.integers(min_value=1, max_value=100_000),
    current_cost=st.integers(min_value=0, max_value=100_000),
    stress_delta=st.integers(min_value=0, max_value=100_000),
)
def test_policy_a_matches_independent_decimal_reference(
    equity: int,
    free_margin: int,
    margin_used: int,
    incremental_margin: int,
    current_cost: int,
    stress_delta: int,
) -> None:
    values = {
        "equity": Decimal(equity),
        "free": Decimal(free_margin),
        "used": Decimal(margin_used),
        "increment": Decimal(incremental_margin),
        "current_cost": Decimal(current_cost),
        "stress_cost": Decimal(current_cost + stress_delta),
    }
    result = evaluate_policy_a(
        PolicyAInput(
            symbol="XAUUSD",
            requested_volume_lots=Decimal("0.01"),
            account_equity=values["equity"],
            account_free_margin=values["free"],
            account_margin_used=values["used"],
            incremental_margin=values["increment"],
            current_adverse_cost=values["current_cost"],
            stressed_adverse_cost=values["stress_cost"],
            exposure=ExposureKnowledge.CONFIRMED_ZERO,
            fingerprint_matches=True,
            protective_stop_present=True,
        )
    )

    with localcontext() as context:
        context.prec = 34
        current_equity = values["equity"] - values["current_cost"]
        current_margin = values["used"] + values["increment"]
        current_free = values["free"] - values["current_cost"] - values["increment"]
        stressed_equity = values["equity"] - values["stress_cost"]
        stressed_margin = values["used"] + values["increment"] * 2
        stressed_free = values["free"] - values["stress_cost"] - values["increment"] * 2
        current_ok = (
            current_equity > 0
            and current_free >= 0
            and current_equity / current_margin * 100 >= 1000
            and current_free >= current_equity * Decimal("0.90")
        )
        stressed_ok = (
            stressed_equity > 0
            and stressed_free >= 0
            and stressed_equity / stressed_margin * 100 >= 1000
            and stressed_free >= stressed_equity * Decimal("0.90")
        )
        current_level = current_equity / current_margin * 100
        stressed_level = stressed_equity / stressed_margin * 100
        reasons = []
        if current_equity <= 0 or current_free < 0:
            reasons.append("M1_CURRENT_INSOLVENT_OR_UNDEFINED")
        else:
            if current_equity / current_margin * 100 < 1000:
                reasons.append("M1_CURRENT_MARGIN_LEVEL_BELOW_1000_PERCENT")
            if current_free < current_equity * Decimal("0.90"):
                reasons.append("M1_CURRENT_FREE_MARGIN_BELOW_90_PERCENT_EQUITY")
        if stressed_equity <= 0 or stressed_free < 0:
            reasons.append("M1_STRESSED_INSOLVENT_OR_UNDEFINED")
        else:
            if stressed_equity / stressed_margin * 100 < 1000:
                reasons.append("M1_STRESSED_MARGIN_LEVEL_BELOW_1000_PERCENT")
            if stressed_free < stressed_equity * Decimal("0.90"):
                reasons.append("M1_STRESSED_FREE_MARGIN_BELOW_90_PERCENT_EQUITY")
    expected = RiskDisposition.ALLOW if current_ok and stressed_ok else RiskDisposition.REJECT
    assert result.disposition is expected
    assert result.policy == "POLICY_A_V1_M1"
    assert result.requested_volume_lots == Decimal("0.01")
    assert result.current_projected_equity == current_equity
    assert result.current_projected_free_margin == current_free
    assert result.current_projected_margin_level_percent == current_level
    assert result.stressed_projected_equity == stressed_equity
    assert result.stressed_projected_free_margin == stressed_free
    assert result.stressed_projected_margin_level_percent == stressed_level
    expected_reasons = tuple(reasons) if reasons else ("ALL_FROZEN_CONTROLS_PASS",)
    assert result.reason_codes == expected_reasons
