"""Independent offline regression of FROZEN Policy A and Event Guard; no MT5."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from xauusd_agent.guards.event_guard import (
    EventGuardState,
    EventObservation,
    ProtectedEvent,
    evaluate_event_guard,
)
from xauusd_agent.risk.full_policy_a import (
    DRAWDOWN_CAP,
    MARGIN_LEVEL_MIN,
    VOLUME_CAP,
    FullPolicyAInput,
    FullRiskDisposition,
    evaluate_full_policy_a,
)


D = Decimal


def synthetic_approved_math_only() -> FullPolicyAInput:
    """This is fabricated data; no broker origin, admission or execution permit."""
    return FullPolicyAInput(
        symbol="XAUUSD", side="BUY", volume_lots=D("0.01"),
        volume_min=D("0.01"), volume_step=D("0.01"),
        entry_worst=D("4000"), stop_adverse=D("3998"),
        tick_size=D("0.01"), tick_value_loss_per_lot_usd=D("1"),
        commission_usd=D("0.40"), swap_buffer_usd=D("0.20"),
        slippage_buffer_usd=D("0.30"), gap_buffer_usd=D("0.40"),
        balance_usd=D("10000"), equity_usd=D("10000"),
        margin_used_usd=D("0"), free_margin_usd=D("10000"),
        incremental_margin_usd=D("10"),
        m1_current_adverse_cost_usd=D("5"),
        m1_stressed_adverse_cost_usd=D("10"),
        concurrent_committed_usd=D("0"),
        existing_incremental_loss_usd=D("0"),
        day_start_equity_usd=D("10000"),
        day_external_flows_usd=D("0"),
        week_start_equity_usd=D("10000"),
        week_external_flows_usd=D("0"),
        inception_external_flows_usd=D("0"),
        normalized_high_water_usd=D("10000"),
        loss_equivalent_streak=D("0"),
        snapshot_reconciled=True, accounting_reconciled=True,
        exposure_known_and_owned=True, sources_verified=True,
        symbol_verified=True, calibration_admitted=True,
        session_event_guard_pass=True, protective_stop_broker_confirmable=True,
    )


def test_planned_usd_loss_prospective_all_components_and_cap() -> None:
    r = evaluate_full_policy_a(synthetic_approved_math_only())
    assert r.disposition == FullRiskDisposition.ALLOW_MATH_ONLY
    assert r.l_price == D("2.00")
    assert r.l_plan == D("3.30")
    assert r.per_trade_cap == D("25.00")
    assert not hasattr(r, "broker_order_authorized")


@pytest.mark.parametrize(("update", "reason"), [
    ({"stop_adverse": D("3950")}, "POLICY_A_PER_TRADE_STOP_LOSS_USD"),
    ({"concurrent_committed_usd": D("49")}, "POLICY_A_CONCURRENT_USD"),
    ({"equity_usd": D("9927")}, "POLICY_A_DAILY_LOSS_USD"),
    ({"equity_usd": D("9853"), "day_start_equity_usd": D("9853")},
     "POLICY_A_WEEKLY_LOSS_USD"),
    ({"equity_usd": D("9950"), "normalized_high_water_usd": D("10500"),
      "day_start_equity_usd": D("9950"), "week_start_equity_usd": D("9950")},
     "POLICY_A_DRAWDOWN_USD"),
    ({"loss_equivalent_streak": D("3")}, "POLICY_A_FULL_RISK_EQUIVALENT_PAUSE"),
    ({"volume_lots": D("0.02")}, "V1_VOLUME_CAP"),
    ({"margin_used_usd": D("1200")}, "POLICY_A_M1_CURRENT"),
    ({"incremental_margin_usd": D("600")}, "POLICY_A_M1_STRESSED"),
    ({"free_margin_usd": D("8800")}, "POLICY_A_M1_CURRENT"),
])
def test_independent_risk_categories_reject(
    update: dict[str, object], reason: str,
) -> None:
    r = evaluate_full_policy_a(replace(synthetic_approved_math_only(), **update))
    assert r.disposition != FullRiskDisposition.ALLOW_MATH_ONLY
    assert any(reason in x for x in r.reasons), (reason, r)


@pytest.mark.parametrize("missing", [
    "commission_usd", "swap_buffer_usd", "slippage_buffer_usd",
    "gap_buffer_usd", "tick_value_loss_per_lot_usd",
    "m1_current_adverse_cost_usd", "m1_stressed_adverse_cost_usd",
])
def test_missing_cash_or_cost_component_is_quarantine(missing: str) -> None:
    r = evaluate_full_policy_a(replace(synthetic_approved_math_only(), **{missing: None}))
    assert r.disposition == FullRiskDisposition.QUARANTINE


@pytest.mark.parametrize("field", [
    "snapshot_reconciled", "accounting_reconciled",
    "exposure_known_and_owned", "sources_verified", "symbol_verified",
    "calibration_admitted", "session_event_guard_pass",
    "protective_stop_broker_confirmable",
])
def test_unknown_or_false_provenance_controls_quarantine(field: str) -> None:
    r = evaluate_full_policy_a(replace(synthetic_approved_math_only(), **{field: False}))
    assert r.disposition == FullRiskDisposition.QUARANTINE


def test_true_stop_sign_cost_stress_and_frozen_risk_limits() -> None:
    base = synthetic_approved_math_only()
    for mutation in (
        {"side": "BUY", "stop_adverse": D("4001")},
        {"side": "SELL", "stop_adverse": D("3998")},
        {"m1_stressed_adverse_cost_usd": D("1")},
        {"commission_usd": D("-1")},
    ):
        r = evaluate_full_policy_a(replace(base, **mutation))
        assert r.disposition == FullRiskDisposition.REJECT
    assert VOLUME_CAP == D("0.01")
    assert MARGIN_LEVEL_MIN == D("1000")
    assert DRAWDOWN_CAP == D("500")


def test_frozen_event_guard_tier1_tier2_blackout_and_normalization() -> None:
    at = datetime(2026, 11, 6, 13, 30, tzinfo=UTC)  # 08:30 EST
    def decision(offset: int, normalized: bool, tier: str = "TIER_1") -> EventGuardState:
        return evaluate_event_guard(EventObservation(
            observed_utc=at + timedelta(minutes=offset),
            events=(ProtectedEvent("synthetic", at, tier),),
            source_healthy=True, sources_agree=True, coverage_complete=True,
            shock_locked=False, normalized=normalized,
        )).state

    assert decision(-30, True) == EventGuardState.PRE_LOCK
    assert decision(0, True) == EventGuardState.EVENT_ACTIVE
    assert decision(29, True) == EventGuardState.POST_LOCK
    assert decision(30, False) == EventGuardState.NORMALIZATION_PENDING
    assert decision(30, True) == EventGuardState.HEALTHY
    assert decision(-16, True, "TIER_2") == EventGuardState.HEALTHY
    assert decision(-15, True, "TIER_2") == EventGuardState.PRE_LOCK


def test_unknown_unhealthy_tentative_and_shock_never_healthy() -> None:
    t = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
    kwargs = dict(
        observed_utc=t,
        events=(ProtectedEvent("synthetic", t + timedelta(days=1), "TIER_1"),),
        source_healthy=True, sources_agree=True,
        coverage_complete=True, shock_locked=False, normalized=True,
    )
    for change in (
        {"events": None}, {"source_healthy": None}, {"source_healthy": False},
        {"sources_agree": False}, {"coverage_complete": False},
        {"shock_locked": True}, {"normalized": None},
        {"events": (ProtectedEvent("tentative", t, "TIER_1",
                                  status="TENTATIVE"),)},
    ):
        obs = EventObservation(**{**kwargs, **change})
        assert not evaluate_event_guard(obs).entry_allowed
