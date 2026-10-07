"""Deterministic decision idempotency with fail-closed key collision handling."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum


class ReservationDisposition(StrEnum):
    NEW = "NEW"
    EXACT_REPLAY = "EXACT_REPLAY"
    CONFLICT_QUARANTINE = "CONFLICT_QUARANTINE"


@dataclass(frozen=True, slots=True)
class DecisionEnvelope:
    decision_id: str
    setup_sha256: str
    account_fingerprint_sha256: str
    symbol_fingerprint_sha256: str
    policy_sha256: str

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id is required")
        for name, value in (
            ("setup_sha256", self.setup_sha256),
            ("account_fingerprint_sha256", self.account_fingerprint_sha256),
            ("symbol_fingerprint_sha256", self.symbol_fingerprint_sha256),
            ("policy_sha256", self.policy_sha256),
        ):
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{name} must be lowercase SHA-256")

    @property
    def envelope_sha256(self) -> str:
        payload = {
            "account_fingerprint_sha256": self.account_fingerprint_sha256,
            "decision_id": self.decision_id,
            "policy_sha256": self.policy_sha256,
            "setup_sha256": self.setup_sha256,
            "symbol_fingerprint_sha256": self.symbol_fingerprint_sha256,
        }
        encoded = json.dumps(
            payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ReservationResult:
    disposition: ReservationDisposition
    decision_id: str
    envelope_sha256: str
    broker_action_permitted: bool = False

    def __post_init__(self) -> None:
        if self.broker_action_permitted:
            raise ValueError("execution-disabled reservations cannot permit broker actions")


@dataclass(frozen=True, slots=True)
class DecisionReservations:
    """Immutable in-memory model suitable for later durable journal projection."""

    by_decision_id: tuple[tuple[str, str], ...] = ()

    def reserve(self, envelope: DecisionEnvelope) -> tuple[DecisionReservations, ReservationResult]:
        known = dict(self.by_decision_id)
        digest = envelope.envelope_sha256
        previous = known.get(envelope.decision_id)
        if previous is None:
            updated = DecisionReservations(
                by_decision_id=tuple(sorted((*self.by_decision_id, (envelope.decision_id, digest))))
            )
            return updated, ReservationResult(
                ReservationDisposition.NEW, envelope.decision_id, digest
            )
        if previous == digest:
            return self, ReservationResult(
                ReservationDisposition.EXACT_REPLAY, envelope.decision_id, digest
            )
        return self, ReservationResult(
            ReservationDisposition.CONFLICT_QUARANTINE, envelope.decision_id, digest
        )
