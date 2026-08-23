"""Offline oracle for the selected Sol Analyst runtime contract.

No function in this module performs network, broker, order, credential, or
process operations.  It validates the frozen request profile and minimized
payload before a separately authorized caller could transmit anything.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).parent
PROFILE = json.loads((ROOT / "ANALYST_RUNTIME_PROFILE_V1.json").read_text(encoding="utf-8"))
REGISTER = json.loads((ROOT / "ANALYST_FIELD_REGISTER_V1.json").read_text(encoding="utf-8"))
OUTPUT_FORMAT = json.loads((ROOT / "ANALYST_OUTPUT_SCHEMA_V1.json").read_text(encoding="utf-8"))
UTC = timezone.utc
DOMAIN = "analyst-runtime-1.0|minimized-snapshot|"

FORBIDDEN_TERMS = (
    "account_number", "account number", "account_login", "ticket_id", "order_id",
    "position_id", "deal_id", "server_id", "broker_server", "exact_balance",
    "exact_equity", "free_margin", "leverage", "lot_size", "volume", "password",
    "api_key", "secret", "email", "phone", "hostname", "ip_address", "filesystem_path",
)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def derive_snapshot_id(payload_without_bound_id: dict) -> str:
    value = dict(payload_without_bound_id)
    value.pop("snapshot_id", None)
    value.pop("analysis_id", None)
    return hashlib.sha256((DOMAIN + canonical(value)).encode("utf-8")).hexdigest()


def expected_fields(family: str) -> set[str]:
    return set(REGISTER["common_fields"]) | set(REGISTER["families"][family])


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value
    ):
        raise ValueError("invalid UTC second timestamp")
    return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)


def _valid_field(value, spec: dict) -> bool:
    kind = spec["type"]
    if kind == "boolean":
        return type(value) is bool
    if kind == "integer":
        return type(value) is int and spec["minimum"] <= value <= spec["maximum"]
    if kind == "enum":
        return type(value) is str and value in spec["values"]
    if kind == "uuid_v4":
        return type(value) is str and re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", value
        ) is not None
    if kind == "sha256":
        return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    if kind == "utc":
        try:
            _utc(value)
            return True
        except (TypeError, ValueError):
            return False
    if kind == "decimal_string":
        if type(value) is not str or re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]{1,5})?", value) is None:
            return False
        try:
            number = Decimal(value)
            return Decimal(spec["minimum"]) <= number <= Decimal(spec["maximum"])
        except InvalidOperation:
            return False
    if kind == "array_opaque_id":
        if type(value) is not list or not spec["minimum_items"] <= len(value) <= spec["maximum_items"]:
            return False
        return len(set(value)) == len(value) and all(
            type(item) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,32}", item) for item in value
        )
    return False


def validate_payload(payload: dict, now: datetime) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if type(payload) is not dict:
        return False, ("PAYLOAD_NOT_OBJECT",)
    family = payload.get("candidate_setup_family")
    if family not in REGISTER["families"]:
        return False, ("UNKNOWN_FAMILY",)
    expected = expected_fields(family)
    actual = set(payload)
    if actual != expected:
        if expected - actual:
            reasons.append("MISSING_FIELDS")
        if actual - expected:
            reasons.append("EXTRA_FIELDS")
    for field in sorted(expected & actual):
        if not _valid_field(payload[field], REGISTER["field_definitions"][field]):
            reasons.append(f"INVALID_FIELD:{field}")
    lowered = canonical(payload).lower()
    if any(term in lowered for term in FORBIDDEN_TERMS):
        reasons.append("PROHIBITED_DATA")
    if payload.get("snapshot_id") != derive_snapshot_id(payload):
        reasons.append("SNAPSHOT_HASH")
    try:
        age = now.astimezone(UTC) - _utc(payload["snapshot_time_utc"])
        maximum = PROFILE["deadlines"]["max_snapshot_age_seconds_at_send"]
        if age.total_seconds() < -1 or age.total_seconds() > maximum:
            reasons.append("STALE_OR_FUTURE_SNAPSHOT")
    except (KeyError, TypeError, ValueError):
        pass
    gates = {
        "spread_state": "NORMAL",
        "volatility_state": "NORMAL",
        "session_state": "OPEN",
        "event_guard_state": "HEALTHY",
        "new_risk_allowed_locally": True,
        "unknown_exposure_present": False,
        "daily_limit_state": "CLEAR",
        "weekly_limit_state": "CLEAR",
        "drawdown_state": "CLEAR",
        "loss_pause_state": "CLEAR",
    }
    if any(payload.get(field) != required for field, required in gates.items()):
        reasons.append("LOCAL_GATE_BLOCKED")
    required_true = [
        field for field in REGISTER["families"][family]
        if REGISTER["field_definitions"][field]["type"] == "boolean"
    ]
    if any(payload.get(field) is not True for field in required_true):
        reasons.append("FAMILY_PREDICATE_NOT_TRUE")
    regime = payload.get("regime")
    direction = payload.get("direction")
    if family in {"TPB", "BRT", "MOC"}:
        required_regime = "UP_TREND" if direction == "BUY" else "DOWN_TREND"
        if regime != required_regime:
            reasons.append("REGIME_DIRECTION_MISMATCH")
    if family == "RSR" and regime != "RANGE":
        reasons.append("REGIME_FAMILY_MISMATCH")
    return not reasons, tuple(sorted(set(reasons)))


def build_request(payload: dict, prompt: str, now: datetime) -> dict:
    healthy, reasons = validate_payload(payload, now)
    if not healthy:
        raise ValueError("LOCAL_NO_CALL:" + ",".join(reasons))
    request_profile = PROFILE["request"]
    return {
        "model": PROFILE["model"],
        "store": request_profile["store"],
        "tools": request_profile["tools"],
        "reasoning": request_profile["reasoning"],
        "max_output_tokens": request_profile["max_output_tokens"],
        "stream": request_profile["stream"],
        "background": request_profile["background"],
        "truncation": request_profile["truncation"],
        "service_tier": request_profile["service_tier"],
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": canonical(payload)}]},
        ],
        "text": {"format": OUTPUT_FORMAT},
    }


def validate_response_envelope(response: dict) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if response.get("status") != PROFILE["response_bounds"]["required_status"]:
        reasons.append("RESPONSE_NOT_COMPLETED")
    if response.get("model") != PROFILE["model"]:
        reasons.append("MODEL_MISMATCH")
    if response.get("incomplete_details") is not None:
        reasons.append("INCOMPLETE_DETAILS")
    output = response.get("output")
    if type(output) is not list:
        reasons.append("OUTPUT_NOT_ARRAY")
    else:
        for item in output:
            if item.get("type") != "message":
                reasons.append("TOOL_OR_UNKNOWN_OUTPUT_ITEM")
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    reasons.append("REFUSAL")
                elif content.get("type") != "output_text":
                    reasons.append("UNKNOWN_CONTENT_ITEM")
    return not reasons, tuple(sorted(set(reasons)))


def reserve_standard_cost(input_token_upper_bound: int) -> Decimal:
    if type(input_token_upper_bound) is not int or input_token_upper_bound < 0:
        raise ValueError("non-negative integer token bound required")
    price = PROFILE["pricing_control"]
    inp = Decimal(price["standard_input_usd_per_million_tokens"])
    out = Decimal(price["standard_output_usd_per_million_tokens"])
    max_out = PROFILE["request"]["max_output_tokens"]
    if input_token_upper_bound > price["long_context_threshold_input_tokens"]:
        inp *= Decimal(price["long_context_input_multiplier"])
        out *= Decimal(price["long_context_output_multiplier"])
    return (Decimal(input_token_upper_bound) * inp + Decimal(max_out) * out) / Decimal(1_000_000)


def strict_object_tree(schema: dict) -> bool:
    """Every object node must reject extra properties and require its fields."""
    if type(schema) is dict:
        if schema.get("type") == "object":
            if schema.get("additionalProperties") is not False:
                return False
            if set(schema.get("properties", {})) != set(schema.get("required", [])):
                return False
        return all(strict_object_tree(value) for value in schema.values())
    if type(schema) is list:
        return all(strict_object_tree(value) for value in schema)
    return True


def artifact_fingerprints(prompt: str) -> dict[str, str]:
    return {
        "profile_sha256": hashlib.sha256(canonical(PROFILE).encode()).hexdigest(),
        "field_register_sha256": hashlib.sha256(canonical(REGISTER).encode()).hexdigest(),
        "output_format_sha256": hashlib.sha256(canonical(OUTPUT_FORMAT).encode()).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    }


def revalidation_required(previous: dict[str, str], current: dict[str, str]) -> bool:
    return previous != current
