# ruff: noqa: I001
"""Non-trading, adversarial rules for V2 known-position management."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from xauusd_demo.envelope import DemoSafetyError
from xauusd_demo.known_position_reconciliation import KnownPositionBinding
from xauusd_demo.known_position_management import (
    KnownMarketSnapshot, ManagementAction, ManagementDecision,
    evaluate_known_position_management,
)

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
FP = "a" * 64


def bound(side="BUY"):
    return KnownPositionBinding(
        position_id=712, entry_order=312, entry_deal=412,
        account_fingerprint=FP, side=side, volume=D("0.01"),
        protective_sl=D("99") if side == "BUY" else D("101"),
        protective_tp=D("103") if side == "BUY" else D("97"),
        tick_size=D("0.01"),
    )


def market(side="BUY"):
    b = bound(side)
    return KnownMarketSnapshot(
        account_fingerprint=FP, position_id=712, side=side, lots=D("0.01"),
        entry_price=D("100"), current_stop=b.protective_sl,
        current_target=b.protective_tp, tick_size=b.tick_size,
        bid=D("100.50"), ask=D("100.60"), quote_utc=NOW,
        observed_utc=NOW, reconciliation="OPEN",
    )


@pytest.mark.parametrize(("side", "tight_stop"), [
    ("BUY", D("100.10")),
    ("SELL", D("100.80")),
])
def test_confirmed_structural_stop_tightening_is_non_executable(side, tight_stop):
    market_row = replace(
        market(side), trailing_stop=tight_stop,
        favourable_structure_confirmed=True,
    )
    decision = evaluate_known_position_management(bound(side), market_row, now=NOW)
    assert decision.action == ManagementAction.PROPOSE_TIGHTEN_STOP
    assert decision.suggested_stop == tight_stop
    assert decision.execution_permitted is False


def test_early_exit_precedes_stop_and_tp_and_has_no_broker_authority():
    market_row = replace(
        market(), structure_invalidation=True,
        trailing_stop=D("100.10"), reduced_take_profit=D("102"),
        favourable_structure_confirmed=True,
    )
    decision = evaluate_known_position_management(bound(), market_row, now=NOW)
    assert decision.action == ManagementAction.PROPOSE_EARLY_EXIT
    assert decision.execution_permitted is False
    assert decision.suggested_stop is None


@pytest.mark.parametrize(("side", "new_target"), [
    ("BUY", D("102")),
    ("SELL", D("99")),
])
def test_only_proven_favourable_structure_can_reduce_tp(side, new_target):
    row = replace(market(side), reduced_take_profit=new_target,
                  favourable_structure_confirmed=True)
    d = evaluate_known_position_management(bound(side), row, now=NOW)
    assert d.action == ManagementAction.PROPOSE_TAKE_PROFIT_REFINEMENT
    assert d.suggested_target == new_target
    assert not d.execution_permitted


@pytest.mark.parametrize(("side", "candidate_stop"), [
    ("BUY", D("98")),    # widen known BUY risk
    ("BUY", D("100.50")),  # at executable bid
    ("SELL", D("102")),    # widen known SELL risk
    ("SELL", D("100.60")),  # at executable ask
])
def test_never_suggest_widening_or_instant_trigger(side, candidate_stop):
    row = replace(market(side), trailing_stop=candidate_stop,
                  favourable_structure_confirmed=True)
    assert evaluate_known_position_management(
        bound(side), row, now=NOW
    ).action == ManagementAction.NO_CHANGE


@pytest.mark.parametrize(("side", "new_target"), [
    ("BUY", D("104")), ("SELL", D("96")),
    ("BUY", D("100.55")), ("SELL", D("100.52")),
])
def test_never_suggest_target_widening_or_executable_crossing(side, new_target):
    row = replace(market(side), reduced_take_profit=new_target,
                  favourable_structure_confirmed=True)
    assert evaluate_known_position_management(
        bound(side), row, now=NOW
    ).action == ManagementAction.NO_CHANGE


def test_unconfirmed_structure_cannot_trigger_stop_or_tp_change():
    row = replace(market(), trailing_stop=D("100.10"),
                  reduced_take_profit=D("102"))
    assert evaluate_known_position_management(
        bound(), row, now=NOW
    ).action == ManagementAction.NO_CHANGE


@pytest.mark.parametrize("field,value", [
    ("account_fingerprint", "b" * 64),
    ("position_id", 42),
    ("side", "SELL"),
    ("lots", D("0.02")),
    ("current_stop", D("98")),
    ("current_target", D("104")),
    ("tick_size", D("0.10")),
    ("reconciliation", "UNKNOWN"),
    ("reconciliation", "CLOSED"),
])
def test_unknown_foreign_or_modified_position_fails_closed(field, value):
    with pytest.raises(DemoSafetyError):
        evaluate_known_position_management(
            bound(), replace(market(), **{field: value}), now=NOW
        )


@pytest.mark.parametrize("field,value", [
    ("bid", D("0")),
    ("bid", D("100.501")),
    ("ask", D("99")),
    ("entry_price", D("nan")),
    ("current_stop", D("0")),
    ("quote_utc", NOW + timedelta(seconds=3)),
    ("quote_utc", NOW - timedelta(seconds=3)),
    ("observed_utc", NOW + timedelta(seconds=1)),
    ("quote_utc", NOW.replace(tzinfo=None)),
    ("observed_utc", NOW.replace(tzinfo=None)),
    ("structure_invalidation", 1),
    ("favourable_structure_confirmed", "yes"),
])
def test_bad_price_freshness_or_untrusted_source_fails_closed(field, value):
    with pytest.raises(DemoSafetyError):
        evaluate_known_position_management(
            bound(), replace(market(), **{field: value}), now=NOW
        )


def test_invalid_mutation_candidates_fail_closed_even_without_execution():
    for change in (
        {"trailing_stop": D("100.101")},
        {"reduced_take_profit": D("102.001")},
        {"trailing_stop": D("-1")},
    ):
        with pytest.raises(DemoSafetyError):
            evaluate_known_position_management(
                bound(), replace(market(), **change), now=NOW
            )


def test_pure_output_cannot_be_turned_into_a_permission():
    with pytest.raises(DemoSafetyError):
        ManagementDecision(ManagementAction.PROPOSE_EARLY_EXIT, "fake",
                           execution_permitted=True)
