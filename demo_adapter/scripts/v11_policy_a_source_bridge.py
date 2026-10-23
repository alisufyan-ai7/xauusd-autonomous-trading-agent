"""Offline-only 4h quote/fee cost candidate and full Policy A binding guard.

This code DOES NOT ADMIT calibration or authorize execution. Source hashes
and a human/independent fee/provenance verifier are required before an
admission decision. Never turn missing components into zero.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from typing import Any

from scripts.v11_quote_coverage import QuoteSample, evaluate_quote_coverage

CENT = Decimal("0.01")
DEMO_VOLUME = Decimal("0.01")


class BridgeSafetyError(ValueError):
    """Missing broker, provenance, fee or Policy A input."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def decimal(raw: Any, field: str, *, nonnegative: bool = True) -> Decimal:
    if type(raw) not in (str, int, Decimal):
        raise BridgeSafetyError(f"invalid decimal source: {field}")
    try:
        value = Decimal(str(raw))
    except Exception as exc:
        raise BridgeSafetyError(f"invalid decimal source: {field}") from exc
    if not value.is_finite() or (nonnegative and value < 0):
        raise BridgeSafetyError(f"missing/nonfinite/negative {field}")
    return value


def cent_up(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_CEILING)


@dataclass(frozen=True)
class DemoCostCandidate:
    status: str
    scope: str
    private_source_sha256: str
    max_spread_usd: str
    adverse_quote_proxy_usd: str
    adverse_gap_quote_proxy_usd: str
    commission_usd: str
    swap_reserve_usd: str
    current_adverse_cost_usd: str
    stressed_adverse_cost_usd: str
    risk_execution_permission: bool = False


def derive_unadmitted_demo_cost_candidate(
    *,
    raw_evidence: bytes,
    sealed_manifest: bytes,
    exact_private_sha256: str,
    fee_proof: dict[str, Any],
    exact_fee_proof_sha256: str,
    fee_proof_source: bytes,
    registered_tolerance_ms: int,
) -> DemoCostCandidate:
    """Derive a transparent NON-ADMITTED USD cost candidate from verified bytes."""
    if digest(raw_evidence) != exact_private_sha256:
        raise BridgeSafetyError("private capture SHA mismatch")
    manifest = json.loads(sealed_manifest)
    record = json.loads(raw_evidence)
    if manifest.get("private_evidence_sha256") != exact_private_sha256:
        raise BridgeSafetyError("independent capture manifest not reconciled")
    if manifest.get("status") != "RAW_CAPTURE_COMPLETE_NOT_CALIBRATION_ADMITTED":
        raise BridgeSafetyError("capture not complete")
    if record.get("schema") != "DEMO_V11_PRIVATE_READONLY_CAPTURE_V1":
        raise BridgeSafetyError("wrong capture schema")
    if record.get("calibration_admitted") is not False or record.get("broker_orders_sent") != 0:
        raise BridgeSafetyError("not pure read-only capture")
    if record.get("symbol") != "XAUUSD":
        raise BridgeSafetyError("non-XAUUSD source")
    if not record.get("account_before") or not record.get("account_after"):
        raise BridgeSafetyError("missing broker account risk boundaries")
    if len(record.get("samples", [])) != 2880:
        raise BridgeSafetyError("observer coverage incomplete")
    if digest(fee_proof_source) != exact_fee_proof_sha256:
        raise BridgeSafetyError("account-specific fee documentation hash mismatch")
    if json.loads(fee_proof_source) != fee_proof:
        raise BridgeSafetyError("fee-provenance object differs from reviewed source")
    if fee_proof.get("scope") != "XAUUSD_EXNESS_DEMO_001":
        raise BridgeSafetyError("fee source wrong broker/symbol/volume")
    if fee_proof.get("independent_reviewer_accepted") is not True:
        raise BridgeSafetyError("no independent fee reviewer acceptance")
    if type(registered_tolerance_ms) is not int or not 0 <= registered_tolerance_ms <= 1000:
        raise BridgeSafetyError("no prospectively registered tick-pair tolerance")
    start = datetime.fromisoformat(record["start"])
    end = datetime.fromisoformat(record["end"])
    polls = [
        QuoteSample(int(p["observed_ms"]), p["bid"], p["ask"])
        for p in record["samples"]
    ]
    ticks = [
        QuoteSample(int(t["time_msc"]), t["bid"], t["ask"])
        for t in record["ticks"]
    ]
    quote = evaluate_quote_coverage(
        start, end, polls, ticks, pair_tolerance_ms=registered_tolerance_ms
    )
    symbol = record["symbol_cash_metadata"]
    contract = decimal(symbol["trade_contract_size"], "contract size")
    tick_size = decimal(symbol["trade_tick_size"], "tick size")
    tick_value = decimal(symbol["trade_tick_value_loss"], "tick value")
    if min(contract, tick_size, tick_value) <= 0:
        raise BridgeSafetyError("nonpositive broker tick conversion")
    broker_tick_usd = contract * tick_size
    if abs(broker_tick_usd - tick_value) > tick_value * Decimal("0.01"):
        raise BridgeSafetyError("broker USD tick/contract metadata mismatch")
    usd_per_price_001 = DEMO_VOLUME * tick_value / tick_size
    spread = decimal(quote.maximum_spread_price, "spread") * usd_per_price_001
    move = max(
        decimal(quote.max_adverse_move_price_1s, "move 1s"),
        decimal(quote.max_adverse_move_price_5s, "move 5s"),
        decimal(quote.max_adverse_move_price_30s, "move 30s"),
    ) * usd_per_price_001
    jump = decimal(
        quote.max_adverse_tick_jump_price, "quote gap"
    ) * usd_per_price_001
    commission = decimal(fee_proof.get("round_trip_commission_usd"), "commission")
    swap = decimal(fee_proof.get("contingent_holding_swap_usd"), "swap")
    # Separate maxima on purpose; conservative potential overlap is documented,
    # and no claim is made that true tick quote moves bound actual broker fills.
    current = cent_up(spread + move + jump + commission + swap)
    stressed = cent_up(max(current * 2, current + spread + move + jump))
    return DemoCostCandidate(
        status="NUMERIC_CANDIDATE_NOT_ADMITTED_INDEPENDENT_RISK_REVIEW_REQUIRED",
        scope="DEMO_LIFECYCLE_ONLY",
        private_source_sha256=exact_private_sha256,
        max_spread_usd=str(cent_up(spread)),
        adverse_quote_proxy_usd=str(cent_up(move)),
        adverse_gap_quote_proxy_usd=str(cent_up(jump)),
        commission_usd=str(cent_up(commission)),
        swap_reserve_usd=str(cent_up(swap)),
        current_adverse_cost_usd=str(current),
        stressed_adverse_cost_usd=str(stressed),
    )


