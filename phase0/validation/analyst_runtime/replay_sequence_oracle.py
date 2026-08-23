"""Chronological non-trading Analyst sequence oracle for an admitted replay.

This wrapper composes the frozen per-exchange contract over a registered
sequence.  It never calls OpenAI or a broker and always reports
``trading_authorized`` false, including for accepted advisory responses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from phase0.validation.analyst_runtime.runtime_contract_oracle import (
    evaluate_chronological_exchange,
)


FAMILIES = {"TPB", "BRT", "FBR", "RSR", "MOC"}
LOCAL_BLOCKS = {"EVENT_LOCK", "UNKNOWN_EXPOSURE", "LOCAL_GATE_BLOCKED", "UNTRUSTED_INPUT"}
SHA = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SequenceResult:
    status: str
    reason_codes: tuple[str, ...]
    accepted_advisories: int
    rejected_responses: int
    local_no_calls: int
    trading_authorized: bool
    case_results: tuple[tuple[str, bool, tuple[str, ...]], ...]


def evaluate_registered_sequence(
    *, bundle_admission_status: str, bundle_root_sha256: str,
    exchanges: Sequence[dict[str, Any]],
) -> SequenceResult:
    reasons: list[str] = []
    case_results: list[tuple[str, bool, tuple[str, ...]]] = []
    accepted = rejected = local_no_calls = 0
    if bundle_admission_status != "ADMITTED" or not SHA.fullmatch(str(bundle_root_sha256)):
        reasons.append("REPLAY_BUNDLE_NOT_ADMITTED")
    if not exchanges:
        reasons.append("SEQUENCE_EMPTY")
    case_ids: set[str] = set()
    analysis_ids: set[str] = set()
    consumed: set[str] = set()
    observed_families: set[str] = set()
    previous_snapshot: datetime | None = None
    for exchange in exchanges:
        case_id = exchange.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            reasons.append("CASE_ID_INVALID_OR_DUPLICATE")
            case_id = str(case_id)
        case_ids.add(case_id)
        expected = exchange.get("expected_advisory_accepted")
        if type(expected) is not bool:
            reasons.append("EXPECTED_RESULT_MISSING")
            expected = False
        if exchange.get("kind") == "LOCAL_NO_CALL":
            local_reasons: list[str] = []
            if exchange.get("response") is not None:
                local_reasons.append("LOCAL_BLOCK_HAS_RESPONSE")
            if exchange.get("local_reason") not in LOCAL_BLOCKS:
                local_reasons.append("LOCAL_BLOCK_REASON_INVALID")
            if expected is not False:
                local_reasons.append("LOCAL_BLOCK_EXPECTATION_INVALID")
            local_no_calls += 1
            case_results.append((case_id, False, tuple(local_reasons or [exchange["local_reason"]])))
            reasons.extend(local_reasons)
            continue
        if exchange.get("kind") != "PROVIDER_RESPONSE":
            reasons.append("EXCHANGE_KIND_INVALID")
            case_results.append((case_id, False, ("EXCHANGE_KIND_INVALID",)))
            rejected += 1
            continue
        payload = exchange.get("payload")
        if not isinstance(payload, dict):
            reasons.append("PAYLOAD_MISSING")
            case_results.append((case_id, False, ("PAYLOAD_MISSING",)))
            rejected += 1
            continue
        observed_families.add(str(payload.get("candidate_setup_family")))
        analysis_id = payload.get("analysis_id")
        analysis_issue = not isinstance(analysis_id, str) or analysis_id in analysis_ids
        analysis_ids.add(str(analysis_id))
        request_time = exchange.get("request_time")
        accept_time = exchange.get("accept_time")
        try:
            snapshot = datetime.fromisoformat(payload["snapshot_time_utc"].replace("Z", "+00:00"))
            sequence_reason = snapshot <= previous_snapshot if previous_snapshot is not None else False
            previous_snapshot = snapshot
        except (KeyError, TypeError, ValueError):
            sequence_reason = True
        if not isinstance(request_time, datetime) or not isinstance(accept_time, datetime):
            result = {"advisory_accepted": False,
                      "reason_codes": ("EXCHANGE_TIME_INVALID",), "trading_authorized": False}
        else:
            result = evaluate_chronological_exchange(
                payload, exchange.get("response"), request_time, accept_time,
                str(exchange.get("state_fingerprint_at_send")),
                str(exchange.get("state_fingerprint_at_accept")), consumed,
            )
        exchange_reasons = list(result["reason_codes"])
        observed = bool(result["advisory_accepted"])
        if analysis_issue:
            exchange_reasons.append("ANALYSIS_ID_INVALID_OR_DUPLICATE")
            observed = False
        if sequence_reason:
            exchange_reasons.append("SEQUENCE_SNAPSHOT_NOT_STRICTLY_INCREASING")
            observed = False
        if result.get("trading_authorized") is not False:
            reasons.append("TRADING_AUTHORIZATION_INVARIANT_BROKEN")
        if observed != expected:
            reasons.append("REGISTERED_EXPECTATION_MISMATCH")
        if observed:
            accepted += 1
        else:
            rejected += 1
        case_results.append((case_id, observed, tuple(sorted(set(exchange_reasons)))))
    if observed_families != FAMILIES:
        reasons.append("FAMILY_SEQUENCE_INCOMPLETE")
    unique = tuple(dict.fromkeys(reasons))
    return SequenceResult(
        "PASS_NON_TRADING" if not unique else "REJECTED",
        unique, accepted, rejected, local_no_calls, False, tuple(case_results),
    )
