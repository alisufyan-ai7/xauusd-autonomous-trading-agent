"""Pure cash-risk preflight for a *future* Exness Pro DEMO runtime.

Does not call order_calc_profit/margin/order_check/send: all inputs must
come from a separately verified broker source and audit ledger. Current
Policy A numerical caps are never adjustable here. A positive preflight is
NOT a broker or execution permit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum

from xauusd_agent.risk.policy_a import (
    ExposureKnowledge,
    PolicyAInput,
    evaluate_policy_a,
)

MAX_RISK_FRACTION = Decimal("0.0025")
APPROVED_ALLOCATION = Decimal("10000")
CONCURRENT_CAP = Decimal("50")
DAILY_CAP = Decimal("75")
WEEKLY_CAP = Decimal("150")
DRAWDOWN_CAP = Decimal("500")
STREAK_PAUSE = Decimal("3")


class CashRiskState(StrEnum):
    DENY = "DENY"
    BROKER_SOURCED_RISK_PRECHECK = "BROKER_SOURCED_RISK_PRECHECK"


@dataclass(frozen=True, slots=True)
class BrokerCashRiskInputs:
    balance_usd: Decimal
    equity_usd: Decimal
    free_margin_usd: Decimal
    used_margin_usd: Decimal
    broker_incremental_margin_usd: Decimal
    stop_loss_price_usd: Decimal
    commission_usd: Decimal
    swap_usd: Decimal
    slippage_usd: Decimal
    gap_reserve_usd: Decimal
    existing_committed_risk_usd: Decimal
    adjusted_daily_loss_usd: Decimal
    adjusted_weekly_loss_usd: Decimal
    drawdown_from_peak_usd: Decimal
    full_risk_loss_streak: Decimal
    volume_lots: Decimal
    broker_identity_ok: bool
    broker_price_cost_source_verified: bool
    period_cashflows_reconciled: bool
    flat_exposure_verified: bool
    protective_stop_verified: bool


@dataclass(frozen=True, slots=True)
class CashRiskPreflight:
    status: CashRiskState
    reasons: tuple[str, ...]
    risk_budget_usd: Decimal | None = None
    planned_loss_usd: Decimal | None = None
    stressed_loss_usd: Decimal | None = None
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("cash-risk preflight cannot authorize an order")


def preview_policy_a_cash_risk(data: BrokerCashRiskInputs) -> CashRiskPreflight:
    def reject(*reasons: str) -> CashRiskPreflight:
        return CashRiskPreflight(CashRiskState.DENY, reasons)

    # Never treat unobserved costs, cash-flows or account identity as zero.
    if not all((
        data.broker_identity_ok,
        data.broker_price_cost_source_verified,
        data.period_cashflows_reconciled,
        data.flat_exposure_verified,
        data.protective_stop_verified,
    )):
        return reject("BROKER_OR_LEDGER_EVIDENCE_UNKNOWN")
    fields = (
        data.balance_usd, data.equity_usd, data.free_margin_usd,
        data.used_margin_usd, data.broker_incremental_margin_usd,
        data.stop_loss_price_usd, data.commission_usd, data.swap_usd,
        data.slippage_usd, data.gap_reserve_usd,
        data.existing_committed_risk_usd, data.adjusted_daily_loss_usd,
        data.adjusted_weekly_loss_usd, data.drawdown_from_peak_usd,
        data.full_risk_loss_streak, data.volume_lots,
    )
    if any(
        not isinstance(v, Decimal) or not v.is_finite() for v in fields
    ):
        return reject("UNKNOWN_OR_NONFINITE_MONETARY_INPUT")
    if any(x < 0 for x in fields[5:15]):
        return reject("NEGATIVE_OR_INCOHERENT_LOSS_INPUT")
    if data.balance_usd <= 0 or data.equity_usd <= 0:
        return reject("NO_ELIGIBLE_EQUITY")
    if data.volume_lots != Decimal("0.01"):
        return reject("ONLY_FROZEN_0_01_LOT_ALLOWED")
    if data.stop_loss_price_usd <= 0:
        return reject("INVALID_BROKER_STOP_LOSS_VALUE")
    eligible = min(data.balance_usd, data.equity_usd, APPROVED_ALLOCATION)
    ceiling = (MAX_RISK_FRACTION * eligible).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN,
    )
    planned = sum((
        data.stop_loss_price_usd,
        data.commission_usd,
        data.swap_usd,
        data.slippage_usd,
    ), Decimal(0))
    stressed = planned + data.gap_reserve_usd
    if stressed > ceiling:
        return CashRiskPreflight(
            CashRiskState.DENY, ("PLANNED_STRESSED_LOSS_EXCEEDS_POLICY_A",),
            risk_budget_usd=ceiling, planned_loss_usd=planned,
            stressed_loss_usd=stressed,
        )
    if data.existing_committed_risk_usd + stressed > CONCURRENT_CAP:
        return reject("CONCURRENT_CASH_CAP_EXCEEDED")
    if data.adjusted_daily_loss_usd + stressed > DAILY_CAP:
        return reject("ADJUSTED_DAILY_LOSS_CAP_EXCEEDED")
    if data.adjusted_weekly_loss_usd + stressed > WEEKLY_CAP:
        return reject("ADJUSTED_WEEKLY_LOSS_CAP_EXCEEDED")
    if data.drawdown_from_peak_usd + stressed > DRAWDOWN_CAP:
        return reject("DRAWDOWN_CASH_CAP_EXCEEDED")
    if data.full_risk_loss_streak >= STREAK_PAUSE:
        return reject("FULL_RISK_STREAK_PAUSE")

    margin = evaluate_policy_a(PolicyAInput(
        symbol="XAUUSD", requested_volume_lots=data.volume_lots,
        account_equity=data.equity_usd,
        account_free_margin=data.free_margin_usd,
        account_margin_used=data.used_margin_usd,
        incremental_margin=data.broker_incremental_margin_usd,
        current_adverse_cost=planned,
        stressed_adverse_cost=stressed,
        exposure=ExposureKnowledge.CONFIRMED_ZERO,
        fingerprint_matches=True,
        protective_stop_present=True,
    ))
    if not margin.allowed:
        return reject("M1_POLICY_A_" + margin.disposition.value, *margin.reason_codes)
    return CashRiskPreflight(
        CashRiskState.BROKER_SOURCED_RISK_PRECHECK,
        ("NONEXECUTABLE_POLICY_A_CASH_SCREEN_ONLY",),
        risk_budget_usd=ceiling,
        planned_loss_usd=planned,
        stressed_loss_usd=stressed,
    )
