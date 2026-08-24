"""Fail-closed admission oracle for an immutable historical replay corpus.

This module validates bytes supplied by a caller.  It has no network, broker,
model, order, or filesystem-write capability and it does not run a backtest.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


SCHEMA_VERSION = "replay-admission-1.0"
CSV_FIELDS = (
    "timestamp_utc", "receipt_utc",
    "open_bid", "high_bid", "low_bid", "close_bid",
    "open_ask", "high_ask", "low_ask", "close_ask", "tick_volume",
)
REQUIRED_RIGHTS = (
    "automated_use", "local_retention", "derived_data",
    "historical_replay", "internal_audit_retention",
)
ALLOWED_GAP_REASONS = {"SESSION_CLOSED", "HOLIDAY_CLOSED", "PROVIDER_SIDE_MISMATCH"}


@dataclass(frozen=True)
class AdmissionResult:
    status: str
    reason_codes: tuple[str, ...]
    dataset_root_sha256: str | None
    data_files: int
    rows: int
    authorized_gaps: int


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(encoded.encode("utf-8"))


def manifest_hash(manifest: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return canonical_hash(unsigned)


def dataset_root(files: list[dict[str, Any]]) -> str:
    frozen = [[item.get("path"), item.get("sha256"), item.get("bytes"),
               item.get("row_count"), item.get("start_utc"), item.get("end_utc")]
              for item in files]
    return canonical_hash(frozen)


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC timestamp must end in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError("timestamp is not UTC")
    return parsed


def _https(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("https://"):
        return False
    authority = value[8:].split("/", 1)[0]
    return bool(authority) and "@" not in authority and not authority.startswith((".", ":"))


def _hex_digest(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _decimal(row: dict[str, str], field: str) -> Decimal:
    try:
        value = Decimal(row[field])
    except (InvalidOperation, KeyError):
        raise ValueError("invalid decimal") from None
    if not value.is_finite():
        raise ValueError("non-finite decimal")
    return value


def _parse_rows(body: bytes) -> list[dict[str, str]]:
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("data is not UTF-8") from None
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != CSV_FIELDS:
        raise ValueError("unexpected CSV schema")
    rows = list(reader)
    if not rows or any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("empty or malformed CSV")
    return rows


def _quality(row: dict[str, str]) -> tuple[datetime, datetime]:
    market_time, receipt_time = _utc(row["timestamp_utc"]), _utc(row["receipt_utc"])
    if receipt_time < market_time:
        raise ValueError("receipt precedes market time")
    bid = {name: _decimal(row, f"{name}_bid") for name in ("open", "high", "low", "close")}
    ask = {name: _decimal(row, f"{name}_ask") for name in ("open", "high", "low", "close")}
    for side in (bid, ask):
        if side["high"] < max(side["open"], side["close"]) or side["low"] > min(side["open"], side["close"]):
            raise ValueError("invalid OHLC")
        if side["high"] < side["low"] or side["low"] <= 0:
            raise ValueError("invalid price range")
    if any(ask[name] < bid[name] for name in bid):
        raise ValueError("crossed bid/ask")
    try:
        volume = int(row["tick_volume"])
    except ValueError:
        raise ValueError("invalid volume") from None
    if volume < 0 or str(volume) != row["tick_volume"]:
        raise ValueError("invalid volume")
    return market_time, receipt_time


def admit(manifest: Mapping[str, Any], artifacts: Mapping[str, bytes]) -> AdmissionResult:
    """Validate one frozen corpus and return all observed fail-closed reasons."""
    reasons: list[str] = []
    rows_total = 0
    gap_count = 0
    root: str | None = None

    if manifest.get("schema_version") != SCHEMA_VERSION:
        reasons.append("SCHEMA_INVALID")
    if manifest.get("manifest_sha256") != manifest_hash(manifest):
        reasons.append("MANIFEST_HASH_MISMATCH")
    for field in ("dataset_id", "frozen_at_utc"):
        if not manifest.get(field):
            reasons.append("PROVENANCE_INCOMPLETE")
    try:
        _utc(manifest.get("frozen_at_utc"))
    except (TypeError, ValueError):
        reasons.append("PROVENANCE_INCOMPLETE")

    provenance = manifest.get("provenance")
    required_provenance = (
        "provider", "source_uri", "instrument", "instrument_semantics",
        "timezone", "acquisition_method", "terms_identifier",
    )
    if (not isinstance(provenance, dict)
            or any(not provenance.get(field) for field in required_provenance)
            or provenance.get("instrument") != "XAUUSD"
            or provenance.get("timezone") != "UTC"
            or not _https(provenance.get("source_uri"))):
        reasons.append("PROVENANCE_INCOMPLETE")

    rights = manifest.get("rights")
    if (not isinstance(rights, dict)
            or rights.get("review_status") != "APPROVED_FOR_INTERNAL_EVALUATION"
            or any(rights.get(field) is not True for field in REQUIRED_RIGHTS)
            or rights.get("redistribution") is not False
            or not rights.get("reviewed_by")
            or not rights.get("terms_artifact")
            or not _hex_digest(rights.get("terms_sha256"))):
        reasons.append("RIGHTS_NOT_ESTABLISHED")
    else:
        terms = artifacts.get(rights["terms_artifact"])
        if terms is None or sha256_bytes(terms) != rights["terms_sha256"]:
            reasons.append("RIGHTS_EVIDENCE_HASH_MISMATCH")
        try:
            _utc(rights.get("reviewed_utc"))
        except (TypeError, ValueError):
            reasons.append("RIGHTS_NOT_ESTABLISHED")

    registration = manifest.get("registration")
    if (not isinstance(registration, dict)
            or any(not registration.get(field) for field in (
                "trial_id", "strategy_version", "code_sha256", "config_sha256",
                "split_map_sha256", "acceptance_rule_version", "registered_utc",
            ))
            or any(not _hex_digest(registration.get(field)) for field in (
                "code_sha256", "config_sha256", "split_map_sha256",
            ))
            or registration.get("holdout_status") != "SEALED"
            or registration.get("results_viewed") is not False):
        reasons.append("REGISTRATION_INCOMPLETE")
    else:
        try:
            _utc(registration["registered_utc"])
        except ValueError:
            reasons.append("REGISTRATION_INCOMPLETE")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        reasons.append("FILES_INCOMPLETE")
        files = []
    descriptors_valid = all(isinstance(item, dict) for item in files)
    paths = [item.get("path") for item in files if isinstance(item, dict)]
    if (not descriptors_valid or len(paths) != len(set(paths))
            or any(not isinstance(path, str) or not path for path in paths)):
        reasons.append("FILES_INCOMPLETE")
    root = dataset_root(files) if files and descriptors_valid else None
    if manifest.get("dataset_root_sha256") != root:
        reasons.append("DATASET_ROOT_MISMATCH")

    gap_registry: dict[tuple[str, str], dict[str, Any]] = {}
    gaps = manifest.get("authorized_gaps")
    if not isinstance(gaps, list):
        reasons.append("GAP_REGISTRY_INVALID")
        gaps = []
    for gap in gaps:
        if not isinstance(gap, dict):
            reasons.append("GAP_REGISTRY_INVALID")
            continue
        after, before = gap.get("after_utc"), gap.get("before_utc")
        if not isinstance(after, str) or not isinstance(before, str):
            reasons.append("GAP_REGISTRY_INVALID")
            continue
        key = (after, before)
        if (key in gap_registry or gap.get("reason") not in ALLOWED_GAP_REASONS
                or not _https(gap.get("source_uri"))
                or not gap.get("evidence_artifact")
                or not _hex_digest(gap.get("evidence_sha256"))):
            reasons.append("GAP_REGISTRY_INVALID")
            continue
        evidence = artifacts.get(gap["evidence_artifact"])
        if evidence is None or sha256_bytes(evidence) != gap["evidence_sha256"]:
            reasons.append("GAP_EVIDENCE_HASH_MISMATCH")
            continue
        try:
            if _utc(key[1]) <= _utc(key[0]):
                raise ValueError("gap order")
        except (TypeError, ValueError):
            reasons.append("GAP_REGISTRY_INVALID")
            continue
        gap_registry[key] = gap

    period = manifest.get("bar_period_seconds")
    if type(period) is not int or period <= 0:
        reasons.append("CADENCE_INVALID")
        period = 0

    seen: set[str] = set()
    previous: datetime | None = None
    used_gaps: set[tuple[str, str]] = set()
    for descriptor in files:
        if not isinstance(descriptor, dict):
            continue
        path = descriptor.get("path")
        body = artifacts.get(path)
        if (body is None or descriptor.get("bytes") != len(body)
                or descriptor.get("sha256") != sha256_bytes(body)):
            reasons.append("FILE_HASH_OR_SIZE_MISMATCH")
            continue
        try:
            rows = _parse_rows(body)
        except ValueError:
            reasons.append("DATA_SCHEMA_INVALID")
            continue
        if descriptor.get("row_count") != len(rows):
            reasons.append("ROW_COUNT_MISMATCH")
        rows_total += len(rows)
        first_time: datetime | None = None
        last_time: datetime | None = None
        for row in rows:
            try:
                current, _ = _quality(row)
            except ValueError:
                reasons.append("ROW_QUALITY_INVALID")
                continue
            stamp = row["timestamp_utc"]
            if stamp in seen:
                reasons.append("DUPLICATE_TIMESTAMP")
            seen.add(stamp)
            if first_time is None:
                first_time = current
            if previous is not None:
                delta = (current - previous).total_seconds()
                if delta <= 0:
                    reasons.append("NON_CHRONOLOGICAL")
                elif period and delta != period:
                    key = (previous.isoformat().replace("+00:00", "Z"), stamp)
                    if key not in gap_registry:
                        reasons.append("UNEXPLAINED_GAP")
                    else:
                        used_gaps.add(key)
                        gap_count += 1
            previous = current
            last_time = current
        if first_time is not None:
            start = first_time.isoformat().replace("+00:00", "Z")
            end = last_time.isoformat().replace("+00:00", "Z") if last_time else None
            if descriptor.get("start_utc") != start or descriptor.get("end_utc") != end:
                reasons.append("FILE_RANGE_MISMATCH")

    if set(gap_registry) != used_gaps:
        reasons.append("UNUSED_GAP_AUTHORIZATION")
    expected_paths = {path for path in paths if isinstance(path, str)}
    evidence_paths = set()
    if isinstance(rights, dict) and rights.get("terms_artifact"):
        evidence_paths.add(rights["terms_artifact"])
    evidence_paths.update(gap.get("evidence_artifact") for gap in gaps if isinstance(gap, dict) and gap.get("evidence_artifact"))
    if set(artifacts) != expected_paths | evidence_paths:
        reasons.append("ARTIFACT_SET_MISMATCH")

    unique = tuple(dict.fromkeys(reasons))
    return AdmissionResult(
        "ADMITTED" if not unique else "REJECTED",
        unique, root, len(files), rows_total, gap_count,
    )