def verify_full_policy_input_provenance(
    *,
    proof_bytes: bytes,
    expected_proof_sha256: str,
    admitted_calibration_sha256: str,
    current_account_snapshot_sha256: str,
    period_ledger_sha256: str,
) -> dict[str, Any]:
    """Block math evaluation until ALL trusted external source receipts exist.

    A hash alone is not broker authenticity; the receipt must be separately
    independently reviewed/accepted. Never flip adapter's order quarantine.
    """
    if digest(proof_bytes) != expected_proof_sha256:
        raise BridgeSafetyError("untrusted Policy A provenance object")
    proof = json.loads(proof_bytes)
    requirements = {
        "scope": "DEMO_LIFECYCLE_ONLY",
        "risk_calibration_sha256": admitted_calibration_sha256,
        "current_broker_snapshot_sha256": current_account_snapshot_sha256,
        "day_week_inception_ledger_sha256": period_ledger_sha256,
        "independent_broker_reconciliation_pass": True,
        "independent_period_cashflow_verification_pass": True,
        "full_policy_a_offline_evaluator_pass": True,
        "session_event_guard_eligible": True,
        "external_python_trading_disabled": True,
        "broker_order_permission": False,
    }
    if any(proof.get(k) != v for k, v in requirements.items()):
        raise BridgeSafetyError("Policy A source binding incomplete")
    for key in (
        "risk_calibration_sha256", "current_broker_snapshot_sha256",
        "day_week_inception_ledger_sha256",
    ):
        if type(proof[key]) is not str or len(proof[key]) != 64:
            raise BridgeSafetyError("bad Policy A binding hash")
    return {
        "status": "POLICY_A_SOURCE_RECEIPTS_HASH_BOUND_OFFLINE_ONLY",
        "execution_authorized": False,
        "provenance_sha256": expected_proof_sha256,
    }
