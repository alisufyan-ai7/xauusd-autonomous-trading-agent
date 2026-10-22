from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from xauusd_agent.ops.v2_demo_paper_lifecycle import (
    PaperEvent,
    PaperJournal,
    PaperPosition,
    PaperState,
    paper_step,
)

ID = "SYNTHETIC-TEST-ONE"


def sample_position(direction: str = "BUY") -> PaperPosition:
    if direction == "BUY":
        return PaperPosition(
            ID, direction, Decimal("3000"), Decimal("2990"),
            Decimal("3020"), Decimal("0.01"),
        )
    return PaperPosition(
        ID, direction, Decimal("3000"), Decimal("3010"),
        Decimal("2980"), Decimal("0.01"),
    )


def step(state: PaperJournal, event: PaperEvent, **kwargs) -> PaperJournal:
    return paper_step(state, expected_revision=state.revision, event=event, **kwargs)


def open_synthetic() -> PaperJournal:
    a = step(PaperJournal(), PaperEvent.SIMULATE_ARM)
    b = step(a, PaperEvent.SIMULATE_ENTRY_INTENT, synthetic_id=ID)
    return step(b, PaperEvent.SIMULATE_FILL_ACK, position=sample_position())


def test_known_position_lifecycle_to_flat_then_disarmed() -> None:
    known = open_synthetic()
    assert known.state is PaperState.POSITION_KNOWN
    assert known.revision == 3
    exit_pending = step(
        known, PaperEvent.SIMULATE_EXIT_INTENT, synthetic_id=ID,
    )
    flat = step(exit_pending, PaperEvent.SIMULATE_FLAT_ACK, synthetic_id=ID)
    assert flat.state is PaperState.FLAT_RECONCILED
    assert flat.position is None
    disarmed = step(flat, PaperEvent.SIMULATE_DISARM)
    assert disarmed.state is PaperState.DISARMED
    assert disarmed.execution_permitted is False


def test_stop_cannot_be_widened_or_removed_or_tightened_past_target() -> None:
    state = open_synthetic()
    with pytest.raises(ValueError, match="tighten"):
        step(state, PaperEvent.SIMULATE_TIGHTEN_STOP, new_stop=Decimal("2989"))
    with pytest.raises(ValueError, match="tighten"):
        step(state, PaperEvent.SIMULATE_TIGHTEN_STOP, new_stop=Decimal("3025"))
    with pytest.raises(ValueError, match="required"):
        step(state, PaperEvent.SIMULATE_TIGHTEN_STOP)
    tightened = step(
        state, PaperEvent.SIMULATE_TIGHTEN_STOP, new_stop=Decimal("3000"),
    )
    assert tightened.position is not None
    assert tightened.position.stop == Decimal("3000")
    assert tightened.execution_permitted is False


def test_sell_stop_tightens_down_only() -> None:
    state = PaperJournal(
        state=PaperState.POSITION_KNOWN,
        revision=2,
        position=sample_position("SELL"),
        synthetic_intent_id=ID,
    )
    with pytest.raises(ValueError, match="tighten"):
        step(state, PaperEvent.SIMULATE_TIGHTEN_STOP, new_stop=Decimal("3011"))
    result = step(state, PaperEvent.SIMULATE_TIGHTEN_STOP, new_stop=Decimal("3000"))
    assert result.position is not None
    assert result.position.stop == Decimal("3000")


def test_unknown_outcome_quarantines_and_refuses_automatic_resume() -> None:
    state = step(PaperJournal(), PaperEvent.SIMULATE_ARM)
    pending = step(state, PaperEvent.SIMULATE_ENTRY_INTENT, synthetic_id=ID)
    locked = step(pending, PaperEvent.AMBIGUOUS_BROKER_OUTCOME)
    assert locked.state is PaperState.QUARANTINED
    with pytest.raises(ValueError, match="quarantine"):
        step(locked, PaperEvent.SIMULATE_ARM)
    with pytest.raises(ValueError, match="quarantine"):
        step(locked, PaperEvent.SIMULATE_FLAT_ACK, synthetic_id=ID)


def test_duplicate_intent_and_stale_writer_refuse() -> None:
    armed = step(PaperJournal(), PaperEvent.SIMULATE_ARM)
    first = step(armed, PaperEvent.SIMULATE_ENTRY_INTENT, synthetic_id=ID)
    with pytest.raises(ValueError, match="not admitted"):
        step(first, PaperEvent.SIMULATE_ENTRY_INTENT, synthetic_id=ID)
    with pytest.raises(ValueError, match="stale journal"):
        paper_step(
            armed, expected_revision=0, event=PaperEvent.SIMULATE_ENTRY_INTENT,
            synthetic_id=ID,
        )
    with pytest.raises(ValueError, match="does not match"):
        step(first, PaperEvent.SIMULATE_FILL_ACK, position=replace(
            sample_position(), synthetic_id="SYNTHETIC-OTHER"
        ))


def test_unknown_ticket_never_closed_and_existing_position_not_disarmed() -> None:
    known = open_synthetic()
    with pytest.raises(ValueError, match="exact known"):
        step(known, PaperEvent.SIMULATE_EXIT_INTENT, synthetic_id="SYNTHETIC-OTHER")
    with pytest.raises(ValueError, match="not admitted"):
        step(known, PaperEvent.SIMULATE_DISARM)
    exit_pending = step(known, PaperEvent.SIMULATE_EXIT_INTENT, synthetic_id=ID)
    with pytest.raises(ValueError, match="exact known"):
        step(exit_pending, PaperEvent.SIMULATE_FLAT_ACK, synthetic_id="SYNTHETIC-OTHER")


def test_position_validation_is_no_real_account_and_exact_min_lot() -> None:
    with pytest.raises(ValueError, match="synthetic"):
        replace(sample_position(), synthetic_id="12345")
    with pytest.raises(ValueError, match="0.01"):
        replace(sample_position(), lots=Decimal("0.005"))
    with pytest.raises(ValueError, match="BUY protective"):
        replace(sample_position(), stop=Decimal("3002"))
    with pytest.raises(ValueError, match="cannot permit trading"):
        replace(PaperJournal(), execution_permitted=True)
