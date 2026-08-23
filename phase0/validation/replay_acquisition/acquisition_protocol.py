"""Fail-closed preregistration and sealing protocol for historical XAUUSD data.

The module validates plans and caller-supplied bytes only.  It cannot connect to
a provider, broker, filesystem, process, model or order API.  A green result is
readiness evidence; it never performs or authorizes acquisition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse


SCHEMA_VERSION = "xauusd-acquisition-plan-1.0"
HEX = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RIGHTS = (
    "automated_use", "local_retention", "derived_data",
    "historical_replay", "internal_audit_retention",
)
TIMEFRAMES = {"H4": (14_400, 300), "H1": (3_600, 500), "M15": (900, 1_000)}
ALLOWED_METHODS = {"HTTPS_EXPORT", "PROVIDER_API_READ_ONLY"}


@dataclass(frozen=True)
class PlanResult:
    status: str
    reason_codes: tuple[str, ...]
    plan_sha256: str | None
    split_map_sha256: str | None


@dataclass(frozen=True)
class InventoryResult:
    status: str
    reason_codes: tuple[str, ...]
    inventory_root_sha256: str | None
    total_bytes: int
    files: int


def canonical_hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def plan_hash(plan: Mapping[str, Any]) -> str:
    return canonical_hash({key: value for key, value in plan.items() if key != "plan_sha256"})


def split_hash(split: Mapping[str, Any]) -> str:
    return canonical_hash(split)


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC Z timestamp required")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError("UTC required")
    return parsed


def _https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None


def _hex(value: Any) -> bool:
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def evaluate_plan(plan: Mapping[str, Any], terms_artifacts: Mapping[str, bytes]) -> PlanResult:
    reasons: list[str] = []
    if plan.get("schema_version") != SCHEMA_VERSION:
        reasons.append("SCHEMA_INVALID")
    actual_plan_hash = plan_hash(plan)
    if plan.get("plan_sha256") != actual_plan_hash:
        reasons.append("PLAN_HASH_MISMATCH")
    try:
        registered = _utc(plan.get("registered_utc"))
    except (TypeError, ValueError):
        registered = None
        reasons.append("REGISTRATION_TIME_INVALID")

    provider = plan.get("provider")
    if (not isinstance(provider, dict)
            or any(not provider.get(key) for key in (
                "name", "legal_entity", "source_uri", "instrument_semantics",
                "terms_identifier",
            ))
            or provider.get("instrument") != "XAUUSD"
            or provider.get("timezone") != "UTC"
            or provider.get("price_content") not in {"TICK_BID_ASK", "BAR_BID_ASK"}
            or provider.get("entitlement_status") != "DOCUMENTED_ACTIVE"
            or not _https(provider.get("source_uri"))):
        reasons.append("PROVIDER_OR_ENTITLEMENT_INCOMPLETE")

    rights = plan.get("rights")
    if (not isinstance(rights, dict)
            or rights.get("review_status") != "APPROVED_FOR_INTERNAL_EVALUATION"
            or any(rights.get(key) is not True for key in REQUIRED_RIGHTS)
            or rights.get("redistribution") is not False
            or rights.get("termination_retention") != "EXPLICITLY_PERMITTED"
            or not rights.get("reviewed_by_role")
            or not _https(rights.get("terms_uri"))
            or not _hex(rights.get("terms_sha256"))
            or not isinstance(rights.get("terms_artifact"), str)):
        reasons.append("RIGHTS_NOT_ESTABLISHED")
    else:
        try:
            date.fromisoformat(rights["terms_effective_date"])
            reviewed = _utc(rights["reviewed_utc"])
            if registered is not None and reviewed > registered:
                reasons.append("RIGHTS_REVIEW_AFTER_REGISTRATION")
        except (KeyError, TypeError, ValueError):
            reasons.append("RIGHTS_NOT_ESTABLISHED")
        body = terms_artifacts.get(rights["terms_artifact"])
        if body is None or sha256_bytes(body) != rights["terms_sha256"]:
            reasons.append("RIGHTS_EVIDENCE_HASH_MISMATCH")

    acquisition = plan.get("acquisition")
    try:
        acquisition_start = _utc(acquisition["start_utc"])
        acquisition_end = _utc(acquisition["end_utc"])
        valid_acquisition = acquisition_start < acquisition_end
    except (KeyError, TypeError, ValueError):
        valid_acquisition = False
        acquisition_start = acquisition_end = None
    if (not isinstance(acquisition, dict) or not valid_acquisition
            or acquisition.get("method") not in ALLOWED_METHODS
            or acquisition.get("http_method") != "GET"
            or acquisition.get("output_outside_repository") is not True
            or acquisition.get("raw_bytes_preserved") is not True
            or acquisition.get("immutable_after_seal") is not True
            or acquisition.get("credentials_in_manifest") is not False):
        reasons.append("ACQUISITION_PROCEDURE_INVALID")

    frames = plan.get("timeframes")
    if not isinstance(frames, dict) or set(frames) != set(TIMEFRAMES):
        reasons.append("TIMEFRAME_INVENTORY_INVALID")
    else:
        for name, (period, minimum) in TIMEFRAMES.items():
            row = frames[name]
            if (not isinstance(row, dict) or row.get("period_seconds") != period
                    or type(row.get("minimum_rows")) is not int
                    or row["minimum_rows"] < minimum
                    or row.get("derivation") != "DETERMINISTIC_FROM_ADMITTED_SOURCE"):
                reasons.append(f"{name}_PROCEDURE_INVALID")

    split = plan.get("split")
    split_digest = split_hash(split) if isinstance(split, dict) else None
    split_names = (
        "train_start_utc", "train_end_utc", "validation_start_utc",
        "validation_end_utc", "embargo_start_utc", "embargo_end_utc",
        "holdout_start_utc", "holdout_end_utc",
    )
    try:
        split_times = [_utc(split[name]) for name in split_names]
        ordered = all(left < right for left, right in zip(split_times, split_times[1:]))
    except (KeyError, TypeError, ValueError):
        split_times = []
        ordered = False
    if (not isinstance(split, dict) or split.get("sealed") is not True or not ordered
            or type(split.get("purge_seconds")) is not int or split["purge_seconds"] <= 0
            or type(split.get("embargo_seconds")) is not int or split["embargo_seconds"] <= 0
            or plan.get("split_map_sha256") != split_digest):
        reasons.append("SPLIT_NOT_PREREGISTERED")
    elif acquisition_start is not None and acquisition_end is not None:
        if split_times[0] < acquisition_start or split_times[-1] > acquisition_end:
            reasons.append("SPLIT_OUTSIDE_ACQUISITION_RANGE")

    registration = plan.get("registration")
    if (not isinstance(registration, dict)
            or registration.get("holdout_status") != "SEALED_UNVIEWED"
            or registration.get("results_viewed") is not False
            or registration.get("random_split") is not False
            or any(not _hex(registration.get(key)) for key in (
                "code_sha256", "config_sha256", "acceptance_rules_sha256",
            ))):
        reasons.append("TRIAL_REGISTRATION_INVALID")

    transforms = plan.get("transformations")
    if (not isinstance(transforms, dict)
            or transforms.get("raw_bytes_immutable") is not True
            or transforms.get("deterministic") is not True
            or transforms.get("bid_ask_preserved") is not True
            or transforms.get("forming_bars_excluded") is not True
            or not _hex(transforms.get("code_sha256"))):
        reasons.append("TRANSFORMATION_CONTRACT_INVALID")

    unique = tuple(dict.fromkeys(reasons))
    return PlanResult(
        "READY_FOR_AUTHORIZED_ACQUISITION" if not unique else "FAIL_CLOSED",
        unique,
        actual_plan_hash if not unique else None,
        split_digest if not unique else None,
    )


def inventory_root(descriptors: list[dict[str, Any]]) -> str:
    frozen = [[row.get("path"), row.get("sha256"), row.get("bytes")]
              for row in descriptors]
    return canonical_hash(frozen)


def verify_sealed_inventory(
    descriptors: list[dict[str, Any]], artifacts: Mapping[str, bytes], declared_root: str,
) -> InventoryResult:
    reasons: list[str] = []
    paths = [row.get("path") for row in descriptors if isinstance(row, dict)]
    if (not descriptors or len(paths) != len(descriptors) or len(paths) != len(set(paths))
            or set(paths) != set(artifacts)):
        reasons.append("INVENTORY_MISMATCH")
    total = 0
    for row in descriptors:
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        body = artifacts.get(path)
        if (not isinstance(path, str) or not path or body is None
                or row.get("bytes") != len(body)
                or row.get("sha256") != sha256_bytes(body)):
            reasons.append("ARTIFACT_HASH_OR_SIZE_MISMATCH")
            continue
        total += len(body)
    root = inventory_root(descriptors) if descriptors else None
    if declared_root != root:
        reasons.append("INVENTORY_ROOT_MISMATCH")
    unique = tuple(dict.fromkeys(reasons))
    return InventoryResult("SEALED" if not unique else "FAIL_CLOSED", unique,
                           root if not unique else None, total, len(descriptors))
