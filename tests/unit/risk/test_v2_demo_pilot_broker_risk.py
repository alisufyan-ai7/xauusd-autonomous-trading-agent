from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.guards.event_guard import EventGuardDecision, EventGuardState
from xauusd_agent.market.models import Quote
from xauusd_agent.risk.full_policy_a import FullPolicyAInput
from xauusd_agent.risk.v2_demo_pilot_broker_risk import (
    ADMITTED_DEMO_FINGERPRINT,
    DemoBrokerRiskReceipt,
    PilotRiskStatus,
    evaluate_demo_pilot_risk,
)

NOW = datetime(2026, 10, 22, 13, tzinfo=UTC)
Q = Decimal


def policy() -> FullPolicyAInput:
    return FullPolicyAInput(
        symbol="XAUUSD", side="BUY",
        volume_lots=Q("0.01"), volume_min=Q("0.01"), volume_step=Q("0.01"),
        entry_worst=Q("3000.200"), stop_adverse=Q("2995.200"),
        tick_size=Q("0.001"), tick_value_loss_per_lot_usd=Q("0.1"),
        commission_usd=Q("5"), swap_buffer_usd=Q("2"),
        slippage_buffer_usd=Q("2"), gap_buffer_usd=Q("2"),
        balance_usd=Q("10000"), equity_usd=Q("10000"),
        margin_used_usd=Q("0"), free_margin_usd=Q("10000"),
        incremental_margin_usd=Q("50"),
        m1_current_adverse_cost_usd=Q("14"),
        m1_stressed_adverse_cost_usd=Q("16"),
        concurrent_committed_usd=Q("0"), existing_incremental_loss_usd=Q("0"),
        day_start_equity_usd=Q("10000"), day_external_flows_usd=Q("0"),
        week_start_equity_usd=Q("10000"), week_external_flows_usd=Q("0"),
        inception_external_flows_usd=Q("0"),
        normalized_high_water_usd=Q("10000"), loss_equivalent_streak=Q("0"),
        snapshot_reconciled=True, accounting_reconciled=True,
        exposure_known_and_owned=True, sources_verified=True,
        symbol_verified=True, calibration_admitted=True,
        session_event_guard_pass=True, protective_stop_broker_confirmable=True,
    )


def receipt() -> DemoBrokerRiskReceipt:
    return DemoBrokerRiskReceipt(
        observed_utc=NOW,
        account_fingerprint_sha256=ADMITTED_DEMO_FINGERPRINT,
        server="Exness-MT5Trial15", company="Exness Technologies Ltd",
        trade_mode="DEMO", symbol="XAUUSD",
        quote=Quote(
            symbol="XAUUSD", broker_time=NOW - timedelta(seconds=1),
            received_time=NOW, bid=Q("3000.000"), ask=Q("3000.200"),
            tick_size=Q("0.001"), sequence=1,
        ),
        order_calc_profit_to_stop_usd=Q("-5.00"),
        order_calc_margin_usd=Q("50"),
        positions_count=0, orders_count=0,
        position_and_deal_history_reconciled=True,
        source_epoch_reconciled=True,
        stop_and_symbol_metadata_broker_verified=True,
        current_session_verified_open=True,
        trading_via_external_python_disabled=True,
    )


def event():
    return EventGuardDecision(EventGuardState.HEALTHY, ())


def verdict(r=None, p=None, e=None):
    return evaluate_demo_pilot_risk(
        receipt=receipt() if r is None else r,
        policy=policy() if p is None else p,
        event_guard=event() if e is None else e,
    )


def test_broker_loss_and_full_policy_reconcile_but_never_enable_execution():
    result = verdict()
    assert result.status is PilotRiskStatus.MATH_RECONCILED_REVIEW_ONLY
    assert result.broker_stop_cash_loss_usd == Q("5.00")
    assert result.mathematical_policy_a_pass
    assert result.execution_permitted is False
    with pytest.raises(ValueError, match="never authorizes"):
        replace(result, execution_permitted=True)


def test_identity_server_trade_mode_and_python_protection_fail_closed():
    for changes in (
        {"account_fingerprint_sha256": "a" * 64},
        {"server": "Exness-Live"},
        {"trade_mode": "LIVE"},
        {"trading_via_external_python_disabled": False},
        {"positions_count": None},
        {"positions_count": 1},
        {"orders_count": 1},
        {"position_and_deal_history_reconciled": False},
        {"source_epoch_reconciled": False},
    ):
        assert verdict(r=replace(receipt(), **changes)).status is PilotRiskStatus.DENY


def test_broker_calc_profit_and_margin_unknown_or_conflicting_denied():
    for changes in (
        {"order_calc_profit_to_stop_usd": None},
        {"order_calc_profit_to_stop_usd": Q("0")},
        {"order_calc_profit_to_stop_usd": Q("1")},
        {"order_calc_profit_to_stop_usd": Q("NaN")},
        {"order_calc_profit_to_stop_usd": Q("-10")},
        {"order_calc_margin_usd": None},
        {"order_calc_margin_usd": Q("0")},
        {"order_calc_margin_usd": Q("51")},
    ):
        assert verdict(r=replace(receipt(), **changes)).status is PilotRiskStatus.DENY


def test_quote_age_broker_entry_and_tick_grid_cannot_drift():
    old = receipt()
    assert verdict(r=replace(old, quote=replace(
        old.quote, broker_time=NOW - timedelta(seconds=8),
        received_time=NOW - timedelta(seconds=1),
    ))).status is PilotRiskStatus.DENY
    assert verdict(p=replace(policy(), entry_worst=Q("3000.201"))).status is PilotRiskStatus.DENY
    assert verdict(p=replace(policy(), stop_adverse=Q("2995.2005"))).status is PilotRiskStatus.DENY


def test_full_policy_a_blocks_stops_too_far_and_unknown_verified_sources():
    assert verdict(p=replace(policy(), stop_adverse=Q("2960.200"))).status is PilotRiskStatus.DENY
    assert verdict(p=replace(policy(), accounting_reconciled=False)).status is PilotRiskStatus.DENY
    paused = verdict(p=replace(policy(), loss_equivalent_streak=Q("3")))
    assert paused.status is PilotRiskStatus.DENY


def test_unknown_or_locked_official_event_and_session_denies():
    assert verdict(e=EventGuardDecision(
        EventGuardState.SOURCE_UNHEALTHY, ("TEST_UNHEALTHY",)
    )).status is PilotRiskStatus.DENY
    assert verdict(r=replace(
        receipt(), current_session_verified_open=False
    )).status is PilotRiskStatus.DENY
    assert evaluate_demo_pilot_risk(
        receipt=receipt(), policy=policy(), event_guard=None
    ).status is PilotRiskStatus.DENY


def test_review_receipt_does_not_have_order_api_capability():
    import ast
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[3]
        / "src/xauusd_agent/risk/v2_demo_pilot_broker_risk.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    banned = {"order_send", "positions_close", "login", "initialize"}
    funcs = {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not banned.intersection(funcs)
