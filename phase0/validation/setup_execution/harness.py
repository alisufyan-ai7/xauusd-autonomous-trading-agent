"""Pure deterministic Gate-0 validation models.

No module in this package imports MetaTrader5, performs network I/O, or exposes an
order-sending method.  The models deliberately stop at PASS_CANDIDATE / state
classification and are test oracles for the frozen Phase-0 specifications.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable


FAMILIES = ("TPB", "BRT", "FBR", "RSR", "MOC")
PRECEDENCE = {name: rank for rank, name in enumerate(("FBR", "BRT", "TPB", "RSR", "MOC"))}

COMMON_LOCKS = {
    "data_valid": "DATA_INVALID",
    "snapshot_fresh": "STALE_SNAPSHOT",
    "session_clear": "SESSION_LOCK",
    "spread_clear": "SPREAD_LOCK",
    "volatility_clear": "VOLATILITY_LOCK",
    "news_clear": "NEWS_LOCK",
    "exposure_clear": "UNKNOWN_EXPOSURE",
    "duplicate_clear": "DUPLICATE_SETUP",
}


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def setup_key(snapshot: dict[str, Any]) -> str:
    fields = (
        "strategy_version", "account_fingerprint", "symbol", "family", "direction",
        "anchor_swing_times", "level_prices", "trigger_bar_time",
    )
    return canonical_hash([[field, snapshot[field]] for field in fields])


def evaluate_setup(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a precomputed feature snapshot against the frozen pass contract.

    Feature generation is tested separately by replay.  This oracle ensures every
    required predicate is explicit and fail-closed; absent values are UNKNOWN.
    """
    reasons: list[str] = []
    predicates: dict[str, str] = {}
    for field, reason in COMMON_LOCKS.items():
        value = case.get(field)
        predicates[field] = "TRUE" if value is True else "FALSE" if value is False else "UNKNOWN"
        if value is not True:
            reasons.append(reason)

    family = case.get("family")
    if family not in FAMILIES:
        reasons.append("SPEC_UNRESOLVED")
    for field, reason in (
        ("regime_eligible", "REGIME_INELIGIBLE"),
        ("structure_valid", "STRUCTURE_MISSING"),
        ("location_valid", "LOCATION_INVALID"),
        ("confirmation_valid", "CONFIRMATION_MISSING"),
        ("entry_unexpired", "ENTRY_EXPIRED"),
        ("structure_uninvalidated", "STRUCTURE_INVALIDATED"),
    ):
        value = case.get(field)
        predicates[field] = "TRUE" if value is True else "FALSE" if value is False else "UNKNOWN"
        if value is not True:
            reasons.append(reason)

    if case.get("zone_sequence_clear") is not True:
        predicates["zone_sequence_clear"] = (
            "FALSE" if case.get("zone_sequence_clear") is False else "UNKNOWN"
        )
        reasons.append("ZONE_SEQUENCE_BLOCK")
    else:
        predicates["zone_sequence_clear"] = "TRUE"

    gross = Decimal(str(case.get("gross_rr", "0")))
    costs = Decimal(str(case.get("cost_r", "0")))
    final_net = gross - costs
    tp1_net = Decimal(str(case.get("tp1_gross_rr", "0"))) - costs
    rr_ok = tp1_net >= Decimal("1.5") and final_net >= Decimal("2.0")
    predicates["net_rr_valid"] = "TRUE" if rr_ok else "FALSE"
    if not rr_ok:
        reasons.append("RR_INSUFFICIENT")

    stop = Decimal(str(case.get("stop_distance", "0")))
    min_stop = max(
        Decimal(str(case.get("broker_min_stop", "0"))),
        Decimal(3) * Decimal(str(case.get("tick_size", "0"))),
        Decimal("0.25") * Decimal(str(case.get("atr_m15", "0"))),
    )
    max_stop = Decimal("2.0") * Decimal(str(case.get("atr_h1", "0")))
    stop_ok = min_stop <= stop <= max_stop
    predicates["stop_distance_valid"] = "TRUE" if stop_ok else "FALSE"
    if not stop_ok:
        reasons.append("STRUCTURE_INVALIDATED")

    reasons = list(dict.fromkeys(reasons))
    return {
        "id": case["id"],
        "family": family,
        "direction": case.get("direction"),
        "result": "PASS_CANDIDATE" if not reasons else "NO_TRADE",
        "reason_codes": reasons,
        "predicates": predicates,
        "net_final_rr": str(final_net),
        "setup_key": setup_key(case) if family in FAMILIES else None,
    }


