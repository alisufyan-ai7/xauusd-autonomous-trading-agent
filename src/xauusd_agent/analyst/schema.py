"""Frozen wire objects for a non-authoritative analyst.

Only derived, allow-listed values belong in ``derived_inputs``.  The analyst can
return NO_TRADE or SETUP; it cannot size risk or authorize execution.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class SchemaError(ValueError):
    """A payload is not an exact instance of the frozen schema."""


class AnalystDecision(StrEnum):
    NO_TRADE = "NO_TRADE"
    SETUP = "SETUP"


_SCALAR_TYPES = (str, int, float, bool)


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SchemaError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{field} must be a non-empty string")
    return value


def _hash(value: str, field: str) -> str:
    value = _nonempty(value, field).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SchemaError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _derived(values: Mapping[str, Any]) -> Mapping[str, str | int | float | bool]:
    if not isinstance(values, Mapping) or not values:
        raise SchemaError("derived_inputs must be a non-empty mapping")
    cleaned: dict[str, str | int | float | bool] = {}
    for key, value in values.items():
        _nonempty(key, "derived_inputs key")
        if type(value) not in _SCALAR_TYPES:
            raise SchemaError(f"derived_inputs[{key!r}] must be a scalar")
        if isinstance(value, float) and not math.isfinite(value):
            raise SchemaError(f"derived_inputs[{key!r}] must be finite")
        cleaned[key] = value
    return MappingProxyType(dict(sorted(cleaned.items())))


@dataclass(frozen=True, slots=True)
class AnalystRequest:
    request_id: str
    observed_at: datetime
    deadline: datetime
    symbol: str
    state_hash: str
    feature_hash: str
    policy_hash: str
    derived_inputs: Mapping[str, str | int | float | bool]
    schema_version: str = "analyst-request-v1"

    def __post_init__(self) -> None:
        if self.schema_version != "analyst-request-v1":
            raise SchemaError("unsupported request schema_version")
        object.__setattr__(self, "request_id", _nonempty(self.request_id, "request_id"))
        object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        object.__setattr__(self, "deadline", _utc(self.deadline, "deadline"))
        if self.deadline <= self.observed_at:
            raise SchemaError("deadline must be after observed_at")
        if self.symbol != "XAUUSD":
            raise SchemaError("symbol must be XAUUSD")
        object.__setattr__(self, "state_hash", _hash(self.state_hash, "state_hash"))
        object.__setattr__(self, "feature_hash", _hash(self.feature_hash, "feature_hash"))
        object.__setattr__(self, "policy_hash", _hash(self.policy_hash, "policy_hash"))
        object.__setattr__(self, "derived_inputs", _derived(self.derived_inputs))

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "observed_at": self.observed_at.isoformat().replace("+00:00", "Z"),
            "deadline": self.deadline.isoformat().replace("+00:00", "Z"),
            "symbol": self.symbol,
            "state_hash": self.state_hash,
            "feature_hash": self.feature_hash,
            "policy_hash": self.policy_hash,
            "derived_inputs": dict(self.derived_inputs),
            "store": False,
            "tools": [],
        }


@dataclass(frozen=True, slots=True)
class AnalystResponse:
    request_id: str
    state_hash: str
    decision: AnalystDecision
    reason_codes: tuple[str, ...]
    schema_version: str = "analyst-response-v1"

    @classmethod
    def parse(cls, raw: str | bytes | Mapping[str, Any]) -> AnalystResponse:
        try:
            loaded = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        except (TypeError, ValueError) as exc:
            raise SchemaError("response is not valid JSON") from exc
        if not isinstance(loaded, Mapping):
            raise SchemaError("response must be a JSON object")
        payload = dict(loaded)
        required = {"schema_version", "request_id", "state_hash", "decision", "reason_codes"}
        if set(payload) != required:
            raise SchemaError("response keys must exactly match the frozen schema")
        codes = payload["reason_codes"]
        if (
            not isinstance(codes, list)
            or not codes
            or any(not isinstance(code, str) or not code.strip() for code in codes)
        ):
            raise SchemaError("reason_codes must be a non-empty string list")
        try:
            decision = AnalystDecision(payload["decision"])
        except (TypeError, ValueError) as exc:
            raise SchemaError("decision must be NO_TRADE or SETUP") from exc
        response = cls(
            schema_version=payload["schema_version"],
            request_id=_nonempty(payload["request_id"], "request_id"),
            state_hash=_hash(payload["state_hash"], "state_hash"),
            decision=decision,
            reason_codes=tuple(codes),
        )
        if response.schema_version != "analyst-response-v1":
            raise SchemaError("unsupported response schema_version")
        return response
