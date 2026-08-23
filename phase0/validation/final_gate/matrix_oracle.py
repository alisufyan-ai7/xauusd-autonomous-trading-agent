"""Pure fail-closed evaluator for the final Gate 0 evidence matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


REQUIRED_IDS = {f"G0-{index:02d}" for index in range(1, 15)}
ALLOWED_STATUS = {"PASS", "PENDING", "FAIL_CLOSED"}


@dataclass(frozen=True)
class MatrixResult:
    verdict: str
    reasons: tuple[str, ...]
    passed: int
    pending: int
    failed: int


def evaluate_matrix(payload: Mapping[str, Any]) -> MatrixResult:
    reasons: list[str] = []
    if payload.get("schema_version") != "gate0-final-evidence-matrix-1.0":
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
    statuses = [row.get("status") for row in rows if isinstance(row, dict)]
    if any(status not in ALLOWED_STATUS for status in statuses):
        reasons.append("ITEM_STATUS_INVALID")
    if any(not row.get("area") or not row.get("evidence") or not row.get("remaining")
           or not row.get("owner_action") for row in rows if isinstance(row, dict)):
        reasons.append("ITEM_EVIDENCE_INCOMPLETE")
    passed = statuses.count("PASS")
    pending = statuses.count("PENDING")
    failed = statuses.count("FAIL_CLOSED")
    expected = "PASS" if len(statuses) == len(REQUIRED_IDS) and passed == len(REQUIRED_IDS) \
        else "INCOMPLETE"
    if payload.get("gate_0_verdict") != expected:
        reasons.append("DECLARED_VERDICT_MISMATCH")
    if reasons:
        return MatrixResult("FAIL_CLOSED", tuple(dict.fromkeys(reasons)),
                            passed, pending, failed)
    return MatrixResult(expected, (), passed, pending, failed)
