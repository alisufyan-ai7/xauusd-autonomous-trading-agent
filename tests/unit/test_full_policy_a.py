"""Independent frozen Policy A vectors; synthetic Decimal input only, no MT5."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from xauusd_agent.risk.full_policy_a import (
    FullPolicyAInput,
    FullRiskDisposition,
    evaluate_full_policy_a,
)


def d(value: str) -> Decimal:
    return Decimal(value)


def good(**changes: object) -> FullPolicyAInput:
    item = FullPolicyAInput(
        symbol="XAUUSD", side="BUY", volume_lots=d("0.01"),
        volume_min=d("0.01"), volume_step=d("0.01"),
        entry_worst=d("2000.20"), stop_adverse=d("1978.20"),
        tick_size=d("0.01"), tick_value_loss_per_lot_usd=d("1"),
        commission_usd=d("1"), swap_buffer_usd=d("0.50"),
        slippage_buffer_usd=d("1"), gap_buffer_usd=d("0.50"),
        balance_usd=d("10000"), equity_usd=d("10000"),
        margin_used_usd=d("0"), free_margin_usd=d("10000"),
        incremental_margin_usd=d("5"),
        m1_current_adverse_cost_usd=d("3"),
        m1_stressed_adverse_cost_usd=d("6"),
        concurrent_committed_usd=d("0"), existing_incremental_loss_usd=d("0"),
        day_start_equity_usd=d("10000"), day_external_flows_usd=d("0"),
        week_start_equity_usd=d("10000"), week_external_flows_usd=d("0"),
        inception_external_flows_usd=d("0"),
        normalized_high_water_usd=d("10000"),
        loss_equivalent_streak=d("0"),
        snapshot_reconciled=True, accounting_reconciled=True,
        exposure_known_and_owned=True, sources_verified=True,
        symbol_verified=True, calibration_admitted=True,
        session_event_guard_pass=True, protective_stop_broker_confirmable=True,
    )
    return replace(item, **changes)


def check(item: FullPolicyAInput, reason: str) -> None:
    result = evaluate_full_policy_a(item)
    assert result.disposition is FullRiskDisposition.REJECT
    assert reason in result.reasons


def test_normative_loss_formula_rg007() -> None:
    result = evaluate_full_policy_a(good())
    assert result.mathematics_pass
    assert result.l_price == d("22.00")
    assert result.l_plan == d("25.00")
    assert result.per_trade_cap == d("25.00")
    assert result.concurrent_prospective == d("25.00")


def test_rg008_one_cent_over_denied() -> None:
    check(good(gap_buffer_usd=d("0.51")), "POLICY_A_PER_TRADE_STOP_LOSS_USD")


@pytest.mark.parametrize("balance,equity,expected", [
    ("10000", "10000", "25.00"), ("9000", "9400", "22.50"),
    ("9500", "8000", "20.00"), ("15000", "15500", "25.00"),
    ("10000", "9999.999", "24.99"),
])
def test_rg001_to_005_and_042_cap(balance: str, equity: str, expected: str) -> None:
    item = good(balance_usd=d(balance), equity_usd=d(equity),
                free_margin_usd=d(equity), day_start_equity_usd=d(equity),
                week_start_equity_usd=d(equity),
                normalized_high_water_usd=d(equity))
    result = evaluate_full_policy_a(item)
    assert result.per_trade_cap == d(expected)
    if expected != "25.00":
        assert "POLICY_A_PER_TRADE_STOP_LOSS_USD" in result.reasons


def test_far_stop_denied_even_at_001_lot() -> None:
    check(good(stop_adverse=d("1000")), "POLICY_A_PER_TRADE_STOP_LOSS_USD")


def test_sell_price_ticks_are_adverse_and_rounded_up() -> None:
    result = evaluate_full_policy_a(good(
        side="SELL", entry_worst=d("2000"), stop_adverse=d("2022.001"),
        tick_size=d("0.01"), commission_usd=d("0"),
        swap_buffer_usd=d("0"), slippage_buffer_usd=d("0"),
        gap_buffer_usd=d("0"),
    ))
    assert result.l_price == d("22.01")
    assert result.l_plan == d("22.01")


def test_committed_boundary_and_one_cent_violation() -> None:
    result = evaluate_full_policy_a(good(concurrent_committed_usd=d("25")))
    assert result.mathematics_pass
    check(good(concurrent_committed_usd=d("25.01")), "POLICY_A_CONCURRENT_USD")


def test_daily_flow_adjustment_counts_unrealized_only_once() -> None:
    item = good(equity_usd=d("9940"), balance_usd=d("9980"),
                free_margin_usd=d("9940"), day_start_equity_usd=d("10000"),
                week_start_equity_usd=d("9940"),
                normalized_high_water_usd=d("9940"),
                existing_incremental_loss_usd=d("10"))
    result = evaluate_full_policy_a(item)
    assert result.day_loss == d("60")
    assert result.day_prospective == d("95")
    assert "POLICY_A_DAILY_LOSS_USD" in result.reasons
    deposited = replace(item, equity_usd=d("10940"), balance_usd=d("10980"),
                       free_margin_usd=d("10940"), day_external_flows_usd=d("1000"),
                       week_start_equity_usd=d("10940"),
                       normalized_high_water_usd=d("9940"),
                       inception_external_flows_usd=d("1000"))
    assert evaluate_full_policy_a(deposited).day_loss == d("60")


def test_daily_at_75_pass_and_75_01_fail() -> None:
    item = good(entry_worst=d("2000.20"), stop_adverse=d("1985.20"),
                equity_usd=d("9950"), balance_usd=d("9950"),
                free_margin_usd=d("9950"),
                normalized_high_water_usd=d("9950"),
                day_start_equity_usd=d("10000"), week_start_equity_usd=d("9950"),
                commission_usd=d("1"), swap_buffer_usd=d("0.50"),
                slippage_buffer_usd=d("1"), gap_buffer_usd=d("0.50"))
    # L_price=15 + 3 buffers =18, so need existing=7 to reach 75.
    pass_item = replace(item, existing_incremental_loss_usd=d("7"))
    assert evaluate_full_policy_a(pass_item).day_prospective == d("75")
    assert evaluate_full_policy_a(pass_item).mathematics_pass
    check(replace(pass_item, existing_incremental_loss_usd=d("7.01")),
          "POLICY_A_DAILY_LOSS_USD")


def test_weekly_and_drawdown_boundaries() -> None:
    base = good(equity_usd=d("9875"), balance_usd=d("9875"),
                free_margin_usd=d("9875"),
                day_start_equity_usd=d("9875"),
                week_start_equity_usd=d("10000"),
                normalized_high_water_usd=d("9875"))
    assert evaluate_full_policy_a(base).week_prospective == d("150")
    assert evaluate_full_policy_a(base).mathematics_pass
    check(replace(base, week_start_equity_usd=d("10000.01")),
          "POLICY_A_WEEKLY_LOSS_USD")
    dd_base = good(equity_usd=d("9725"), balance_usd=d("9725"),
                   free_margin_usd=d("9725"),
                   day_start_equity_usd=d("9725"),
                   week_start_equity_usd=d("9725"),
                   normalized_high_water_usd=d("10200"))
    assert evaluate_full_policy_a(dd_base).drawdown_prospective == d("500")
    assert evaluate_full_policy_a(dd_base).mathematics_pass
    check(replace(dd_base, normalized_high_water_usd=d("10200.01")),
          "POLICY_A_DRAWDOWN_USD")


def test_loss_equivalent_streak_pause_at_3() -> None:
    assert evaluate_full_policy_a(good(loss_equivalent_streak=d("2.99"))).mathematics_pass
    check(good(loss_equivalent_streak=d("3")), "POLICY_A_FULL_RISK_EQUIVALENT_PAUSE")


def test_m1_current_and_stressed_independent() -> None:
    check(good(incremental_margin_usd=d("500")), "POLICY_A_M1_STRESSED")
    check(good(incremental_margin_usd=d("1100")), "POLICY_A_M1_CURRENT")


@pytest.mark.parametrize("field", [
    "snapshot_reconciled", "accounting_reconciled", "exposure_known_and_owned",
    "sources_verified", "symbol_verified", "calibration_admitted",
    "session_event_guard_pass", "protective_stop_broker_confirmable",
])
def test_any_unverified_dependency_quarantines(field: str) -> None:
    item = good(**{field: False})
    result = evaluate_full_policy_a(item)
    assert result.disposition is FullRiskDisposition.QUARANTINE


@pytest.mark.parametrize("field", [
    "commission_usd", "swap_buffer_usd", "slippage_buffer_usd", "gap_buffer_usd",
    "tick_size", "tick_value_loss_per_lot_usd",
    "day_start_equity_usd", "day_external_flows_usd",
    "week_start_equity_usd", "inception_external_flows_usd",
    "normalized_high_water_usd", "incremental_margin_usd",
])
def test_missing_required_field_quarantines(field: str) -> None:
    item = good(**{field: None})
    result = evaluate_full_policy_a(item)
    assert result.disposition is FullRiskDisposition.QUARANTINE


def test_nonfinite_float_wrong_symbol_and_volume_grid_fail_closed() -> None:
    assert (evaluate_full_policy_a(good(gap_buffer_usd=d("NaN"))).disposition
            is FullRiskDisposition.QUARANTINE)
    assert (evaluate_full_policy_a(good(gap_buffer_usd=0.0)).disposition
            is FullRiskDisposition.QUARANTINE)
    assert (evaluate_full_policy_a(good(symbol="EURUSD")).disposition
            is FullRiskDisposition.QUARANTINE)
    check(good(volume_lots=d("0.02")), "V1_VOLUME_CAP")
    check(good(volume_lots=d("0.005")), "BELOW_BROKER_VOLUME_MIN")


def test_stress_cost_below_current_denied_and_free_margin_gate() -> None:
    check(good(m1_stressed_adverse_cost_usd=d("2")), "STRESS_BELOW_CURRENT_COST")
    check(good(margin_used_usd=d("1000"),
               free_margin_usd=d("9000")), "POLICY_A_M1_CURRENT")


def test_no_emergency_close_or_broker_import_in_pure_engine() -> None:
    import inspect

    from xauusd_agent.risk import full_policy_a

    source = inspect.getsource(full_policy_a)
    assert "MetaTrader5" not in source
    assert "order_send(" not in source
    assert "positions_get(" not in source
    assert "order_check(" not in source
