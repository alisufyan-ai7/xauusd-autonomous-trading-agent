"""Actual MetaTrader5 account + complete cash-deal source for DEMO policy.

The port reads existing MT5 observations only. It does not accept caller
assertions of historical completeness: balance must reconcile to the sum of
all dated broker balance/trade/fee cash entries from 2000-01-01 UTC. Its
output is the pure prospective cash journal's own data model, not an order
permit. A trading-capable adapter must independently recheck every source
immediately before order_check/order_send.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .envelope import DemoSafetyError
from .prospective_cash_journal import CashDeal, CashObservation

_EXPECTED_SHA = "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"
_EXPECTED_COMPANY = "Exness Technologies Ltd"
_EXPECTED_SERVER = "Exness-MT5Trial15"
_START = datetime(2000, 1, 1, tzinfo=UTC)


def _row(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        raise DemoSafetyError(f"{label} unavailable")
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if hasattr(value, "__dict__"):
        return vars(value)
    raise DemoSafetyError(f"{label} unrecognized")


def _cash(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise DemoSafetyError(f"{field} not broker cash decimal") from exc
    if not result.is_finite():
        raise DemoSafetyError(f"{field} not finite")
    return result


def _deal_to_cash(mt5: Any, deal: Any, observed_utc: datetime) -> CashDeal:
    d = _row(deal, "history deal")
    kinds = {
        getattr(mt5, "DEAL_TYPE_BALANCE", -9000): "BALANCE",
        getattr(mt5, "DEAL_TYPE_CREDIT", -9001): "CREDIT",
        getattr(mt5, "DEAL_TYPE_BUY", -9002): "BUY",
        getattr(mt5, "DEAL_TYPE_SELL", -9003): "SELL",
    }
    kind = kinds.get(d.get("type"))
    if kind is None:
        raise DemoSafetyError("unknown broker history deal cash class")
    deal_id = d.get("ticket")
    if type(deal_id) is not int or deal_id <= 0:
        raise DemoSafetyError("unusable broker deal ticket")
    millis = d.get("time_msc")
    if type(millis) is int and millis > 0:
        when = datetime.fromtimestamp(millis / 1000, tz=UTC)
    else:
        seconds = d.get("time")
        if type(seconds) is not int or seconds <= 0:
            raise DemoSafetyError("broker deal time missing")
        when = datetime.fromtimestamp(seconds, tz=UTC)
    if when < _START or when > observed_utc:
        raise DemoSafetyError("broker deal timestamp outside history window")
    amount = sum(
        (_cash(d.get(field), field) for field in (
            "profit", "commission", "swap", "fee",
        )),
        Decimal(0),
    )
    magic = d.get("magic")
    if type(magic) is not int or magic < 0:
        raise DemoSafetyError("broker deal magic invalid")
    return CashDeal(
        deal_id=str(deal_id), time_utc=when, kind=kind,
        amount=amount, magic=magic,
    )


def read_mt5_pro_demo_cash(mt5: Any, *, now: datetime) -> CashObservation:
    """Use solely actual MT5 account and history values; never submit."""
    offset = now.utcoffset()
    if now.tzinfo is None or offset is None or offset.total_seconds() != 0:
        raise DemoSafetyError("exact UTC now required")
    terminal = _row(mt5.terminal_info(), "terminal")
    account = _row(mt5.account_info(), "account")
    if terminal.get("connected") is not True:
        raise DemoSafetyError("MT5 session disconnected")
    if type(account.get("trade_mode")) is not int or account["trade_mode"] != 0:
        raise DemoSafetyError("LIVE or unverified trade mode forbidden")
    if (
        account.get("company") != _EXPECTED_COMPANY
        or account.get("server") != _EXPECTED_SERVER
        or account.get("currency") != "USD"
    ):
        raise DemoSafetyError("wrong Exness server/currency")
    login = account.get("login")
    if type(login) is not int or login <= 0:
        raise DemoSafetyError("MT5 login missing")
    fingerprint = hashlib.sha256(
        f"{_EXPECTED_COMPANY}|{_EXPECTED_SERVER}|{login}|USD".encode()
    ).hexdigest()
    if fingerprint != _EXPECTED_SHA:
        raise DemoSafetyError("DEMO account fingerprint mismatch")

    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        raise DemoSafetyError("broker exposure query failed")

    raw_deals = mt5.history_deals_get(_START, now)
    if raw_deals is None:
        raise DemoSafetyError("broker historical cash source failed")
    deals = tuple(_deal_to_cash(mt5, x, now) for x in raw_deals)
    if not deals:
        raise DemoSafetyError("inception deposit not present in broker history")

    balance = _cash(account.get("balance"), "balance")
    equity = _cash(account.get("equity"), "equity")
    if balance <= 0 or equity <= 0:
        raise DemoSafetyError("nonpositive DEMO account capital")
    transaction_sum = sum((d.amount for d in deals), Decimal(0))
    if abs(transaction_sum - balance) > Decimal("0.02"):
        raise DemoSafetyError("broker history does not reconcile total account balance")
    return CashObservation(
        observed_utc=now,
        balance=balance,
        equity=equity,
        account_currency="USD",
        account_fingerprint=fingerprint,
        broker_history_complete=True,
        positions_count=len(tuple(positions)),
        orders_count=len(tuple(orders)),
        broker_deals=deals,
    )
