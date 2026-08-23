"""Fail-closed admission for a frozen empirical M1 adverse-stress artifact.

The oracle validates caller-supplied metadata only.  It does not read private
account state, calibrate market data, call MT5, or grant an M1/trading verdict.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


SCHEMA_VERSION = "gate0-m1-adverse-stress-1.0"
COMPONENTS = ("spread_stress", "slippage_stress", "gap_stress", "cost_stress")
SHA = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class StressAdmission:
    status: str
    reason_codes: tuple[str, ...]
    artifact_sha256: str | None
    adverse_stresses: tuple[tuple[str, Decimal], ...]


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def artifact_hash(artifact: Mapping[str, Any]) -> str:
    return canonical_hash({key: value for key, value in artifact.items()
                           if key != "artifact_sha256"})


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC required")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError("UTC required")
    return parsed


def _positive_decimal(value: Any) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("canonical decimal string required")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid decimal") from None
    if not number.is_finite() or number <= 0 or format(number, "f") != value:
        raise ValueError("positive canonical decimal required")
    return number


def admit_stress_artifact(
    artifact: Mapping[str, Any], *, expected_bundle_root_sha256: str,
    now_utc: datetime,
) -> StressAdmission:
    reasons: list[str] = []
    values: list[tuple[str, Decimal]] = []
    if artifact.get("schema_version") != SCHEMA_VERSION:
        reasons.append("STRESS_SCHEMA_INVALID")
    calculated = artifact_hash(artifact)
    if artifact.get("artifact_sha256") != calculated:
        reasons.append("STRESS_ARTIFACT_HASH_MISMATCH")
    if artifact.get("status") != "FROZEN" or artifact.get("holdout_results_viewed") is not False:
        reasons.append("STRESS_NOT_FROZEN_PRE_HOLDOUT")
    scope = artifact.get("scope")
    if (not isinstance(scope, dict) or scope.get("symbol") != "XAUUSD"
            or scope.get("volume_lots") != "0.01" or scope.get("currency") != "USD"
            or not SHA.fullmatch(str(scope.get("contract_spec_sha256", "")))):
        reasons.append("STRESS_SCOPE_INVALID")
    provenance = artifact.get("provenance")
    if (not isinstance(provenance, dict)
            or provenance.get("bundle_root_sha256") != expected_bundle_root_sha256
            or not SHA.fullmatch(str(expected_bundle_root_sha256))
            or not SHA.fullmatch(str(provenance.get("calibration_code_sha256", "")))
            or not SHA.fullmatch(str(provenance.get("config_sha256", "")))
            or not SHA.fullmatch(str(provenance.get("split_map_sha256", "")))):
        reasons.append("STRESS_PROVENANCE_INVALID")
    try:
        train_start = _utc(artifact.get("training_start_utc"))
        train_end = _utc(artifact.get("training_end_utc"))
        frozen = _utc(artifact.get("frozen_at_utc"))
        review_due = _utc(artifact.get("review_due_utc"))
        if not train_start < train_end <= frozen <= now_utc.astimezone(timezone.utc) <= review_due:
            raise ValueError("chronology")
    except (TypeError, ValueError):
        reasons.append("STRESS_CHRONOLOGY_OR_REVIEW_INVALID")
    components = artifact.get("components")
    if not isinstance(components, dict) or set(components) != set(COMPONENTS):
        reasons.append("STRESS_COMPONENT_INVENTORY_INVALID")
        components = {}
    for name in COMPONENTS:
        item = components.get(name)
        if not isinstance(item, dict):
            reasons.append("STRESS_COMPONENT_INVALID")
            continue
        try:
            empirical = _positive_decimal(item.get("empirical_value_usd"))
            selected = _positive_decimal(item.get("selected_value_usd"))
            if selected < empirical:
                reasons.append("STRESS_SELECTED_BELOW_EMPIRICAL")
            if (item.get("method") != "TRAIN_ONLY_EMPIRICAL_QUANTILE"
                    or type(item.get("quantile_basis_points")) is not int
                    or not 1 <= item["quantile_basis_points"] <= 10_000
                    or type(item.get("sample_count")) is not int
                    or item["sample_count"] <= 0
                    or not SHA.fullmatch(str(item.get("evidence_sha256", "")))):
                reasons.append("STRESS_COMPONENT_INVALID")
            values.append((name, selected))
        except ValueError:
            reasons.append("STRESS_COMPONENT_INVALID")
    unique = tuple(dict.fromkeys(reasons))
    return StressAdmission(
        "ADMITTED_SPEC_ONLY" if not unique else "REJECTED",
        unique, calculated if not unique else None, tuple(values) if not unique else (),
    )
