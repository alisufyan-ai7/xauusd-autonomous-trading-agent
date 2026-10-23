"""Broker-bound full Policy A *preflight* for future Exness Pro DEMO.

Queries the real attached MT5 broker, never sends/orders/checks orders.
The admitted cash journal supplies period baselines. Price loss is checked
against BOTH MetaQuotes order_calc_profit and per-tick loss-value arithmetic.
Missing cost calibration, event/source authority or a crossed epoch DENIES.
A mathematical pass is NOT an order permit; the S2 hard stop stays active.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from typing import Any

from xauusd_agent.risk.full_policy_a import (
    FullPolicyAInput,
    FullPolicyAResult,
    evaluate_full_policy_a,
)

from .broker_money_readonly import EXPECTED_ACCOUNT_SHA256, EXPECTED_COMPANY, EXPECTED_SERVER
from .envelope import DemoSafetyError
from .mt5_demo import _decimal, _record
from .prospective_cash_journal import CashObservation, CashRiskBaseline

LOT = Decimal("0.01")
MAX_TICK_AGE = timedelta(seconds=2)


@dataclass(frozen=True, slots=True)
class BrokerStopProposal:
    """Pure mechanical buy/sell stop with attached fixed SL + final TP."""
    side: str
    entry: Decimal
    stop: Decimal
    take_profit: Decimal

    def validate(self) -> None:
        if self.side not in ("BUY", "SELL"):
            raise DemoSafetyError("unsupported broker stop direction")
        for x in (self.entry, self.stop, self.take_profit):
            if type(x) is not Decimal or not x.is_finite() or x <= 0:
                raise DemoSafetyError("broker stop price missing")
        if not (
            (self.side == "BUY" and self.stop < self.entry < self.take_profit)
            or (self.side == "SELL" and self.take_profit < self.entry < self.stop)
        ):
            raise DemoSafetyError("adverse SL / trendward TP required")


@dataclass(frozen=True, slots=True)
class BoundAdverseCost:
    """Adverse costs supplied by a separately verified calibration record.

    Hash equality detects drift but does NOT prove calibration quality, expiry
    or license. That evidence and admission remain a separate release gate.
    """
    calibration_id: str
    evidence_sha256: str
    commission_roundtrip_usd: Decimal
    swap_reserve_usd: Decimal
    slippage_reserve_usd: Decimal
    gap_reserve_usd: Decimal

    def digest(self) -> str:
        if (
            not self.calibration_id
            or len(self.evidence_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.evidence_sha256)
        ):
            raise DemoSafetyError("cost source provenance incomplete")
        items = (
            self.commission_roundtrip_usd, self.swap_reserve_usd,
            self.slippage_reserve_usd, self.gap_reserve_usd,
        )
        if any(type(x) is not Decimal or not x.is_finite() or x < 0 for x in items):
            raise DemoSafetyError("cost reserve not finite nonnegative")
        raw = {
            "calibration_id": self.calibration_id,
            "evidence_sha256": self.evidence_sha256,
            "commission_roundtrip_usd": str(items[0]),
            "swap_reserve_usd": str(items[1]),
            "slippage_reserve_usd": str(items[2]),
            "gap_reserve_usd": str(items[3]),
        }
        return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class BrokerPolicyReceipt:
    decision: FullPolicyAResult
    tick_utc: datetime
    broker_price_loss_usd: Decimal
    broker_incremental_margin_usd: Decimal
    symbol_tick_loss_usd_per_lot: Decimal
    cost_digest_sha256: str
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if self.execution_permitted:
            raise ValueError("broker policy preview cannot be an execution permit")


def _check_alignment(value: Decimal, tick: Decimal, label: str) -> None:
    if (value / tick) != (value / tick).to_integral_value():
        raise DemoSafetyError(f"{label} off the broker tick grid")


def preview_broker_full_policy_a(
    mt5: Any,
    *,
    now: datetime,
    cash: CashObservation,
    baseline: CashRiskBaseline,
    proposal: BrokerStopProposal,
    costs: BoundAdverseCost,
    expected_cost_sha256: str,
    official_guard_pass: bool,
    session_source_verified: bool,
) -> BrokerPolicyReceipt:
    """Observe one epoch and evaluate *all* frozen money caps, never submit.

    Caller-derived status flags cannot authorize broker execution; this
    release preview only returns FullPolicyAResult mathematics.
    """
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise DemoSafetyError("exact UTC observation clock required")
    proposal.validate()
    digest = costs.digest()
    if digest != expected_cost_sha256:
        raise DemoSafetyError("cost calibration not anchored to approved digest")
    if official_guard_pass is not True or session_source_verified is not True:
        raise DemoSafetyError("unknown official news or session coverage")
    if (
        baseline.admitted is not True or baseline.no_order_authority is not True
        or cash.broker_history_complete is not True
        or cash.observed_utc > now
        or now - cash.observed_utc > timedelta(seconds=2)
        or cash.account_fingerprint != EXPECTED_ACCOUNT_SHA256
        or cash.positions_count != 0 or cash.orders_count != 0
        or cash.account_currency != "USD"
    ):
        raise DemoSafetyError("cash baseline not same-epoch broker complete")
    if any(
        x is None
        for x in (
            baseline.day_start_equity, baseline.week_start_equity,
            baseline.normalized_high_water, baseline.loss_equivalent_streak,
        )
    ):
        raise DemoSafetyError("period equity baselines unavailable")
    term = _record(mt5.terminal_info(), "terminal")
    account = _record(mt5.account_info(), "account")
    if (
        term.get("connected") is not True
        or type(account.get("trade_mode")) is not int
        or account["trade_mode"] != 0
        or account.get("company") != EXPECTED_COMPANY
        or account.get("server") != EXPECTED_SERVER
        or account.get("currency") != "USD"
        or type(account.get("login")) is not int
    ):
        raise DemoSafetyError("wrong/disconnected/LIVE account")
    fp = hashlib.sha256(
        f"{EXPECTED_COMPANY}|{EXPECTED_SERVER}|{account['login']}|USD".encode()
    ).hexdigest()
    if fp != EXPECTED_ACCOUNT_SHA256:
        raise DemoSafetyError("unadmitted DEMO account")
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None or tuple(positions) or tuple(orders):
        raise DemoSafetyError("flat broker exposure not verified")
    bid = _record(mt5.symbol_info_tick("XAUUSD"), "symbol tick")
    specs = _record(mt5.symbol_info("XAUUSD"), "symbol specs")
    time_ms = bid.get("time_msc")
    if type(time_ms) is not int or time_ms <= 0:
        raise DemoSafetyError("broker tick missing timestamp")
    tick_utc = datetime.fromtimestamp(time_ms / 1000, UTC)
    if tick_utc > now + timedelta(seconds=1) or now - tick_utc > MAX_TICK_AGE:
        raise DemoSafetyError("stale broker quote")
    ask_price, bid_price = _decimal(bid.get("ask"), "ask"), _decimal(bid.get("bid"), "bid")
    if ask_price <= bid_price or bid_price <= 0:
        raise DemoSafetyError("broker quote invalid")
    if specs.get("trade_mode") != getattr(mt5, "SYMBOL_TRADE_MODE_FULL", None):
        raise DemoSafetyError("XAUUSD broker session not tradable")
    tick_size = _decimal(specs.get("trade_tick_size"), "trade tick size")
    tick_loss = _decimal(specs.get("trade_tick_value_loss"), "trade tick loss")
    vol_min = _decimal(specs.get("volume_min"), "volume minimum")
    vol_step = _decimal(specs.get("volume_step"), "volume step")
    point = _decimal(specs.get("point"), "point")
    broker_stop_dist = Decimal(int(specs.get("trade_stops_level", -1))) * point
    if (
        tick_size <= 0 or tick_loss <= 0 or vol_min <= 0 or vol_step <= 0
        or point <= 0 or broker_stop_dist < 0
        or LOT < vol_min or (LOT - vol_min) % vol_step != 0
    ):
        raise DemoSafetyError("symbol volume/tick/stops not verified")
    for title, price in (
        ("entry", proposal.entry), ("SL", proposal.stop),
        ("TP", proposal.take_profit),
    ):
        _check_alignment(price, tick_size, title)
    if (
        (proposal.side == "BUY" and proposal.entry <= ask_price + broker_stop_dist)
        or (proposal.side == "SELL" and proposal.entry >= bid_price - broker_stop_dist)
    ):
        raise DemoSafetyError("STOP entry no longer beyond executable market")
    if (
        (proposal.side == "BUY" and proposal.entry - proposal.stop < broker_stop_dist)
        or (proposal.side == "SELL" and proposal.stop - proposal.entry < broker_stop_dist)
    ):
        raise DemoSafetyError("protective SL violates broker stop level")
    order_type = (
        mt5.ORDER_TYPE_BUY if proposal.side == "BUY"
        else mt5.ORDER_TYPE_SELL
    )
    raw_loss = mt5.order_calc_profit(
        order_type, "XAUUSD", float(LOT),
        float(proposal.entry), float(proposal.stop),
    )
    raw_margin = mt5.order_calc_margin(
        order_type, "XAUUSD", float(LOT), float(proposal.entry),
    )
    loss = _decimal(raw_loss, "order_calc_profit")
    margin = _decimal(raw_margin, "order_calc_margin")
    if loss >= 0 or margin <= 0:
        raise DemoSafetyError("broker loss/margin calculation rejected")
    distance_ticks = (abs(proposal.entry - proposal.stop) / tick_size).to_integral_value(
        rounding=ROUND_CEILING
    )
    tick_value_based = distance_ticks * tick_loss * LOT
    # Broker profit/margin are mandatory independent consistency checks.
    if abs(tick_value_based + loss) > Decimal("0.02"):
        raise DemoSafetyError("broker calculated loss contradicts tick cash value")
    balance = _decimal(account.get("balance"), "balance")
    equity = _decimal(account.get("equity"), "equity")
    used_margin = _decimal(account.get("margin"), "used margin")
    free_margin = _decimal(account.get("margin_free"), "free margin")
    if (
        abs(balance - cash.balance) > Decimal("0.01")
        or abs(equity - cash.equity) > Decimal("0.01")
    ):
        raise DemoSafetyError("broker cash snapshot changed across preflight")
    if free_margin < 0 or used_margin < 0:
        raise DemoSafetyError("broker margin fields invalid")
    if mt5.positions_get() is None or mt5.orders_get() is None:
        raise DemoSafetyError("post-preflight exposure unavailable")
    if tuple(mt5.positions_get()) or tuple(mt5.orders_get()):
        raise DemoSafetyError("exposure changed during calculation")
    adverse_price = max(-loss, tick_value_based)
    current_cost = (
        adverse_price + costs.commission_roundtrip_usd
        + costs.swap_reserve_usd + costs.slippage_reserve_usd
    )
    stressed_cost = current_cost + costs.gap_reserve_usd
    data = FullPolicyAInput(
        symbol="XAUUSD", side=proposal.side, volume_lots=LOT,
        volume_min=vol_min, volume_step=vol_step,
        entry_worst=proposal.entry, stop_adverse=proposal.stop,
        tick_size=tick_size, tick_value_loss_per_lot_usd=tick_loss,
        commission_usd=costs.commission_roundtrip_usd,
        swap_buffer_usd=costs.swap_reserve_usd,
        slippage_buffer_usd=costs.slippage_reserve_usd,
        gap_buffer_usd=costs.gap_reserve_usd,
        balance_usd=balance, equity_usd=equity,
        margin_used_usd=used_margin, free_margin_usd=free_margin,
        incremental_margin_usd=margin, m1_current_adverse_cost_usd=current_cost,
        m1_stressed_adverse_cost_usd=stressed_cost,
        concurrent_committed_usd=Decimal(0),
        existing_incremental_loss_usd=Decimal(0),
        day_start_equity_usd=baseline.day_start_equity,
        day_external_flows_usd=Decimal(0),
        week_start_equity_usd=baseline.week_start_equity,
        week_external_flows_usd=Decimal(0),
        inception_external_flows_usd=Decimal(0),
        normalized_high_water_usd=baseline.normalized_high_water,
        loss_equivalent_streak=baseline.loss_equivalent_streak,
        snapshot_reconciled=True, accounting_reconciled=True,
        exposure_known_and_owned=True, sources_verified=True,
        symbol_verified=True, calibration_admitted=True,
        session_event_guard_pass=True, protective_stop_broker_confirmable=True,
    )
    return BrokerPolicyReceipt(
        decision=evaluate_full_policy_a(data),
        tick_utc=tick_utc, broker_price_loss_usd=adverse_price,
        broker_incremental_margin_usd=margin,
        symbol_tick_loss_usd_per_lot=tick_loss,
        cost_digest_sha256=digest,
    )
