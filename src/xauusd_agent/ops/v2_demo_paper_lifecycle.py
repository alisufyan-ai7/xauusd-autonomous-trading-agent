"""Paper-only autonomous DEMO lifecycle state machine.

This module owns no broker handle and has no broker order APIs. All positions
and acknowledgements are synthetic inputs; it is NOT a deployable executor.
An actual DEMO broker writer requires independently reviewed API, Policy A,
account binding, MT5 order-check/send and broker reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum


class PaperState(StrEnum):
    DISARMED = "DISARMED"
    READY = "READY"
    ENTRY_PENDING = "ENTRY_PENDING"
    POSITION_KNOWN = "POSITION_KNOWN"
    EXIT_PENDING = "EXIT_PENDING"
    FLAT_RECONCILED = "FLAT_RECONCILED"
    QUARANTINED = "QUARANTINED"


class PaperEvent(StrEnum):
    SIMULATE_ARM = "SIMULATE_ARM"
    SIMULATE_ENTRY_INTENT = "SIMULATE_ENTRY_INTENT"
    SIMULATE_FILL_ACK = "SIMULATE_FILL_ACK"
    SIMULATE_TIGHTEN_STOP = "SIMULATE_TIGHTEN_STOP"
    SIMULATE_EXIT_INTENT = "SIMULATE_EXIT_INTENT"
    SIMULATE_FLAT_ACK = "SIMULATE_FLAT_ACK"
    AMBIGUOUS_BROKER_OUTCOME = "AMBIGUOUS_BROKER_OUTCOME"
    SIMULATE_DISARM = "SIMULATE_DISARM"


@dataclass(frozen=True, slots=True)
class PaperPosition:
    synthetic_id: str
    direction: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    lots: Decimal

    def __post_init__(self) -> None:
        if (
            not self.synthetic_id.startswith("SYNTHETIC-")
            or self.direction not in {"BUY", "SELL"}
            or self.lots != Decimal("0.01")
            or any(not x.is_finite() or x <= 0 for x in (
                self.entry, self.stop, self.target,
            ))
        ):
            raise ValueError("synthetic 0.01-lot position required")
        if self.direction == "BUY" and not (
            self.stop < self.entry < self.target
        ):
            raise ValueError("BUY protective stop/target must surround entry")
        if self.direction == "SELL" and not (
            self.target < self.entry < self.stop
        ):
            raise ValueError("SELL protective stop/target must surround entry")


@dataclass(frozen=True, slots=True)
class PaperJournal:
    state: PaperState = PaperState.DISARMED
    revision: int = 0
    position: PaperPosition | None = None
    synthetic_intent_id: str | None = None
    reason: str = "PAPER_ONLY"
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("paper journal cannot permit trading")
        if self.revision < 0:
            raise ValueError("revision must be nonnegative")


def paper_step(
    ledger: PaperJournal,
    *,
    expected_revision: int,
    event: PaperEvent,
    synthetic_id: str | None = None,
    position: PaperPosition | None = None,
    new_stop: Decimal | None = None,
) -> PaperJournal:
    """Deterministic dry-run transition: all mutations are in-memory only.

    Fail and quarantine on ambiguous simulated broker outcome; no automated
    recovery from unknown exposure or attempt to close unknown positions.
    """
    if expected_revision != ledger.revision:
        raise ValueError("stale journal revision; possible duplicate writer")
    if ledger.state is PaperState.QUARANTINED:
        raise ValueError("quarantine cannot self-rearm")
    if event is PaperEvent.AMBIGUOUS_BROKER_OUTCOME:
        return replace(
            ledger, state=PaperState.QUARANTINED, revision=ledger.revision + 1,
            reason="SIMULATED_AMBIGUOUS_OUTCOME_HUMAN_RECONCILE",
        )
    if event is PaperEvent.SIMULATE_ARM and ledger.state is PaperState.DISARMED:
        return replace(
            ledger, state=PaperState.READY, revision=ledger.revision + 1,
            reason="SIMULATED_ARM_NO_REAL_AUTHORIZATION",
        )
    if (
        event is PaperEvent.SIMULATE_ENTRY_INTENT
        and ledger.state in {PaperState.READY, PaperState.FLAT_RECONCILED}
    ):
        if not synthetic_id or not synthetic_id.startswith("SYNTHETIC-"):
            raise ValueError("synthetic intent identity is required")
        if ledger.position is not None:
            raise ValueError("cannot add to existing paper exposure")
        if ledger.synthetic_intent_id == synthetic_id:
            raise ValueError("duplicate paper intent")
        return replace(
            ledger, state=PaperState.ENTRY_PENDING,
            revision=ledger.revision + 1,
            synthetic_intent_id=synthetic_id,
            reason="SYNTHETIC_ENTRY_PENDING",
        )
    if event is PaperEvent.SIMULATE_FILL_ACK and ledger.state is PaperState.ENTRY_PENDING:
        if position is None or position.synthetic_id != ledger.synthetic_intent_id:
            raise ValueError("synthetic position does not match durable intent")
        return replace(
            ledger, state=PaperState.POSITION_KNOWN,
            position=position, revision=ledger.revision + 1,
            reason="SYNTHETIC_KNOWN_POSITION",
        )
    if (
        event is PaperEvent.SIMULATE_TIGHTEN_STOP
        and ledger.state is PaperState.POSITION_KNOWN
    ):
        existing = ledger.position
        if existing is None or new_stop is None or not new_stop.is_finite():
            raise ValueError("known position and valid new stop required")
        if existing.direction == "BUY" and not (
            existing.stop < new_stop < existing.target
        ):
            raise ValueError("BUY stop must strictly tighten below target")
        if existing.direction == "SELL" and not (
            existing.target < new_stop < existing.stop
        ):
            raise ValueError("SELL stop must strictly tighten above target")
        return replace(
            ledger, position=replace(existing, stop=new_stop),
            revision=ledger.revision + 1,
            reason="SYNTHETIC_STOP_TIGHTENED",
        )
    if event is PaperEvent.SIMULATE_EXIT_INTENT and ledger.state is PaperState.POSITION_KNOWN:
        if ledger.position is None or synthetic_id != ledger.position.synthetic_id:
            raise ValueError("only the exact known synthetic position may exit")
        return replace(
            ledger, state=PaperState.EXIT_PENDING,
            revision=ledger.revision + 1,
            reason="SYNTHETIC_EXIT_PENDING",
        )
    if event is PaperEvent.SIMULATE_FLAT_ACK and ledger.state is PaperState.EXIT_PENDING:
        if ledger.position is None or synthetic_id != ledger.position.synthetic_id:
            raise ValueError("must reconcile exact known synthetic exit")
        return replace(
            ledger, state=PaperState.FLAT_RECONCILED,
            position=None, revision=ledger.revision + 1,
            reason="SYNTHETIC_FLAT_CONFIRMED",
        )
    if (
        event is PaperEvent.SIMULATE_DISARM
        and ledger.state in {PaperState.READY, PaperState.FLAT_RECONCILED}
        and ledger.position is None
    ):
        return replace(
            ledger, state=PaperState.DISARMED,
            revision=ledger.revision + 1,
            reason="PAPER_DISARMED",
        )
    raise ValueError(f"paper transition not admitted: {ledger.state} -> {event}")