def select_candidate(candidates: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    passing = [c for c in candidates if c["result"] == "PASS_CANDIDATE"]
    if not passing:
        return None
    if len({c["direction"] for c in passing}) != 1:
        return None
    passing.sort(key=lambda c: (-Decimal(c["net_final_rr"]), PRECEDENCE[c["family"]]))
    first = passing[0]
    if len(passing) == 1:
        return first
    delta = Decimal(first["net_final_rr"]) - Decimal(passing[1]["net_final_rr"])
    if delta < Decimal("0.10"):
        tied = [c for c in passing if Decimal(first["net_final_rr"]) - Decimal(c["net_final_rr"]) < Decimal("0.10")]
        tied.sort(key=lambda c: PRECEDENCE[c["family"]])
        return tied[0]
    return first


class State(str, Enum):
    OBSERVED = "OBSERVED"
    PROPOSED = "PROPOSED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    READY = "READY"
    SUBMITTING = "SUBMITTING"
    SUBMISSION_UNCERTAIN = "SUBMISSION_UNCERTAIN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RECONCILED_OPEN = "RECONCILED_OPEN"
    MANAGING = "MANAGING"
    EXIT_SUBMITTING = "EXIT_SUBMITTING"
    EXIT_UNCERTAIN = "EXIT_UNCERTAIN"
    RECONCILED_CLOSED = "RECONCILED_CLOSED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    QUARANTINED = "QUARANTINED"
    INCIDENT = "INCIDENT"


class EventClass(str, Enum):
    NORMAL_TRANSITION = "NORMAL_TRANSITION"
    SAFETY_OBSERVATION = "SAFETY_OBSERVATION"
    PROTOCOL_INVALID = "PROTOCOL_INVALID"
    EVIDENCE_CORRUPTION = "EVIDENCE_CORRUPTION"


TERMINAL = {State.REJECTED, State.EXPIRED, State.CANCELLED, State.RECONCILED_CLOSED}
UNCERTAIN = {State.SUBMISSION_UNCERTAIN, State.EXIT_UNCERTAIN, State.QUARANTINED, State.INCIDENT}

ALLOWED: dict[State, set[State]] = {
    State.OBSERVED: {State.PROPOSED, State.REJECTED},
    State.PROPOSED: {State.REJECTED, State.APPROVED},
    State.APPROVED: {State.READY, State.REJECTED, State.EXPIRED, State.CANCELLED},
    State.READY: {State.SUBMITTING, State.REJECTED, State.EXPIRED, State.CANCELLED},
    State.SUBMITTING: {State.ACKNOWLEDGED, State.SUBMISSION_UNCERTAIN},
    State.ACKNOWLEDGED: {State.RECONCILED_OPEN, State.RECONCILED_CLOSED, State.SUBMISSION_UNCERTAIN},
    State.RECONCILED_OPEN: {State.MANAGING, State.EXIT_SUBMITTING, State.QUARANTINED},
    State.MANAGING: {State.EXIT_SUBMITTING, State.RECONCILED_CLOSED, State.QUARANTINED},
    State.EXIT_SUBMITTING: {State.RECONCILED_CLOSED, State.EXIT_UNCERTAIN},
}


@dataclass
class IntentMachine:
    state: State = State.OBSERVED
    version: int = 0
    attempt_committed: bool = False
    call_claimed: bool = False

    def transition(self, target: State, *, expected_version: int) -> State:
        if expected_version != self.version:
            self.state = State.INCIDENT
            return self.state
        if target not in ALLOWED.get(self.state, set()):
            self.state = State.INCIDENT
            self.version += 1
            return self.state
        if self.state == State.READY and target == State.SUBMITTING:
            if self.attempt_committed:
                self.state = State.INCIDENT
                self.version += 1
                return self.state
            self.attempt_committed = True
        self.state = target
        self.version += 1
        return self.state

    def claim_call(self) -> bool:
        if self.state != State.SUBMITTING or not self.attempt_committed or self.call_claimed:
            return False
        self.call_claimed = True
        return True

    def restart_outcome(self) -> State:
        if self.state == State.READY:
            return State.APPROVED
        if self.state in {State.SUBMITTING, State.SUBMISSION_UNCERTAIN, State.ACKNOWLEDGED,
                          State.EXIT_SUBMITTING, State.EXIT_UNCERTAIN}:
            return State.QUARANTINED
        if self.state in {State.QUARANTINED, State.INCIDENT}:
            return self.state
        if self.state in {State.RECONCILED_OPEN, State.MANAGING}:
            return State.QUARANTINED
        return self.state


def classify_event(*classes: EventClass) -> State | None:
    """Apply the frozen event-class precedence before normal transitions."""
    observed = set(classes)
    if EventClass.EVIDENCE_CORRUPTION in observed or EventClass.PROTOCOL_INVALID in observed:
        return State.INCIDENT
    if EventClass.SAFETY_OBSERVATION in observed:
        return State.QUARANTINED
    return None


def classify_attribution(observation: dict[str, Any]) -> str:
    required = ("account", "symbol", "magic", "fingerprint", "direction", "volume", "linkage")
    matches = [observation.get(field) is True for field in required]
    if all(matches):
        return "OWNED_UNIQUE"
    if observation.get("known_external") is True:
        return "KNOWN_EXTERNAL"
    if any(matches):
        return "CONFLICTING"
    return "UNKNOWN"


def closure_allowed(*, open_volume: Decimal, entry_volume: Decimal, exit_volume: Decimal, history_complete: bool) -> bool:
    return history_complete and open_volume == 0 and entry_volume == exit_volume


def safe_exit_volume(requested: Decimal, remaining: Decimal) -> bool:
    return Decimal("0") < requested <= remaining
