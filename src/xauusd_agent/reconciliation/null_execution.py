"""Immutable proof record for a decision that could not execute."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from xauusd_agent.risk.policy_a import RiskDisposition


class NullExecutionResult(StrEnum):
    NOT_EXECUTED = "NOT_EXECUTED"


@dataclass(frozen=True, slots=True)
class NullExecutionRecord:
    decision_id: str
    decided_at_utc: str
    setup_id: str | None
    risk_disposition: RiskDisposition
    risk_reason_codes: tuple[str, ...]
    result: NullExecutionResult = NullExecutionResult.NOT_EXECUTED
    execution_capability: str = "ABSENT"
    broker_action_count: int = 0

    def __post_init__(self) -> None:
        if not self.decision_id or not self.decided_at_utc:
            raise ValueError("decision identity and UTC time are required")
        if self.result is not NullExecutionResult.NOT_EXECUTED:
            raise ValueError("null execution records must be NOT_EXECUTED")
        if self.execution_capability != "ABSENT":
            raise ValueError("production-candidate execution capability must be absent")
        if self.broker_action_count != 0:
            raise ValueError("production-candidate broker action count must be zero")
