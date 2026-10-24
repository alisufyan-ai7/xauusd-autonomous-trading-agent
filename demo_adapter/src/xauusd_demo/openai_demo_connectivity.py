"""Preflight the EXACT OpenAI API project and structured Responses capability.

Discovery uses the key's actual /v1/models listing; no assumptions that a
model shown in public pricing is enabled for a given service-account key.
Probe may consume a few billable tokens but can never call MT5 or trade.
Never log key, headers, response body or bearer-bearing request URLs.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .envelope import DemoSafetyError

# Preferred order: inexpensive Luna, stronger Sol, established mini APIs.
# The live trader must pin this selected identifier, not silently switch.
CANDIDATE_MODELS: tuple[str, ...] = (
    # Confirmed in the OWNER'S OpenAI API project allowlist (2026-10-24).
    # Luna first for the least expensive frequent setup confirmation.
    # Terra / Sol are permissible explicit fallbacks if actually listed
    # by this key AND a strict Responses test succeeds.
    "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol",
)

_PING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["READY"]},
    },
    "required": ["status"],
    "additionalProperties": False,
}


def _json_request(
    *, api_key: str, path: str, payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(
        payload, separators=(",", ":"),
    ).encode("utf-8")
    headers = {"Authorization": "Bearer " + api_key}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        "https://api.openai.com" + path,
        data=body, headers=headers,
        method="POST" if body is not None else "GET",
    )
    # HTTPS origin and paths are fixed by this module; no user-controlled URL.
    with urllib.request.urlopen(request, timeout=18) as result:  # noqa: S310
        if result.status != 200:
            raise DemoSafetyError("OPENAI_HTTP_" + str(result.status))
        parsed = json.loads(result.read(131072))
    if type(parsed) is not dict:
        raise DemoSafetyError("OPENAI_JSON_OBJECT_REQUIRED")
    return parsed


def select_verified_model(
    api_key: str, *, preferred: str | None = None,
) -> str:
    if not api_key or len(api_key) < 20:
        raise DemoSafetyError("OPENAI_KEY_MISSING_OR_INVALID_FORMAT")
    if preferred is not None and preferred not in CANDIDATE_MODELS:
        raise DemoSafetyError("OPENAI_MODEL_NOT_IN_REVIEWED_SET")
    try:
        listing = _json_request(api_key=api_key, path="/v1/models")
    except urllib.error.HTTPError as exc:
        raise DemoSafetyError(
            "OPENAI_MODELS_LIST_HTTP_" + str(exc.code)
        ) from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise DemoSafetyError("OPENAI_MODELS_LIST_UNAVAILABLE") from exc
    records = listing.get("data")
    if not isinstance(records, list):
        raise DemoSafetyError("OPENAI_MODELS_LIST_INVALID")
    names = {
        row["id"]
        for row in records
        if type(row) is dict and type(row.get("id")) is str
    }
    candidates = (
        (preferred,) if preferred is not None
        else CANDIDATE_MODELS
    )
    choices = [name for name in candidates if name in names]
    if not choices:
        raise DemoSafetyError(
            "OPENAI_PROJECT_KEY_HAS_NO_ALLOWED_GPT56_MODEL_VISIBLE"
        )

    for model in choices:
        payload = {
            "model": model,
            "instructions": (
                "Connectivity test only. Do not make a trade decision. "
                "Return status READY in the strict supplied JSON schema."
            ),
            "input": "Reply with status READY for API health verification.",
            "store": False,
            "max_output_tokens": 1024,
            "reasoning": {"effort": "low"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "demo_api_health",
                    "strict": True,
                    "schema": _PING_SCHEMA,
                },
            },
        }
        try:
            response = _json_request(
                api_key=api_key, path="/v1/responses", payload=payload,
            )
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404, 422):
                # Model listed, but this endpoint/format is not admissible.
                continue
            raise DemoSafetyError(
                "OPENAI_RESPONSES_HTTP_" + str(exc.code)
            ) from None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise DemoSafetyError(
                "OPENAI_RESPONSES_CONNECTIVITY_FAILED"
            ) from exc
        if response.get("status") != "completed":
            continue
        output = [
            item.get("text")
            for node in response.get("output", [])
            if isinstance(node, dict) and node.get("type") == "message"
            for item in node.get("content", [])
            if isinstance(item, dict) and item.get("type") == "output_text"
        ]
        if len(output) != 1 or type(output[0]) is not str:
            continue
        try:
            result = json.loads(output[0])
        except (ValueError, TypeError):
            continue
        if result == {"status": "READY"}:
            return model
    raise DemoSafetyError(
        "OPENAI_NO_CANDIDATE_PASSED_STRUCTURED_RESPONSES_PROBE"
    )
