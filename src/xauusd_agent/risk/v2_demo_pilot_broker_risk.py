"""Exness Pro DEMO pre-submission broker monetary consistency gate.

OFFLINE, deterministic, no MT5 import or broker method call. This compares a
separately acquired, timestamp-bound broker order_calc_profit/order_calc_margin
receipt to full frozen Policy A. It is NOT evidence of the receipt's origin,
no order_check/order_send and NEVER a broker execution authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from xauusd_agent.guards.event_guard import EventGuardDecision
from xauusd_agent.market.models import Quote, _require_utc
from xauusd_agent.risk.full_policy_a import (
    FullPolicyAInput,
    FullRiskDisposition,
    evaluate_full_policy_a,
)

ADMITTED_DEMO_FINGERPRINT = "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"
ADMITTED_SERVER = "Exness-MT5Trial15"
ADMITTED_COMPANY = "Exness Technologies Ltd"


class PilotRiskStatus(StrEnum):
    DENY = "DENY"
    MATH_RECONCILED_REVIEW_ONLY = "MATH_RECONCILED_REVIEW_ONLY"


@dataclass(frozen=True, slots=True)
class DemoBrokerRiskReceipt:
    """Data-only broker observation that an independent future MT5 adapter must attest.

    No account numbers, passwords, broker order tickets or credentials.
    """
    observed_utc: datetime
    account_fingerprint_sha256: str
    server: str
    company: str
    trade_mode: str
    symbol: str
    quote: Quote
    order_calc_profit_to_stop_usd: Decimal | None
    order_calc_margin_usd: Decimal | None
    positions_count: int | None
    orders_count: int | None
    position_and_deal_history_reconciled: bool
    source_epoch_reconciled: bool
    stop_and_symbol_metadata_broker_verified: bool
    current_session_verified_open: bool
    trading_via_external_python_disabled: bool

    def __post_init__(self) -> None:
        _require_utc(self.observed_utc, "observed_utc")


@dataclass(frozen=True, slots=True)
class DemoPilotRiskVerdict:
    status: PilotRiskStatus
    reason_codes: tuple[str, ...]
    mathematical_policy_a_pass: bool
    broker_stop_cash_loss_usd: Decimal | None = None
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("broker cash preflight never authorizes execution")


def evaluate_demo_pilot_risk(
    *,
    receipt: DemoBrokerRiskReceipt,
    policy: FullPolicyAInput,
    event_guard: EventGuardDecision | None,
) -> DemoPilotRiskVerdict:
    """Fail closed on mismatch, including any unknown field; never submit.

    Positive status states only that *supplied* data and mathematics reconcile.
    It is not proof of genuine MT5 sourcing, a strategy signal, order_check,
    live alert delivery, release activation or historical strategy expectancy.
    """
    reasons: list[str] = []

    def denied() -> DemoPilotRiskVerdict:
        return DemoPilotRiskVerdict(
            PilotRiskStatus.DENY, tuple(sorted(set(reasons))), False,
        )

    if (
        receipt.account_fingerprint_sha256 != ADMITTED_DEMO_FINGERPRINT
        or receipt.server != ADMITTED_SERVER
        or receipt.company != ADMITTED_COMPANY
        or receipt.trade_mode != "DEMO"
        or receipt.symbol != "XAUUSD"
    ):
        reasons.append("DEMO_ACCOUNT_OR_SYMBOL_IDENTITY_MISMATCH")
    if receipt.trading_via_external_python_disabled is not True:
        reasons.append("PYTHON_TRADING_PROTECTION_MUST_REMAIN_DISABLED_IN_REVIEW")
    if (
        receipt.positions_count != 0
        or receipt.orders_count != 0
        or receipt.position_and_deal_history_reconciled is not True
        or receipt.source_epoch_reconciled is not True
        or receipt.stop_and_symbol_metadata_broker_verified is not True
    ):
        reasons.append("BROKER_EXPOSURE_OR_SOURCE_UNKNOWN")
    if receipt.current_session_verified_open is not True:
        reasons.append("BROKER_CURRENT_SESSION_UNVERIFIED")
    if event_guard is None or not event_guard.entry_allowed:
        reasons.append("EVENT_GUARD_BLOCK_OR_UNVERIFIED")
    quote = receipt.quote
    if (
        quote.symbol != "XAUUSD"
        or quote.broker_time > receipt.observed_utc
        or quote.received_time > receipt.observed_utc
        or quote.received_time < quote.broker_time
        or receipt.observed_utc - quote.broker_time > timedelta(seconds=5)
    ):
        reasons.append("QUOTE_STALE_OR_INCOHERENT")
    if policy.symbol != "XAUUSD" or policy.volume_lots != Decimal("0.01"):
        reasons.append("WRONG_SYMBOL_OR_LOT")
    if policy.side not in {"BUY", "SELL"}:
        reasons.append("WRONG_SIDE")
    else:
        expected_entry = quote.ask if policy.side == "BUY" else quote.bid
        if policy.entry_worst != expected_entry:
            reasons.append("RISK_ENTRY_NOT_BOUND_TO_BROKER_QUOTE")
    if (
        policy.tick_size != quote.tick_size
        or policy.tick_size <= 0
        or policy.stop_adverse % policy.tick_size != 0
    ):
        reasons.append("STOP_OR_TICK_GRID_INVALID")

    profit = receipt.order_calc_profit_to_stop_usd
    margin = receipt.order_calc_margin_usd
    if (
        not isinstance(profit, Decimal)
        or not profit.is_finite()
        or profit >= 0
        or not isinstance(margin, Decimal)
        or not margin.is_finite()
        or margin <= 0
    ):
        reasons.append("BROKER_LOSS_OR_MARGIN_UNAVAILABLE")
    elif policy.incremental_margin_usd != margin:
        reasons.append("BROKER_MARGIN_NOT_BOUND_TO_POLICY_A")
    if reasons:
        return denied()

    result = evaluate_full_policy_a(policy)
    if result.disposition is not FullRiskDisposition.ALLOW_MATH_ONLY:
        reasons.extend(result.reasons)
        return denied()

    assert isinstance(profit, Decimal)
    assert result.l_price is not None
    # Rounding upward to the nearest cent and adverse tick is conservative.
    # A material mismatch signals stale symbol specifications or a misbound
    # order_calc_profit receipt and MUST NOT be silently accepted.
    broker_cash_loss = -profit
    one_tick = policy.tick_value_loss_per_lot_usd * policy.volume_lots
    if (
        result.l_price < broker_cash_loss
        or result.l_price - broker_cash_loss > one_tick + Decimal("0.01")
    ):
        reasons.append("BROKER_CASH_LOSS_CONFLICT_WITH_TICK_VALUE_POLICY_A")
        return denied()
    return DemoPilotRiskVerdict(
        PilotRiskStatus.MATH_RECONCILED_REVIEW_ONLY,
        ("NONEXECUTABLE_MT5_MONETARY_CONSISTENCY_ONLY",),
        True,
        broker_stop_cash_loss_usd=broker_cash_loss,
    )
