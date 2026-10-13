"""Data-only representation of submission uncertainty.

The production candidate cannot submit orders.  These states exist so replay or
future separately governed adapters cannot turn ambiguity into an automatic retry.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class UncertaintyState(StrEnum):
    UNRESOLVED_QUARANTINE = "UNRESOLVED_QUARANTINE"
    RECONCILED_PRESENT = "RECONCILED_PRESENT"
    RECONCILED_ABSENT = "RECONCILED_ABSENT"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


class UncertaintyResolution(StrEnum):
    BROKER_PRESENT = "BROKER_PRESENT"
    BROKER_ABSENT = "BROKER_ABSENT"
    OBSERVATION_INCONCLUSIVE = "OBSERVATION_INCONCLUSIVE"


@dataclass(frozen=True, slots=True)
class SubmissionUncertainty:
    intent_id: str
    first_observed_at_utc: str
    reason: str
    state: UncertaintyState = UncertaintyState.UNRESOLVED_QUARANTINE
    retry_permitted: bool = False

    def __post_init__(self) -> None:
        if not self.intent_id or not self.first_observed_at_utc or not self.reason:
            raise ValueError("complete uncertainty identity is required")
        if self.retry_permitted:
            raise ValueError("automatic retry after submission uncertainty is prohibited")

    def reconcile(self, resolution: UncertaintyResolution) -> SubmissionUncertainty:
        if self.state is not UncertaintyState.UNRESOLVED_QUARANTINE:
            raise ValueError("submission uncertainty is already terminal")
        target = {
            UncertaintyResolution.BROKER_PRESENT: UncertaintyState.RECONCILED_PRESENT,
            UncertaintyResolution.BROKER_ABSENT: UncertaintyState.RECONCILED_ABSENT,
            UncertaintyResolution.OBSERVATION_INCONCLUSIVE: UncertaintyState.HUMAN_ESCALATION,
        }[resolution]
        return replace(self, state=target)
