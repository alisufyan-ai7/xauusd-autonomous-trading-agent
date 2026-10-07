from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.features import (
    Direction,
    Predicate,
    SetupConfig,
    SetupFamily,
    SetupLifecycle,
    SetupState,
    evaluate_setup,
    select_unambiguous,
    transition,
)

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64


def candidate(family: SetupFamily = SetupFamily.TPB, **overrides):
    config = SetupConfig("P0-SETUPS-001-v1.0", Decimal("0.001"))
    assert config.required_predicates is not None
    arguments = {
        "config": config,
        "account_fingerprint": FINGERPRINT,
        "family": family,
        "direction": Direction.LONG,
        "decision_time": NOW,
        "trigger_bar_time": NOW - timedelta(minutes=15),
        "anchor_times": (NOW - timedelta(hours=8), NOW - timedelta(hours=2)),
        "level_prices": (Decimal("2700.1"), Decimal("2705.2")),
        "predicates": {name: Predicate.TRUE for name in config.required_predicates[family]},
        "entry": Decimal("2700"),
        "stop": Decimal("2699"),
        "tp1": Decimal("2701.5"),
        "final_target": Decimal("2702"),
    }
    arguments.update(overrides)
    return evaluate_setup(**arguments)


def test_all_frozen_families_produce_only_advisory_proposals() -> None:
    expected_expiry = {"TPB": 4, "BRT": 4, "FBR": 3, "RSR": 4, "MOC": 0}
    for family in SetupFamily:
        result = candidate(family)
        assert result.state is SetupState.PROPOSED
        assert result.expiry_bars == expected_expiry[family.value]
        assert len(result.setup_id) == 64


def test_missing_or_unknown_predicate_is_no_trade() -> None:
    config = SetupConfig("P0-SETUPS-001-v1.0", Decimal("0.001"))
    assert config.required_predicates is not None
    predicates = {name: Predicate.TRUE for name in config.required_predicates[SetupFamily.TPB]}
    predicates.pop("confirmation")
    predicates["event_clear"] = Predicate.UNKNOWN
    result = candidate(predicates=predicates)
    assert result.state is SetupState.NO_TRADE
    assert "confirmation:UNKNOWN" in result.reasons
    assert "event_clear:UNKNOWN" in result.reasons


def test_weakening_rr_or_predicate_inventory_is_rejected() -> None:
    with pytest.raises(ValueError, match="weakens"):
        SetupConfig("v", Decimal("0.001"), minimum_rr_tp1=Decimal("1.49"))
    with pytest.raises(ValueError, match="required_predicates"):
        SetupConfig(
            "v",
            Decimal("0.001"),
            required_predicates={family: frozenset() for family in SetupFamily},
        )


def test_setup_identity_is_deterministic_and_ambiguity_fails_closed() -> None:
    first = candidate()
    second = candidate()
    competing = candidate(SetupFamily.BRT)
    assert first.setup_id == second.setup_id
    assert select_unambiguous([first]) == first
    assert select_unambiguous([first, competing]) is None
    assert select_unambiguous([]) is None


def test_lifecycle_is_monotonic_terminal_and_non_reactivating() -> None:
    state = SetupLifecycle("id")
    proposed = transition(state, "PROPOSE", NOW)
    pending = transition(proposed, "RESERVE", NOW + timedelta(seconds=1))
    terminal = transition(pending, "EVENT_LOCK", NOW + timedelta(seconds=2))
    assert terminal.state is SetupState.CANCELLED
    assert terminal.terminal_reason == "EVENT_LOCK"
    with pytest.raises(ValueError, match="terminal"):
        transition(terminal, "PROPOSE", NOW + timedelta(seconds=3))
    with pytest.raises(ValueError, match="increase"):
        transition(pending, "FILLED_OBSERVED", NOW)


def test_reward_risk_failure_is_no_trade_not_exception() -> None:
    result = candidate(tp1=Decimal("2701.49"), final_target=Decimal("2701.99"))
    assert result.state is SetupState.NO_TRADE
    assert result.reasons[-2:] == ("TP1_RR_INSUFFICIENT", "FINAL_RR_INSUFFICIENT")
