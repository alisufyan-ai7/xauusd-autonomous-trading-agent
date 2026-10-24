"""Regression contract for owner goal and release gates in GitHub.

A fake-MT5 success is never the real Exness DEMO-server order acceptance;
24-48h of DEMO does not grant any LIVE execution authority. This test
validates durable decision metadata only, not operational broker proof.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "phase0/roadmap/REAL_BROKER_DEMO_LIVE_MILESTONES_2026-10-23.json"


def _milestones() -> dict[str, object]:
    with REGISTRY.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def test_real_exness_demo_broker_orders_are_required_not_fake_orders() -> None:
    record = _milestones()
    definition = record["definition"]
    assert isinstance(definition, dict)
    assert definition["environment"] == "DEMO"
    assert definition["broker"] == "Exness Pro"
    assert definition["capital_type"] == "VIRTUAL"
    assert definition["real_broker_order_send_required"] is True
    assert definition["real_demo_broker_order_records_required"] is True
    assert definition["simulation_acceptable_for_final_demo_acceptance"] is False
    assert definition["autonomous_buy_sell_stop_tp"] is True


def test_live_never_promotes_after_one_two_day_review() -> None:
    record = _milestones()
    stages = record["stages"]
    assert isinstance(stages, list)
    assert [stage["id"] for stage in stages] == ["M1", "M2", "M3", "M4", "M5"]
    early_review, live = stages[3], stages[4]
    assert early_review["early_review_hours_min"] == 24
    assert early_review["early_review_hours_target"] == 48
    assert early_review["profitability_validated_by_48h"] is False
    assert early_review["automatic_live_promotion"] is False
    assert live["status"] == "FUTURE_DESIRED_NOT_AUTHORIZED"
    assert live["automatically_authorized_after_demo"] is False
    assert "SEPARATE_EXACT_OWNER_LIVE_APPROVAL" in live["acceptance"]
    assert "MIN_0_01_LOT_FITS_0_25_PERCENT_OR_NO_TRADE" in live["acceptance"]


def test_demo_and_live_release_gates_both_remain_closed() -> None:
    record = _milestones()
    gates = record["gates"]
    assert isinstance(gates, dict)
    assert gates["effective_demo_order_execution"] == "NO_GO"
    assert gates["effective_live_order_execution"] == "NO_GO"
    assert gates["demo_server_order_evidence"] is False
    assert gates["vps_installed_broker_trader"] is False
    assert gates["external_python_trading_enabled"] is False
    assert gates["live_credentials_in_demo_package"] is False
    assert gates["accepted_main_governance_rule7_conflict"].startswith("UNRESOLVED")
    assert gates["old_gate_failures_reclassified"] is False
    assert gates["allow_merged_without_owner_approval"] is False


def test_real_order_s2_still_denied_prior_to_any_broker_call() -> None:
    source = (ROOT / "demo_adapter/src/xauusd_demo/mt5_demo.py").read_text(
        encoding="utf-8"
    )
    denial = source.index("FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED")
    broker_check = source.index("self._mt5.order_check(mt5_request)")
    broker_send = source.index("self._mt5.order_send(mt5_request)")
    assert denial < broker_check < broker_send
    # Static ordering is necessary but never sufficient: release tests also
    # exercise the S2 path with a counted synthetic broker.
