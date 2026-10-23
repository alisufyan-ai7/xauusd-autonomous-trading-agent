"""Offline source-bound demo v1.1 cost and Policy A input provenance tests."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts.v11_policy_a_source_bridge import (
    BridgeSafetyError,
    derive_unadmitted_demo_cost_candidate,
    digest,
    verify_full_policy_input_provenance,
)


def _sources() -> tuple[bytes, bytes, dict[str, object], bytes]:
    start = datetime(2026, 10, 21, 12, tzinfo=UTC)
    observations = [
        {
            "observed_ms": int((start + timedelta(seconds=i * 5)).timestamp() * 1000),
            "bid": "2000.00", "ask": "2000.25",
        }
        for i in range(2880)
    ]
    ticks = [
        {
            "time_msc": int((start + timedelta(seconds=i)).timestamp() * 1000),
            "bid": "2000.00", "ask": "2000.25",
        }
        for i in range(14400)
    ]
    document = {
        "schema": "DEMO_V11_PRIVATE_READONLY_CAPTURE_V1",
        "calibration_admitted": False,
        "broker_orders_sent": 0,
        "symbol": "XAUUSD",
        "start": start.isoformat(),
        "end": (start + timedelta(hours=4)).isoformat(),
        "samples": observations,
        "ticks": ticks,
        "account_before": {"balance": "10000", "equity": "10000"},
        "account_after": {"balance": "10000", "equity": "10000"},
        "symbol_cash_metadata": {
            "trade_contract_size": "100", "trade_tick_size": "0.01",
            "trade_tick_value_loss": "1",
        },
    }
    data = json.dumps(document, separators=(",", ":")).encode()
    manifest = json.dumps({
        "status": "RAW_CAPTURE_COMPLETE_NOT_CALIBRATION_ADMITTED",
        "private_evidence_sha256": digest(data),
    }).encode()
    fees: dict[str, object] = {
        "scope": "XAUUSD_EXNESS_DEMO_001",
        "independent_reviewer_accepted": True,
        "round_trip_commission_usd": "0.40",
        "contingent_holding_swap_usd": "1.20",
    }
    fee_bytes = json.dumps(fees, sort_keys=True).encode()
    return data, manifest, fees, fee_bytes


def test_quote_cost_candidate_requires_real_ticks_and_fee_provenance() -> None:
    data, manifest, fees, fee_bytes = _sources()
    result = derive_unadmitted_demo_cost_candidate(
        raw_evidence=data,
        sealed_manifest=manifest,
        exact_private_sha256=digest(data),
        fee_proof=fees,
        exact_fee_proof_sha256=digest(fee_bytes),
        fee_proof_source=fee_bytes,
        registered_tolerance_ms=100,
    )
    assert result.status.startswith("NUMERIC_CANDIDATE_NOT_ADMITTED")
    assert result.scope == "DEMO_LIFECYCLE_ONLY"
    assert result.risk_execution_permission is False
    assert result.commission_usd == "0.40"
    assert result.swap_reserve_usd == "1.20"
    assert result.current_adverse_cost_usd == "1.85"
    assert result.stressed_adverse_cost_usd == "3.70"


@pytest.mark.parametrize("modification", ["fees", "approval", "hash", "tolerance"])
def test_unverified_fee_or_tick_source_never_admitted(modification: str) -> None:
    data, manifest, fees, fee_bytes = _sources()
    expected = digest(data)
    tol: int | None = 100
    if modification == "fees":
        fees["contingent_holding_swap_usd"] = None
        fee_bytes = json.dumps(fees, sort_keys=True).encode()
    elif modification == "approval":
        fees["independent_reviewer_accepted"] = False
        fee_bytes = json.dumps(fees, sort_keys=True).encode()
    elif modification == "hash":
        expected = "0" * 64
    else:
        tol = None
    with pytest.raises(BridgeSafetyError):
        derive_unadmitted_demo_cost_candidate(
            raw_evidence=data,
            sealed_manifest=manifest,
            exact_private_sha256=expected,
            fee_proof=fees,
            exact_fee_proof_sha256=digest(fee_bytes),
            fee_proof_source=fee_bytes,
            registered_tolerance_ms=tol,  # type: ignore[arg-type]
        )


def test_full_policy_receipt_binding_is_never_order_authority() -> None:
    proof = {
        "scope": "DEMO_LIFECYCLE_ONLY",
        "risk_calibration_sha256": "1" * 64,
        "current_broker_snapshot_sha256": "2" * 64,
        "day_week_inception_ledger_sha256": "3" * 64,
        "independent_broker_reconciliation_pass": True,
        "independent_period_cashflow_verification_pass": True,
        "full_policy_a_offline_evaluator_pass": True,
        "session_event_guard_eligible": True,
        "external_python_trading_disabled": True,
        "broker_order_permission": False,
    }
    source = json.dumps(proof, sort_keys=True).encode()
    allowed = verify_full_policy_input_provenance(
        proof_bytes=source, expected_proof_sha256=digest(source),
        admitted_calibration_sha256="1" * 64,
        current_account_snapshot_sha256="2" * 64,
        period_ledger_sha256="3" * 64,
    )
    assert allowed["execution_authorized"] is False
    proof["broker_order_permission"] = True
    source = json.dumps(proof, sort_keys=True).encode()
    with pytest.raises(BridgeSafetyError):
        verify_full_policy_input_provenance(
            proof_bytes=source, expected_proof_sha256=digest(source),
            admitted_calibration_sha256="1" * 64,
            current_account_snapshot_sha256="2" * 64,
            period_ledger_sha256="3" * 64,
        )
