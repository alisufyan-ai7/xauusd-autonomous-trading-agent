from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from xauusd_agent.config import ConfigurationError, RuntimeConfig
from xauusd_agent.reconciliation.null_execution import NullExecutionRecord
from xauusd_agent.risk.policy_a import (
    ExposureKnowledge,
    PolicyAInput,
    RiskDisposition,
    evaluate_policy_a,
)


def _valid_risk_input() -> PolicyAInput:
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


@given(st.integers(min_value=10_001, max_value=10_000_000))
def test_any_volume_above_frozen_cap_never_allows(micro_lots: int) -> None:
    volume = Decimal(micro_lots) / Decimal("1000000")
    result = evaluate_policy_a(replace(_valid_risk_input(), requested_volume_lots=volume))
    assert result.disposition is RiskDisposition.REJECT
    assert "V1_VOLUME_CAP_EXCEEDED" in result.reason_codes


@given(
    st.sampled_from(
        [
            "requested_volume_lots",
            "account_equity",
            "account_free_margin",
            "account_margin_used",
            "incremental_margin",
            "current_adverse_cost",
            "stressed_adverse_cost",
        ]
    )
)
def test_missing_numeric_risk_input_always_quarantines(field: str) -> None:
    result = evaluate_policy_a(replace(_valid_risk_input(), **{field: None}))
    assert result.disposition is RiskDisposition.QUARANTINE
    assert result.allowed is False


@given(st.text(min_size=1).filter(lambda value: value != "NULL"))
def test_every_non_null_broker_sink_is_rejected(sink: str) -> None:
    with pytest.raises(ConfigurationError):
        RuntimeConfig(state_directory=Path("/state"), broker_sink=sink)


@given(st.text(min_size=1), st.text(min_size=1))
def test_null_execution_record_is_immutable_and_zero_action(
    decision_id: str, decided_at_utc: str
) -> None:
    record = NullExecutionRecord(
        decision_id=decision_id,
        decided_at_utc=decided_at_utc,
        setup_id=None,
        risk_disposition=RiskDisposition.REJECT,
        risk_reason_codes=("PROPERTY_TEST",),
    )
    assert record.execution_capability == "ABSENT"
    assert record.broker_action_count == 0
    with pytest.raises((FrozenInstanceError, AttributeError)):
        record.broker_action_count = 1  # type: ignore[misc]
