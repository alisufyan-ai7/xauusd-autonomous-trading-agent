"""Pure fail-closed evaluator for the receipt-bound Gate 0 matrix.

The caller supplies SHA-256 values computed from sanitized repository artifacts.
This module performs no file, network, broker, model, process or write access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping


REQUIRED_CLAIMS = {
    "G0-01": ("READ_ONLY_BASELINE_REAL",),
    "G0-02": ("POLICY_SPEC_AND_OFFLINE",),
    "G0-03": ("OFFICIAL_EVENT_GUARD_REAL",),
    "G0-04": ("NATURAL_EVENT_TRANSITIONS_REAL",),
    "G0-05": ("LICENSED_EMPIRICAL_CALIBRATION",),
    "G0-06": ("ACCOUNT_SESSION_BOUNDARIES_REAL",),
    "G0-07": ("CONTROLLED_VPS_FAULTS_REAL",),
    "G0-08": ("ACCOUNT_MARGIN_STRESS_REAL",),
    "G0-09": ("DUAL_ALERT_DELIVERY_REAL",),
    "G0-10": ("EXHAUSTIVE_SETUP_CORPUS",),
    "G0-11": ("LICENSED_IMMUTABLE_REPLAY_DATA",),
    "G0-12": ("REGISTERED_CHRONOLOGICAL_REPLAY",),
    "G0-13": ("LIVE_MODEL_BENCHMARK", "ANALYST_OFFLINE_CONTRACT"),
    "G0-14": ("LIVE_CHRONOLOGICAL_ANALYST",),
}
CLAIM_PROVENANCE = {
    "READ_ONLY_BASELINE_REAL": "SANITIZED_HASH_RECEIPT",
    "POLICY_SPEC_AND_OFFLINE": "SANITIZED_REPORT",
    "OFFICIAL_EVENT_GUARD_REAL": "SANITIZED_REPORT",
    "NATURAL_EVENT_TRANSITIONS_REAL": "SANITIZED_HASH_RECEIPT",
    "LICENSED_EMPIRICAL_CALIBRATION": "SANITIZED_HASH_RECEIPT",
    "ACCOUNT_SESSION_BOUNDARIES_REAL": "SANITIZED_HASH_RECEIPT",
    "CONTROLLED_VPS_FAULTS_REAL": "SANITIZED_HASH_RECEIPT",
    "ACCOUNT_MARGIN_STRESS_REAL": "SANITIZED_HASH_RECEIPT",
    "DUAL_ALERT_DELIVERY_REAL": "SANITIZED_HASH_RECEIPT",
    "EXHAUSTIVE_SETUP_CORPUS": "SANITIZED_REPORT",
    "LICENSED_IMMUTABLE_REPLAY_DATA": "SANITIZED_HASH_RECEIPT",
    "REGISTERED_CHRONOLOGICAL_REPLAY": "SANITIZED_HASH_RECEIPT",
    "LIVE_MODEL_BENCHMARK": "SANITIZED_HASH_RECEIPT",
    "ANALYST_OFFLINE_CONTRACT": "SANITIZED_REPORT",
    "LIVE_CHRONOLOGICAL_ANALYST": "SANITIZED_HASH_RECEIPT",
}
FROZEN_ADMITTED_RECEIPTS = {
    "READ_ONLY_BASELINE_REAL": (
        "phase0/evidence/VPS_DIAGNOSTIC_EVIDENCE_VALIDATION_2026-08-12.md",
        "8ca4608069f933d3b5c8dadff0a6a2665540f3ed384298aa4fbab99bd6f38478",
        "SANITIZED_HASH_RECEIPT",
    ),
    "POLICY_SPEC_AND_OFFLINE": (
        "phase0/validation/operational_policy/VALIDATION_REPORT_2026-08-23.md",
        "69d39b9f81e65dec404a9863e3c3feb587a9f67012d94d127b7bf099d8345370",
        "SANITIZED_REPORT",
    ),
    "OFFICIAL_EVENT_GUARD_REAL": (
        "phase0/publication/GATE0_CLOSURE_STATUS_2026-08-23_R18.json",
        "536d16ad570ce33f55a017e47d62985c99fe22a5d9fa26d125a3511c5772cf65",
        "SANITIZED_REPORT",
    ),
    "EXHAUSTIVE_SETUP_CORPUS": (
        "phase0/validation/setup_features/VALIDATION_REPORT_2026-08-23_R4.md",
        "cfc779a0ecf81e87c21cd1201dffdebca5ad4276c1b9c5af8c8a05c54b1b2714",
        "SANITIZED_REPORT",
    ),
    "LICENSED_IMMUTABLE_REPLAY_DATA": (
        "phase0/validation/replay_acquisition/DUKASCOPY_DATASET_ADMISSION_REPORT_2026-08-24_R3.json",
        "5408257cc6fa152ddfb8cc2e4f73646858aa14432fbd18ad13db6eba86569c2d",
        "SANITIZED_HASH_RECEIPT",
    ),
    "LIVE_MODEL_BENCHMARK": (
        "phase0/benchmark/openai_analyst/SECOND_LIVE_BENCHMARK_EVALUATION_2026-08-23.md",
        "4e092b22ac12787f632001f8a8eb17c0e5a9321e657c77b953a32b2e683169a2",
        "SANITIZED_HASH_RECEIPT",
    ),
    "ANALYST_OFFLINE_CONTRACT": (
        "phase0/validation/analyst_runtime/VALIDATION_REPORT_2026-08-23_R2.md",
        "5e49d6be163f62777edfd09e52a977b25f09d8c93cd981459df33a839f507234",
        "SANITIZED_REPORT",
    ),
}
REQUIRED_IDS = set(REQUIRED_CLAIMS)
HEX = re.compile(r"^[0-9a-f]{64}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$")


@dataclass(frozen=True)
class MatrixResult:
    verdict: str
    reasons: tuple[str, ...]
    passed: int
    pending: int
    failed: int


def _utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo == timezone.utc


def _receipt_reasons(
    item_id: str, receipt: Any, artifact_hashes: Mapping[str, str],
) -> list[str]:
    if not isinstance(receipt, dict):
        return [f"{item_id}_RECEIPT_INVALID"]
    claim = receipt.get("claim_type")
    path = receipt.get("artifact_path")
    digest = receipt.get("artifact_sha256")
    reasons: list[str] = []
    if claim not in CLAIM_PROVENANCE or claim not in REQUIRED_CLAIMS[item_id]:
        reasons.append(f"{item_id}_CLAIM_NOT_REQUIRED")
    elif receipt.get("provenance") != CLAIM_PROVENANCE[claim]:
        reasons.append(f"{item_id}_PROVENANCE_INVALID")
    if (not isinstance(path, str) or SAFE_PATH.fullmatch(path) is None
            or path.startswith("/") or ".." in path.split("/")):
        reasons.append(f"{item_id}_ARTIFACT_PATH_INVALID")
    if not isinstance(digest, str) or HEX.fullmatch(digest) is None:
        reasons.append(f"{item_id}_ARTIFACT_HASH_INVALID")
    elif not isinstance(path, str) or artifact_hashes.get(path) != digest:
        reasons.append(f"{item_id}_ARTIFACT_HASH_MISMATCH")
    if receipt.get("evidence_status") != "ADMITTED":
        reasons.append(f"{item_id}_EVIDENCE_NOT_ADMITTED")
    if isinstance(claim, str) and (path, digest, receipt.get("provenance")) \
            != FROZEN_ADMITTED_RECEIPTS.get(claim):
        reasons.append(f"{item_id}_RECEIPT_NOT_IN_FROZEN_REGISTRY")
    if not _utc(receipt.get("observed_utc")):
        reasons.append(f"{item_id}_OBSERVED_TIME_INVALID")
    if receipt.get("private_source") is True \
            and receipt.get("published_hash_only") is not True:
        reasons.append(f"{item_id}_PRIVATE_PUBLICATION_INVALID")
    if receipt.get("trading_authorized") is not False:
        reasons.append(f"{item_id}_TRADING_AUTHORIZATION_INVALID")
    if receipt.get("external_python_trading_disabled") is not True:
        reasons.append(f"{item_id}_EXTERNAL_PYTHON_STATE_INVALID")
    if not receipt.get("claim_limit"):
        reasons.append(f"{item_id}_CLAIM_LIMIT_MISSING")
    return reasons


def evaluate_matrix(
    payload: Mapping[str, Any], artifact_hashes: Mapping[str, str],
) -> MatrixResult:
    reasons: list[str] = []
    if payload.get("schema_version") != "gate0-final-evidence-matrix-1.3":
        reasons.append("SCHEMA_INVALID")
    if payload.get("trading_authorized") is not False:
        reasons.append("TRADING_AUTHORIZATION_INVALID")
    if payload.get("external_python_trading_required_state") != "DISABLED":
        reasons.append("EXTERNAL_PYTHON_STATE_INVALID")
    if payload.get("owner_actions_requested_now") != []:
        reasons.append("UNEXPECTED_OWNER_ACTION_REQUEST")
    rows = payload.get("items")
    if not isinstance(rows, list):
        return MatrixResult("FAIL_CLOSED", ("ITEMS_INVALID",), 0, 0, 0)
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or set(ids) != REQUIRED_IDS or len(ids) != len(set(ids)):
        reasons.append("ITEM_INVENTORY_INVALID")

    derived: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("id") not in REQUIRED_IDS:
            continue
        item_id = row["id"]
        if (not row.get("area") or not row.get("evidence") or not row.get("remaining")
                or not row.get("owner_action")):
            reasons.append(f"{item_id}_ITEM_EVIDENCE_INCOMPLETE")
        required = tuple(row.get("required_claims", ()))
        if required != REQUIRED_CLAIMS[item_id]:
            reasons.append(f"{item_id}_REQUIREMENT_REGISTRY_MISMATCH")
        receipts = row.get("receipts")
        if not isinstance(receipts, list):
            reasons.append(f"{item_id}_RECEIPTS_INVALID")
            receipts = []
        claims = [receipt.get("claim_type") for receipt in receipts
                  if isinstance(receipt, dict)]
        if len(claims) != len(set(claims)):
            reasons.append(f"{item_id}_DUPLICATE_CLAIM_RECEIPT")
        receipt_reasons: list[str] = []
        for receipt in receipts:
            receipt_reasons.extend(_receipt_reasons(item_id, receipt, artifact_hashes))
        reasons.extend(receipt_reasons)
        complete = set(claims) == set(REQUIRED_CLAIMS[item_id]) and not receipt_reasons
        expected_status = "PASS" if complete else "PENDING"
        derived.append(expected_status)
        if row.get("status") != expected_status:
            reasons.append(f"{item_id}_STATUS_DERIVATION_MISMATCH")

    passed = derived.count("PASS")
    pending = derived.count("PENDING")
    expected_verdict = "PASS" if len(derived) == len(REQUIRED_IDS) \
        and passed == len(REQUIRED_IDS) else "INCOMPLETE"
    if payload.get("gate_0_verdict") != expected_verdict:
        reasons.append("DECLARED_VERDICT_MISMATCH")
    unique = tuple(dict.fromkeys(reasons))
    if unique:
        return MatrixResult("FAIL_CLOSED", unique, passed, pending, 0)
    return MatrixResult(expected_verdict, (), passed, pending, 0)
