"""Offline oracle for the selected Sol Analyst runtime contract.

No function in this module performs network, broker, order, credential, or
process operations.  It validates the frozen request profile and minimized
payload before a separately authorized caller could transmit anything.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
        message_count = 0
        output_text_count = 0
        for item in output:
            if type(item) is not dict:
                reasons.append("INVALID_OUTPUT_ITEM")
                continue
            if item.get("type") == "reasoning":
                continue
            if item.get("type") != "message":
                reasons.append("TOOL_OR_UNKNOWN_OUTPUT_ITEM")
                continue
            message_count += 1
            content_items = item.get("content", [])
            if type(content_items) is not list:
                reasons.append("CONTENT_NOT_ARRAY")
                continue
            for content in content_items:
                if type(content) is not dict:
                    reasons.append("INVALID_CONTENT_ITEM")
                    continue
                if content.get("type") == "refusal":
                    reasons.append("REFUSAL")
                elif content.get("type") == "output_text":
                    output_text_count += 1
                    if type(content.get("text")) is not str:
                        reasons.append("OUTPUT_TEXT_NOT_STRING")
                else:
                    reasons.append("UNKNOWN_CONTENT_ITEM")
        if message_count != 1:
            reasons.append("MESSAGE_CARDINALITY")
        if output_text_count != 1:
            reasons.append("OUTPUT_TEXT_CARDINALITY")
    return not reasons, tuple(sorted(set(reasons)))


def _reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _output_text(response: dict) -> str:
    texts = [
        content["text"]
        for item in response.get("output", []) if type(item) is dict
        for content in item.get("content", []) if type(content) is dict
        if content.get("type") == "output_text" and type(content.get("text")) is str
    ]
    if len(texts) != 1:
        raise ValueError("exactly one output_text required")
    return texts[0]


def _exact_keys(value, required: set[str]) -> bool:
    return type(value) is dict and set(value) == required


def _json_depth(value) -> int:
    if type(value) is dict:
        return 1 + max((_json_depth(item) for item in value.values()), default=0)
    if type(value) is list:
        return 1 + max((_json_depth(item) for item in value), default=0)
    return 0


def validate_response_body(response: dict, payload: dict) -> tuple[bool, tuple[str, ...]]:
    """Validate strict output semantics after the provider envelope is accepted."""
    reasons: list[str] = []
    envelope_ok, envelope_reasons = validate_response_envelope(response)
    reasons.extend(envelope_reasons)
    if not envelope_ok:
        return False, tuple(sorted(set(reasons)))
    try:
        text = _output_text(response)
        if len(text.encode("utf-8")) > PROFILE["response_bounds"]["max_body_bytes"]:
            return False, ("OUTPUT_BODY_TOO_LARGE",)
        body = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False, ("OUTPUT_JSON_INVALID",)
    if _json_depth(body) > PROFILE["response_bounds"]["max_json_depth"]:
        reasons.append("OUTPUT_JSON_TOO_DEEP")
    top = {"schema_version", "analysis_id", "snapshot_id", "decision", "reason_codes", "summary", "proposal"}
    if not _exact_keys(body, top):
        reasons.append("OUTPUT_FIELDS")
        return False, tuple(sorted(set(reasons)))
    if body.get("schema_version") != "analyst-runtime-1.0":
        reasons.append("OUTPUT_SCHEMA_VERSION")
    if body.get("analysis_id") != payload.get("analysis_id"):
        reasons.append("ANALYSIS_ID_MISMATCH")
    if body.get("snapshot_id") != payload.get("snapshot_id"):
        reasons.append("SNAPSHOT_ID_MISMATCH")
    decision = body.get("decision")
    if decision not in {"NO_TRADE", "PROPOSE_TRADE"}:
        reasons.append("DECISION_INVALID")
    allowed_reasons = set(OUTPUT_FORMAT["schema"]["properties"]["reason_codes"]["items"]["enum"])
    reason_codes = body.get("reason_codes")
    if (type(reason_codes) is not list or not 1 <= len(reason_codes) <= 8
            or len(set(reason_codes)) != len(reason_codes)
            or any(type(code) is not str or code not in allowed_reasons for code in reason_codes)):
        reasons.append("REASON_CODES_INVALID")
    summary = body.get("summary")
    if type(summary) is not str or not 1 <= len(summary) <= PROFILE["response_bounds"]["max_summary_characters"]:
        reasons.append("SUMMARY_INVALID")
    proposal = body.get("proposal")
    if decision == "NO_TRADE":
        if not _exact_keys(proposal, {"kind", "recheck_condition"}):
            reasons.append("NO_TRADE_PROPOSAL_FIELDS")
        elif (proposal.get("kind") != "NONE"
              or proposal.get("recheck_condition") not in {"NEW_COMPLETED_BAR", "MATERIAL_STATE_CHANGE", "AFTER_EVENT_LOCK", "NONE"}):
            reasons.append("NO_TRADE_PROPOSAL_INVALID")
        if type(reason_codes) is list and "VALID_SETUP" in reason_codes:
            reasons.append("NO_TRADE_REASON_CONFLICT")
    elif decision == "PROPOSE_TRADE":
        trade_fields = {
            "kind", "setup_family", "direction", "entry_type", "entry",
            "invalidation_price", "stop_loss", "targets", "expiry_time_utc",
            "cancellation_conditions", "confidence", "evidence_refs",
        }
        if not _exact_keys(proposal, trade_fields):
            reasons.append("TRADE_PROPOSAL_FIELDS")
        else:
            if proposal.get("kind") != "TRADE":
                reasons.append("TRADE_PROPOSAL_KIND")
            if proposal.get("setup_family") != payload.get("candidate_setup_family"):
                reasons.append("PROPOSAL_FAMILY_MISMATCH")
            if proposal.get("direction") != payload.get("direction"):
                reasons.append("PROPOSAL_DIRECTION_MISMATCH")
            if proposal.get("entry_type") not in {"MARKET_AFTER_CLOSE", "LIMIT", "STOP"}:
                reasons.append("ENTRY_TYPE_INVALID")
            allowed_prices = {
                value for field, value in payload.items()
                if field.endswith("_price") and type(value) is str
            }
            entry = proposal.get("entry")
            if type(entry) is not dict or entry.get("kind") not in {"SINGLE", "RANGE"}:
                reasons.append("ENTRY_INVALID")
            elif entry["kind"] == "SINGLE":
                if not _exact_keys(entry, {"kind", "price"}) or entry.get("price") not in allowed_prices:
                    reasons.append("INVENTED_ENTRY_PRICE")
            elif (not _exact_keys(entry, {"kind", "near_price", "far_price"})
                  or entry.get("near_price") not in allowed_prices
                  or entry.get("far_price") not in allowed_prices):
                reasons.append("INVENTED_ENTRY_PRICE")
            if proposal.get("invalidation_price") not in allowed_prices or proposal.get("stop_loss") not in allowed_prices:
                reasons.append("INVENTED_RISK_PRICE")
            targets = proposal.get("targets")
            expected_targets = [
                {"role": "TP1", "price": payload.get("first_target_price")},
                {"role": "FINAL", "price": payload.get("final_target_price")},
            ]
            if targets != expected_targets:
                reasons.append("TARGET_BINDING")
            try:
                expiry = _utc(proposal.get("expiry_time_utc"))
                snapshot_time = _utc(payload["snapshot_time_utc"])
                if not snapshot_time < expiry <= snapshot_time + PROFILE["deadlines"]["max_proposal_lifetime_seconds"] * timedelta(seconds=1):
                    reasons.append("EXPIRY_INVALID")
            except (KeyError, TypeError, ValueError):
                reasons.append("EXPIRY_INVALID")
            conditions = proposal.get("cancellation_conditions")
            allowed_conditions = set(OUTPUT_FORMAT["schema"]["properties"]["proposal"]["oneOf"][1]["properties"]["cancellation_conditions"]["items"]["enum"])
            if (type(conditions) is not list or not 1 <= len(conditions) <= 8
                    or len(set(conditions)) != len(conditions)
                    or any(item not in allowed_conditions for item in conditions)):
                reasons.append("CANCELLATION_CONDITIONS_INVALID")
            confidence = proposal.get("confidence")
            if type(confidence) is not int or not 0 <= confidence <= 100:
                reasons.append("CONFIDENCE_INVALID")
            refs = proposal.get("evidence_refs")
            if (type(refs) is not list or not 1 <= len(refs) <= 16
                    or len(set(refs)) != len(refs)
                    or not set(refs).issubset(set(payload.get("evidence_ids", [])))):
                reasons.append("EVIDENCE_BINDING")
        if type(reason_codes) is list and "VALID_SETUP" not in reason_codes:
            reasons.append("PROPOSAL_REASON_CONFLICT")
    return not reasons, tuple(sorted(set(reasons)))


def evaluate_chronological_exchange(
    payload: dict,
    response: dict,
    request_time: datetime,
    accept_time: datetime,
    state_fingerprint_at_send: str,
    state_fingerprint_at_accept: str,
    consumed_snapshot_ids: set[str],
) -> dict:
    """Offline, fail-closed acceptance oracle; never grants trading authority."""
    reasons: list[str] = []
    healthy, payload_reasons = validate_payload(payload, request_time)
    reasons.extend(payload_reasons)
    if accept_time < request_time:
        reasons.append("CLOCK_REVERSED")
    try:
        age = accept_time.astimezone(UTC) - _utc(payload["snapshot_time_utc"])
        if age.total_seconds() < 0 or age.total_seconds() > PROFILE["deadlines"]["max_snapshot_age_seconds_at_accept"]:
            reasons.append("RESPONSE_STALE")
    except (KeyError, TypeError, ValueError):
        reasons.append("RESPONSE_STALE")
    if state_fingerprint_at_send != state_fingerprint_at_accept:
        reasons.append("LOCAL_STATE_CHANGED")
    snapshot_id = payload.get("snapshot_id")
    if snapshot_id in consumed_snapshot_ids:
        reasons.append("SNAPSHOT_REPLAY")
    body_ok, body_reasons = validate_response_body(response, payload)
    reasons.extend(body_reasons)
    accepted = healthy and body_ok and not reasons
    if accepted:
        consumed_snapshot_ids.add(snapshot_id)
    return {
        "advisory_accepted": accepted,
        "reason_codes": tuple(sorted(set(reasons))),
        "trading_authorized": False,
    }


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
