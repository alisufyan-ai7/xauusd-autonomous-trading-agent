"""Fail-closed orchestration around the strict analyst boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .schema import AnalystDecision, AnalystRequest, AnalystResponse
from .transport import AnalystTransport, DisabledAnalystTransport


@dataclass(frozen=True, slots=True)
class AnalystVerdict:
    decision: AnalystDecision
    admissible: bool
    reason_codes: tuple[str, ...]


class AnalystClient:
    def __init__(self, transport: AnalystTransport | None = None, *, timeout_seconds: float = 2.0):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._transport = transport or DisabledAnalystTransport()
        self._timeout_seconds = timeout_seconds

    def evaluate(self, request: AnalystRequest, *, now: datetime | None = None) -> AnalystVerdict:
        if now is not None and (now.tzinfo is None or now.utcoffset() is None):
            return self._reject("ANALYST_CLOCK_INVALID")
        evaluated_at = (now or datetime.now(UTC)).astimezone(UTC)
        if evaluated_at > request.deadline:
            return self._reject("ANALYST_DEADLINE_EXPIRED")
        remaining = (request.deadline - evaluated_at).total_seconds()
        try:
            raw = self._transport.send(
                request.to_payload(), timeout_seconds=min(self._timeout_seconds, remaining)
            )
            response = AnalystResponse.parse(raw)
        except Exception as exc:  # the boundary is deliberately fail-closed
            return self._reject(f"ANALYST_UNAVAILABLE:{type(exc).__name__}")
        completed_at = (now or datetime.now(UTC)).astimezone(UTC)
        if completed_at > request.deadline:
            return self._reject("ANALYST_DEADLINE_EXPIRED")
        if response.request_id != request.request_id:
            return self._reject("ANALYST_REQUEST_ECHO_MISMATCH")
        if response.state_hash != request.state_hash:
            return self._reject("ANALYST_STATE_ECHO_MISMATCH")
        return AnalystVerdict(response.decision, True, response.reason_codes)

    @staticmethod
    def _reject(code: str) -> AnalystVerdict:
        return AnalystVerdict(AnalystDecision.NO_TRADE, False, (code,))
