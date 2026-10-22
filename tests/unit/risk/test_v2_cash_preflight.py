"""Pure current Policy A tests; no broker connection or execution."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from xauusd_agent.risk.v2_cash_preflight import (
    BrokerCashRiskInputs,
    CashRiskState,
    preview_policy_a_cash_risk,
)


def inputs() -> BrokerCashRiskInputs:
    return BrokerCashRiskInputs(
        balance_usd=Decimal("10000"),
        equity_usd=Decimal("10000"),
        free_margin_usd=Decimal("10000"),
        used_margin_usd=Decimal("0"),
        broker_incremental_margin_usd=Decimal("10"),
        stop_loss_price_usd=Decimal("8"),
        commission_usd=Decimal("3"),
        swap_usd=Decimal("0"),
        slippage_usd=Decimal("0"),
        gap_reserve_usd=Decimal("2"),
        existing_committed_risk_usd=Decimal("0"),
        adjusted_daily_loss_usd=Decimal("0"),
        adjusted_weekly_loss_usd=Decimal("0"),
        drawdown_from_peak_usd=Decimal("0"),
        full_risk_loss_streak=Decimal("0"),
        volume_lots=Decimal("0.01"),
        broker_identity_ok=True,
        broker_price_cost_source_verified=True,
        period_cashflows_reconciled=True,
        flat_exposure_verified=True,
        protective_stop_verified=True,
    )


def test_cash_preview_pass_is_never_execution_permission() -> None:
    result = preview_policy_a_cash_risk(inputs())
    assert result.status is CashRiskState.BROKER_SOURCED_RISK_PRECHECK
    assert result.risk_budget_usd == Decimal("25.00")
    assert result.stressed_loss_usd == Decimal("13")
    assert not result.execution_permitted
    with pytest.raises(ValueError, match="cannot authorize"):
        replace(result, execution_permitted=True)


def test_small_pro_account_cannot_bypass_minimum_lot_and_costs() -> None:
    result = preview_policy_a_cash_risk(replace(
        inputs(), balance_usd=Decimal("300"), equity_usd=Decimal("300"),
        free_margin_usd=Decimal("300"),
    ))
    assert result.status is CashRiskState.DENY
    assert result.risk_budget_usd == Decimal("0.75")


def test_unknown_ledger_account_or_costs_reject() -> None:
    for item in (
        replace(inputs(), broker_identity_ok=False),
        replace(inputs(), period_cashflows_reconciled=False),
        replace(inputs(), broker_price_cost_source_verified=False),
        replace(inputs(), protective_stop_verified=False),
    ):
        assert preview_policy_a_cash_risk(item).status is CashRiskState.DENY
    assert preview_policy_a_cash_risk(replace(
        inputs(), commission_usd=Decimal("NaN")
    )).status is CashRiskState.DENY


def test_period_loss_and_streak_governor_block() -> None:
    assert "ADJUSTED_DAILY_LOSS_CAP_EXCEEDED" in preview_policy_a_cash_risk(
        replace(inputs(), adjusted_daily_loss_usd=Decimal("70"))
    ).reasons
    assert "ADJUSTED_WEEKLY_LOSS_CAP_EXCEEDED" in preview_policy_a_cash_risk(
        replace(inputs(), adjusted_weekly_loss_usd=Decimal("145"))
    ).reasons
    assert "DRAWDOWN_CASH_CAP_EXCEEDED" in preview_policy_a_cash_risk(
        replace(inputs(), drawdown_from_peak_usd=Decimal("490"))
    ).reasons
    assert "FULL_RISK_STREAK_PAUSE" in preview_policy_a_cash_risk(
        replace(inputs(), full_risk_loss_streak=Decimal("3"))
    ).reasons


def test_existing_frozen_m1_margin_and_lot_cap_reject() -> None:
    poor = preview_policy_a_cash_risk(
        replace(inputs(), broker_incremental_margin_usd=Decimal("2000"))
    )
    assert poor.status is CashRiskState.DENY
    assert "M1_POLICY_A_REJECT" in poor.reasons
    assert "ONLY_FROZEN_0_01_LOT_ALLOWED" in preview_policy_a_cash_risk(
        replace(inputs(), volume_lots=Decimal("0.02"))
    ).reasons
