"""Owner-attended real Exness DEMO broker cash and margin observation.

Only terminal/account/symbol/quote/positions/orders/history and
order_calc_profit/order_calc_margin are called. NEVER order_check/order_send,
never toggle the external Python trading setting or select/switch accounts.
The output is aggregate sanitized evidence, NOT risk approval or deployment.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from .envelope import DemoSafetyError
from .mt5_demo import _decimal, _record

EXPECTED_ACCOUNT_SHA256 = (
    "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"
)
EXPECTED_SERVER = "Exness-MT5Trial15"
EXPECTED_COMPANY = "Exness Technologies Ltd"
LOT = Decimal("0.01")
REFERENCE_DISTANCE = Decimal("5.00")


def _identity(port: Any) -> dict[str, Any]:
    term = _record(port.terminal_info(), "terminal_info")
    account = _record(port.account_info(), "account_info")
    if term.get("connected") is not True or term.get("tradeapi_disabled") is not True:
        raise DemoSafetyError("terminal disconnected or external Python trading not disabled")
    if type(account.get("trade_mode")) is not int or account["trade_mode"] != 0:
        raise DemoSafetyError("MT5 account is not DEMO")
    if (
        account.get("company") != EXPECTED_COMPANY
        or account.get("server") != EXPECTED_SERVER
        or account.get("currency") != "USD"
    ):
        raise DemoSafetyError("Exness account broker/server/currency mismatch")
    login = account.get("login")
    if login is None:
        raise DemoSafetyError("MT5 login missing")
    raw = f"{account['company']}|{account['server']}|{login}|{account['currency']}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if digest != EXPECTED_ACCOUNT_SHA256:
        raise DemoSafetyError("MT5 DEMO fingerprint mismatch")
    if account.get("trade_allowed") is False:
        # A readonly profile is allowed to observe monetary calculations,
        # but this state is NOT a reason to enable account trading.
        pass
    return account


def _flat(port: Any) -> None:
    positions = port.positions_get()
    orders = port.orders_get()
    if positions is None or orders is None or tuple(positions) or tuple(orders):
        raise DemoSafetyError("zero open orders and positions not established")


def _price_tick(time_value: Any, now: datetime) -> datetime:
    try:
        time_msc = int(time_value)
    except (TypeError, ValueError) as exc:
        raise DemoSafetyError("broker tick timestamp invalid") from exc
    if time_msc <= 0:
        raise DemoSafetyError("broker tick timestamp missing")
    observed = datetime.fromtimestamp(time_msc / 1000, tz=UTC)
    if observed > now + timedelta(seconds=1) or now - observed > timedelta(seconds=5):
        raise DemoSafetyError("MT5 tick stale or future")
    return observed


def _broker_side(
    port: Any,
    *,
    side: str,
    tick: dict[str, Any],
    tick_size: Decimal,
) -> dict[str, str]:
    price = _decimal(tick["ask" if side == "BUY" else "bid"], "broker quote")
    if price <= 0:
        raise DemoSafetyError("invalid executable price")
    raw_stop = price + (REFERENCE_DISTANCE if side == "SELL" else -REFERENCE_DISTANCE)
    if raw_stop <= 0:
        raise DemoSafetyError("reference stop below zero")
    stop = (raw_stop / tick_size).to_integral_value() * tick_size
    order_type = port.ORDER_TYPE_BUY if side == "BUY" else port.ORDER_TYPE_SELL
    cash_value = port.order_calc_profit(
        order_type, "XAUUSD", float(LOT), float(price), float(stop)
    )
    margin_value = port.order_calc_margin(
        order_type, "XAUUSD", float(LOT), float(price)
    )
    cash = _decimal(cash_value, "broker order_calc_profit")
    margin = _decimal(margin_value, "broker order_calc_margin")
    if cash >= 0 or margin <= 0:
        raise DemoSafetyError("broker hypothetical protective loss or margin invalid")
    return {
        "side": side,
        "reference_stop_distance_usd_per_oz": str(REFERENCE_DISTANCE),
        "broker_reference_stop_loss_cash_usd": str(-cash),
        "broker_margin_for_0_01_lot_usd": str(margin),
    }


def inspect_real_demo_money(port: Any, *, now: datetime) -> dict[str, object]:
    """Solely read broker data. Port must be initialized by the caller.

    No receipt claiming a complete, independently calibrated Policy A source
    may be constructed from these summary amounts.
    """
    if now.tzinfo != UTC:
        raise DemoSafetyError("explicit UTC clock required")
    account = _identity(port)
    _flat(port)
    info = _record(port.symbol_info("XAUUSD"), "symbol_info")
    tick = _record(port.symbol_info_tick("XAUUSD"), "symbol_info_tick")
    full_mode = getattr(port, "SYMBOL_TRADE_MODE_FULL", None)
    if full_mode is None or info.get("trade_mode") is None or info["trade_mode"] != full_mode:
        raise DemoSafetyError("XAUUSD instrument is not in full trading mode")
    tick_size = _decimal(info.get("trade_tick_size"), "trade_tick_size")
    tick_loss = _decimal(info.get("trade_tick_value_loss"), "trade_tick_value_loss")
    volume_min = _decimal(info.get("volume_min"), "volume_min")
    volume_step = _decimal(info.get("volume_step"), "volume_step")
    if (
        tick_size <= 0 or tick_loss <= 0
        or volume_min <= 0 or volume_step <= 0
        or LOT < volume_min or (LOT - volume_min) % volume_step != 0
    ):
        raise DemoSafetyError("broker symbol cash/tick/lot specification invalid")
    broker_time = _price_tick(tick.get("time_msc"), now)
    bid = _decimal(tick.get("bid"), "bid")
    ask = _decimal(tick.get("ask"), "ask")
    if bid <= 0 or ask <= bid:
        raise DemoSafetyError("crossed or unusable XAUUSD quote")
    equity = _decimal(account.get("equity"), "equity")
    balance = _decimal(account.get("balance"), "balance")
    used = _decimal(account.get("margin"), "margin")
    free = _decimal(account.get("margin_free"), "margin_free")
    if balance <= 0 or equity <= 0 or used < 0 or free <= 0:
        raise DemoSafetyError("account balance/equity/margin invalid")
    # History is read to diagnose cash accounting completeness. A deal count
    # NEVER proves high-water equity, daily boundary cash flows or loss streak.
    deals = port.history_deals_get(datetime(2020, 1, 1, tzinfo=UTC), now)
    if deals is None:
        raise DemoSafetyError("broker history_deals_get returned no data")
    results = [
        _broker_side(port, side=side, tick=tick, tick_size=tick_size)
        for side in ("BUY", "SELL")
    ]
    _flat(port)
    _identity(port)
    return {
        "status": "REAL_BROKER_READONLY_MONEY_CAPTURE_NOT_ORDER_ADMISSION",
        "observed_utc": now.isoformat(),
        "broker_tick_utc": broker_time.isoformat(),
        "broker": EXPECTED_COMPANY,
        "server": EXPECTED_SERVER,
        "account_fingerprint_sha256": EXPECTED_ACCOUNT_SHA256,
        "mode": "DEMO",
        "symbol": "XAUUSD",
        "lot_tested": "0.01",
        "balance_usd": str(balance),
        "equity_usd": str(equity),
        "margin_used_usd": str(used),
        "free_margin_usd": str(free),
        "spread_usd_per_oz": str(ask - bid),
        "tick_size": str(tick_size),
        "tick_value_loss_per_lot_usd": str(tick_loss),
        "historical_deal_count_unclassified": len(tuple(deals)),
        "hypothetical_side_calculations": results,
        "history_cashflow_and_loss_streak_reconciled": False,
        "event_guard_live_source_admitted": False,
        "full_policy_a_runtime_admitted": False,
        "strategy_direction_qualified": False,
        "execution_permitted": False,
        "order_check_calls": 0,
        "order_send_calls": 0,
        "external_python_trading_disabled": True,
    }
