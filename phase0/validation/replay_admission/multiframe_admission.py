"""Admission oracle for one sealed H4/H1/M15 replay bundle.

Each child timeframe must first pass the byte-level replay-admission oracle.
This layer then proves exact timeframe inventory, minimum warm-up rows, common
provider/instrument/rights semantics, a preregistered chronological split and a
bundle root.  It has no network, broker, model, file-write or replay capability.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from admission import admit


SCHEMA_VERSION = "replay-multiframe-bundle-1.0"
REQUIRED = {"H4": (14_400, 300), "H1": (3_600, 500), "M15": (900, 1000)}


@dataclass(frozen=True)
class BundleResult:
    status: str
    reason_codes: tuple[str, ...]
    bundle_root_sha256: str | None
    child_rows: tuple[tuple[str, int], ...]


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def split_hash(split: Mapping[str, Any]) -> str:
    return canonical_hash(split)


def bundle_root(timeframes: Mapping[str, Any]) -> str:
    frozen = [[name, timeframes[name].get("dataset_id"),
               timeframes[name].get("dataset_root_sha256")]
              for name in sorted(timeframes)]
    return canonical_hash(frozen)


def bundle_hash(bundle: Mapping[str, Any]) -> str:
    return canonical_hash({key: value for key, value in bundle.items()
                           if key != "bundle_manifest_sha256"})


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC required")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError("UTC required")
    return parsed


def admit_multiframe_bundle(
    bundle: Mapping[str, Any],
    child_manifests: Mapping[str, Mapping[str, Any]],
    child_artifacts: Mapping[str, Mapping[str, bytes]],
) -> BundleResult:
    reasons: list[str] = []
    row_counts: list[tuple[str, int]] = []
    if bundle.get("schema_version") != SCHEMA_VERSION:
        reasons.append("BUNDLE_SCHEMA_INVALID")
    if bundle.get("bundle_manifest_sha256") != bundle_hash(bundle):
        reasons.append("BUNDLE_HASH_MISMATCH")
    declared = bundle.get("timeframes")
    if not isinstance(declared, dict) or set(declared) != set(REQUIRED):
        reasons.append("TIMEFRAME_INVENTORY_INVALID")
        declared = {}
    if set(child_manifests) != set(REQUIRED) or set(child_artifacts) != set(REQUIRED):
        reasons.append("CHILD_INVENTORY_INVALID")

    split = bundle.get("split")
    split_valid = isinstance(split, dict) and split.get("sealed") is True
    split_fields = ("train_start_utc", "train_end_utc", "embargo_end_utc", "holdout_end_utc")
    try:
        times = [_utc(split[field]) for field in split_fields] if split_valid else []
        if len(times) != 4 or not times[0] < times[1] < times[2] < times[3]:
            raise ValueError("split order")
    except (KeyError, TypeError, ValueError):
        split_valid = False
        times = []
    expected_split_hash = split_hash(split) if isinstance(split, dict) else None
    if not split_valid or bundle.get("split_map_sha256") != expected_split_hash:
        reasons.append("SPLIT_MAP_INVALID")

    providers: set[str] = set()
    semantics: set[str] = set()
    terms: set[str] = set()
    dataset_ids: set[str] = set()
    for name, (period, minimum) in REQUIRED.items():
        manifest = child_manifests.get(name)
        artifacts = child_artifacts.get(name)
        if not isinstance(manifest, Mapping) or not isinstance(artifacts, Mapping):
            reasons.append("CHILD_MISSING_OR_INVALID")
            continue
        result = admit(manifest, artifacts)
        row_counts.append((name, result.rows))
        if result.status != "ADMITTED":
            reasons.append(f"{name}_CHILD_NOT_ADMITTED")
        if manifest.get("bar_period_seconds") != period or result.rows < minimum:
            reasons.append(f"{name}_WARMUP_OR_CADENCE_INVALID")
        provenance = manifest.get("provenance", {})
        rights = manifest.get("rights", {})
        registration = manifest.get("registration", {})
        providers.add(str(provenance.get("provider")))
        semantics.add(str(provenance.get("instrument_semantics")))
        terms.add(str(rights.get("terms_sha256")))
        dataset_ids.add(str(manifest.get("dataset_id")))
        if (provenance.get("instrument") != "XAUUSD"
                or registration.get("split_map_sha256") != bundle.get("split_map_sha256")):
            reasons.append("CHILD_BINDING_MISMATCH")
        descriptor = declared.get(name, {}) if isinstance(declared, dict) else {}
        if (descriptor.get("dataset_id") != manifest.get("dataset_id")
                or descriptor.get("dataset_root_sha256") != result.dataset_root_sha256):
            reasons.append("CHILD_ROOT_MISMATCH")
        files = manifest.get("files", [])
        try:
            child_start = min(_utc(item["start_utc"]) for item in files)
            child_end = max(_utc(item["end_utc"]) for item in files)
            if split_valid and (child_start > times[0] or child_end < times[3]):
                reasons.append("SPLIT_COVERAGE_INCOMPLETE")
        except (KeyError, TypeError, ValueError):
            reasons.append("SPLIT_COVERAGE_INCOMPLETE")

    if len(dataset_ids) != 3:
        reasons.append("CHILD_DATASET_ID_COLLISION")
    if len(providers) != 1 or len(semantics) != 1 or len(terms) != 1:
        reasons.append("CROSS_TIMEFRAME_PROVENANCE_OR_RIGHTS_MISMATCH")
    root = bundle_root(declared) if declared and set(declared) == set(REQUIRED) else None
    if bundle.get("bundle_root_sha256") != root:
        reasons.append("BUNDLE_ROOT_MISMATCH")
    unique = tuple(dict.fromkeys(reasons))
    return BundleResult("ADMITTED" if not unique else "REJECTED", unique, root,
                        tuple(sorted(row_counts)))
