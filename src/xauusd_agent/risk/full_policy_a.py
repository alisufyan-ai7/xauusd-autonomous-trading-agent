"""Pure, broker-free full Policy A cash-risk math. NOT execution approval.

The caller must independently verify and reconcile *every* supplied field
from one epoch, boundary snapshots, cashflow journal, position/order records,
admitted costs, session guard and symbol specs. An untrusted input or a
missing methodology in frozen Policy A §12 cannot be turned into an ALLOW.

This math engine has no MT5 import, order API, file I/O, or side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from enum import StrEnum
from typing import Final

CENT: Final = Decimal("0.01")
ALLOCATION: Final = Decimal("10000")
RISK_RATE: Final = Decimal("0.0025")
TRADE_CAP_MAX: Final = Decimal("25.00")
CONCURRENT_CAP: Final = Decimal("50.00")
DAILY_CAP: Final = Decimal("75.00")
WEEKLY_CAP: Final = Decimal("150.00")
DRAWDOWN_CAP: Final = Decimal("500.00")
PAUSE_Q: Final = Decimal("3.00")
VOLUME_CAP: Final = Decimal("0.01")
MARGIN_LEVEL_MIN: Final = Decimal("1000")
FREE_MARGIN_FRACTION_MIN: Final = Decimal("0.90")
STRESS_MARGIN_MULTIPLIER: Final = Decimal("2")


class FullRiskDisposition(StrEnum):
    ALLOW_MATH_ONLY = "ALLOW_MATH_ONLY"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"


@dataclass(frozen=True, slots=True)
class FullPolicyAInput:
    # Caller supplies *verified* values, never best-effort estimates.
    symbol: str
    side: str  # BUY or SELL
    volume_lots: Decimal
    volume_min: Decimal
    volume_step: Decimal
    entry_worst: Decimal  # worst executable BUY ask / SELL bid
    stop_adverse: Decimal  # already broker-normalized protective stop
    tick_size: Decimal
    tick_value_loss_per_lot_usd: Decimal
    commission_usd: Decimal
    swap_buffer_usd: Decimal
    slippage_buffer_usd: Decimal
    gap_buffer_usd: Decimal
    balance_usd: Decimal
    equity_usd: Decimal
    margin_used_usd: Decimal
    free_margin_usd: Decimal
    incremental_margin_usd: Decimal
    m1_current_adverse_cost_usd: Decimal
    m1_stressed_adverse_cost_usd: Decimal
    concurrent_committed_usd: Decimal
    existing_incremental_loss_usd: Decimal
    day_start_equity_usd: Decimal
    day_external_flows_usd: Decimal
    week_start_equity_usd: Decimal
    week_external_flows_usd: Decimal
    inception_external_flows_usd: Decimal
    normalized_high_water_usd: Decimal
    loss_equivalent_streak: Decimal
    # Flag values are *claims* that the upstream independently verified adapter
    # must prove; this pure evaluator is NOT a source authenticity validator.
    snapshot_reconciled: bool
    accounting_reconciled: bool
    exposure_known_and_owned: bool
    sources_verified: bool
    symbol_verified: bool
    calibration_admitted: bool
    session_event_guard_pass: bool
    protective_stop_broker_confirmable: bool


@dataclass(frozen=True, slots=True)
class FullPolicyAResult:
    disposition: FullRiskDisposition
    reasons: tuple[str, ...]
    per_trade_cap: Decimal | None = None
    l_price: Decimal | None = None
    l_plan: Decimal | None = None
    concurrent_prospective: Decimal | None = None
    day_loss: Decimal | None = None
    day_prospective: Decimal | None = None
    week_loss: Decimal | None = None
    week_prospective: Decimal | None = None
    drawdown: Decimal | None = None
    drawdown_prospective: Decimal | None = None
    m1_current_margin_percent: Decimal | None = None
    m1_stressed_margin_percent: Decimal | None = None

    @property
    def mathematics_pass(self) -> bool:
        return self.disposition is FullRiskDisposition.ALLOW_MATH_ONLY


def _decimal(value: object) -> bool:
    return type(value) is Decimal and value.is_finite()


def _cent_up(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_CEILING)


def _cent_down(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_FLOOR)


def evaluate_full_policy_a(data: FullPolicyAInput) -> FullPolicyAResult:
    """Evaluate all frozen monetary gates without creating broker authority.

    Strict < current day/week/drawdown, <= prospective day/week/drawdown.
    Already reflected unrealized P/L is not counted again as future loss.
    Current and stressed M1 test independently; one may not waive another.
    """
    uncertain = []
    for name in (
        "snapshot_reconciled", "accounting_reconciled",
        "exposure_known_and_owned", "sources_verified", "symbol_verified",
        "calibration_admitted", "session_event_guard_pass",
        "protective_stop_broker_confirmable",
    ):
        if getattr(data, name) is not True:
            uncertain.append("UNVERIFIED_" + name.upper())
    fields = (
        "volume_lots", "volume_min", "volume_step", "entry_worst",
        "stop_adverse", "tick_size", "tick_value_loss_per_lot_usd",
        "commission_usd", "swap_buffer_usd", "slippage_buffer_usd",
        "gap_buffer_usd", "balance_usd", "equity_usd", "margin_used_usd",
        "free_margin_usd", "incremental_margin_usd",
        "m1_current_adverse_cost_usd", "m1_stressed_adverse_cost_usd",
        "concurrent_committed_usd", "existing_incremental_loss_usd",
        "day_start_equity_usd", "day_external_flows_usd",
        "week_start_equity_usd", "week_external_flows_usd",
        "inception_external_flows_usd", "normalized_high_water_usd",
        "loss_equivalent_streak",
    )
    uncertain.extend("UNKNOWN_" + name.upper() for name in fields
                     if not _decimal(getattr(data, name)))
    if type(data.symbol) is not str or data.symbol != "XAUUSD":
        uncertain.append("UNKNOWN_OR_WRONG_SYMBOL")
    if type(data.side) is not str or data.side not in ("BUY", "SELL"):
        uncertain.append("UNKNOWN_SIDE")
    if uncertain:
        return FullPolicyAResult(FullRiskDisposition.QUARANTINE, tuple(uncertain))

    # Guard signs before allowing numerical calculations or division.
    invalid = []
    positive_fields = (
        "volume_lots", "volume_min", "volume_step", "entry_worst",
        "stop_adverse", "tick_size", "tick_value_loss_per_lot_usd",
        "balance_usd", "equity_usd", "day_start_equity_usd",
        "week_start_equity_usd", "normalized_high_water_usd",
        "incremental_margin_usd",
    )
    for name in positive_fields:
        if getattr(data, name) <= 0:
            invalid.append("NONPOSITIVE_" + name.upper())
    nonnegative_fields = (
        "commission_usd", "swap_buffer_usd", "slippage_buffer_usd",
        "gap_buffer_usd", "margin_used_usd", "free_margin_usd",
        "m1_current_adverse_cost_usd", "m1_stressed_adverse_cost_usd",
        "concurrent_committed_usd", "existing_incremental_loss_usd",
        "loss_equivalent_streak",
    )
    invalid.extend("NEGATIVE_" + name.upper() for name in nonnegative_fields
                   if getattr(data, name) < 0)
    if data.volume_lots > VOLUME_CAP:
        invalid.append("V1_VOLUME_CAP")
    if data.volume_lots < data.volume_min:
        invalid.append("BELOW_BROKER_VOLUME_MIN")
    if data.volume_step > 0 and data.volume_min > 0:
        if (data.volume_lots - data.volume_min) % data.volume_step != 0:
            invalid.append("BROKER_VOLUME_GRID")
    if data.side == "BUY" and data.stop_adverse >= data.entry_worst:
        invalid.append("BUY_STOP_NOT_ADVERSE")
    if data.side == "SELL" and data.stop_adverse <= data.entry_worst:
        invalid.append("SELL_STOP_NOT_ADVERSE")
    if data.m1_stressed_adverse_cost_usd < data.m1_current_adverse_cost_usd:
        invalid.append("STRESS_BELOW_CURRENT_COST")
    if invalid:
        return FullPolicyAResult(FullRiskDisposition.REJECT, tuple(invalid))

    with localcontext() as ctx:
        ctx.prec = 50
        capital = min(data.balance_usd, data.equity_usd, ALLOCATION)
        cap = _cent_down(RISK_RATE * capital)

        # Never round the number of adverse price ticks down. The documented
        # one-lot tick-value-loss must be independently checked for each side.
        distance = (data.entry_worst - data.stop_adverse
                    if data.side == "BUY" else
                    data.stop_adverse - data.entry_worst)
        adverse_ticks = (distance / data.tick_size).to_integral_value(
            rounding=ROUND_CEILING
        )
        l_price = _cent_up(adverse_ticks * data.tick_value_loss_per_lot_usd *
                           data.volume_lots)
        l_plan = _cent_up(
            l_price + data.commission_usd + data.swap_buffer_usd
            + data.slippage_buffer_usd + data.gap_buffer_usd
        )
        concurrent = data.concurrent_committed_usd + l_plan
        future = data.existing_incremental_loss_usd + l_plan
        day_loss = max(Decimal(0), data.day_start_equity_usd -
                       (data.equity_usd - data.day_external_flows_usd))
        week_loss = max(Decimal(0), data.week_start_equity_usd -
                        (data.equity_usd - data.week_external_flows_usd))
        normalized_equity = data.equity_usd - data.inception_external_flows_usd
        dd = max(Decimal(0), data.normalized_high_water_usd - normalized_equity)

        reasons = []
        if l_plan > cap or cap <= 0:
            reasons.append("POLICY_A_PER_TRADE_STOP_LOSS_USD")
        if concurrent > CONCURRENT_CAP:
            reasons.append("POLICY_A_CONCURRENT_USD")
        if day_loss >= DAILY_CAP or day_loss + future > DAILY_CAP:
            reasons.append("POLICY_A_DAILY_LOSS_USD")
        if week_loss >= WEEKLY_CAP or week_loss + future > WEEKLY_CAP:
            reasons.append("POLICY_A_WEEKLY_LOSS_USD")
        if dd >= DRAWDOWN_CAP or dd + future > DRAWDOWN_CAP:
            reasons.append("POLICY_A_DRAWDOWN_USD")
        if data.loss_equivalent_streak >= PAUSE_Q:
            reasons.append("POLICY_A_FULL_RISK_EQUIVALENT_PAUSE")

        cur_equity = data.equity_usd - data.m1_current_adverse_cost_usd
        cur_used = data.margin_used_usd + data.incremental_margin_usd
        cur_free = data.free_margin_usd - data.m1_current_adverse_cost_usd - data.incremental_margin_usd
        stress_equity = data.equity_usd - data.m1_stressed_adverse_cost_usd
        stress_used = (data.margin_used_usd +
                       STRESS_MARGIN_MULTIPLIER * data.incremental_margin_usd)
        stress_free = (data.free_margin_usd -
                       data.m1_stressed_adverse_cost_usd -
                       STRESS_MARGIN_MULTIPLIER * data.incremental_margin_usd)
        cur_level = (cur_equity / cur_used * 100) if cur_used > 0 else None
        stress_level = (stress_equity / stress_used * 100) if stress_used > 0 else None
        if (cur_equity <= 0 or cur_free < 0
                or (cur_level is not None and cur_level < MARGIN_LEVEL_MIN)
                or cur_free < FREE_MARGIN_FRACTION_MIN * cur_equity):
            reasons.append("POLICY_A_M1_CURRENT")
        if (stress_equity <= 0 or stress_free < 0
                or (stress_level is not None and stress_level < MARGIN_LEVEL_MIN)
                or stress_free < FREE_MARGIN_FRACTION_MIN * stress_equity):
            reasons.append("POLICY_A_M1_STRESSED")

    return FullPolicyAResult(
        disposition=(FullRiskDisposition.REJECT if reasons
                     else FullRiskDisposition.ALLOW_MATH_ONLY),
        reasons=tuple(reasons) if reasons else ("MATHEMATICS_ONLY_ALL_FROZEN_LIMITS_PASS",),
        per_trade_cap=cap,
        l_price=l_price,
        l_plan=l_plan,
        concurrent_prospective=concurrent,
        day_loss=day_loss, day_prospective=day_loss + future,
        week_loss=week_loss, week_prospective=week_loss + future,
        drawdown=dd, drawdown_prospective=dd + future,
        m1_current_margin_percent=cur_level,
        m1_stressed_margin_percent=stress_level,
    )
