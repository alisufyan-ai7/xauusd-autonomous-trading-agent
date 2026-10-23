"""Read-only Exness DEMO pending STOP -> fill/expiry reconciliation.

MetaQuotes order ticket selects history_orders_get(ticket=) AND
history_deals_get(ticket=), whereas filled exposure is identified by the
DEAL_POSITION_ID/position.identifier. Never infer fill from order retcode.
The attached MT5 terminal must already be initialized by the caller.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

from .continuous_coordinator import (
    PendingBrokerAck, PendingOrderObservation, QualifiedBrokerAck,
)
from .envelope import DemoSafetyError
from .known_position_reconciliation import (
    EXPECTED_COMPANY, EXPECTED_SERVER, KNOWN_MAGIC,
)
from .mt5_demo import _decimal, _record


class ReadOnlyPendingMT5Port:
    """QualifiedDemoBrokerPort's pending observation method ONLY."""

    def __init__(self, mt5: Any) -> None:
        self.mt5 = mt5

    def known_pending_state(
        self, receipt: PendingBrokerAck, now: datetime
    ) -> PendingOrderObservation:
        def unknown() -> PendingOrderObservation:
            return PendingOrderObservation("UNKNOWN")

        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("pending MT5 observation requires exact UTC")
        mt5 = self.mt5
        terminal = _record(mt5.terminal_info(), "terminal")
        account = _record(mt5.account_info(), "account")
        if terminal.get("connected") is not True:
            return unknown()
        if (
            type(account.get("trade_mode")) is not int
            or account["trade_mode"] != 0
            or account.get("company") != EXPECTED_COMPANY
            or account.get("server") != EXPECTED_SERVER
            or account.get("currency") != "USD"
            or type(account.get("login")) is not int
        ):
            raise DemoSafetyError("wrong / LIVE MT5 pending-order account")
        fingerprint = hashlib.sha256(
            f"{EXPECTED_COMPANY}|{EXPECTED_SERVER}|{account['login']}|USD".encode()
        ).hexdigest()
        receipt.validate(
            setup_key=receipt.setup_key, side=receipt.side,
            account_fingerprint=fingerprint,
        )
        orders = mt5.orders_get()
        positions = mt5.positions_get()
        if orders is None or positions is None:
            return unknown()
        order_rows, position_rows = tuple(orders), tuple(positions)
        if len(order_rows) > 1 or len(position_rows) > 1:
            return unknown()
        expected_type = (
            getattr(mt5, "ORDER_TYPE_BUY_STOP", None)
            if receipt.side == "BUY" else
            getattr(mt5, "ORDER_TYPE_SELL_STOP", None)
        )
        if expected_type is None:
            return unknown()

        def order_matches(row: dict[str, Any]) -> bool:
            try:
                return (
                    row.get("ticket") == receipt.order_ticket
                    and row.get("symbol") == "XAUUSD"
                    and row.get("magic") == KNOWN_MAGIC
                    and row.get("type") == expected_type
                    and _decimal(row.get("volume_initial"), "order volume")
                    == receipt.volume_lots
                    and _decimal(row.get("price_open"), "order price")
                    == receipt.entry_stop
                    and _decimal(row.get("sl"), "order stop") == receipt.stop_loss
                    and _decimal(row.get("tp"), "order TP") == receipt.take_profit
                    and row.get("time_expiration")
                    == int(receipt.expires_utc.timestamp())
                )
            except DemoSafetyError:
                return False

        if order_rows:
            if position_rows:
                return unknown()
            try:
                order = _record(order_rows[0], "pending order")
            except DemoSafetyError:
                return unknown()
            if not order_matches(order):
                return unknown()
            if order.get("state") != getattr(mt5, "ORDER_STATE_PLACED", None):
                return unknown()
            return PendingOrderObservation(
                "PENDING" if now < receipt.expires_utc else "UNKNOWN"
            )

        history = mt5.history_orders_get(ticket=receipt.order_ticket)
        deals = mt5.history_deals_get(ticket=receipt.order_ticket)
        if history is None or deals is None or len(tuple(history)) != 1:
            return unknown()
        try:
            historic = _record(tuple(history)[0], "historical pending order")
        except DemoSafetyError:
            return unknown()
        if not order_matches(historic):
            return unknown()
        deal_rows = tuple(deals)
        if (
            historic.get("state") in (
                getattr(mt5, "ORDER_STATE_EXPIRED", None),
                getattr(mt5, "ORDER_STATE_CANCELED", None),
            )
            and not deal_rows and not position_rows
        ):
            # Current broker order table flat + historical terminal expired or
            # cancelled + exact order-filtered deals empty. No manual replay.
            return PendingOrderObservation("EXPIRED")
        if historic.get("state") != getattr(mt5, "ORDER_STATE_FILLED", None):
            return unknown()
        if len(deal_rows) != 1 or len(position_rows) != 1:
            # Partial fill, no open position (already closed), foreign exposure
            # or missing broker history always requires human reconciliation.
            return unknown()
        try:
            deal = _record(deal_rows[0], "broker fill deal")
            position = _record(position_rows[0], "broker filled position")
            direction = (
                mt5.DEAL_TYPE_BUY if receipt.side == "BUY"
                else mt5.DEAL_TYPE_SELL
            )
            if (
                deal.get("order") != receipt.order_ticket
                or deal.get("symbol") != "XAUUSD"
                or deal.get("entry") != mt5.DEAL_ENTRY_IN
                or deal.get("magic") != KNOWN_MAGIC
                or deal.get("type") != direction
                or type(deal.get("ticket")) is not int
                or type(deal.get("position_id")) is not int
                or not deal["ticket"] > 0 or not deal["position_id"] > 0
                or _decimal(deal.get("volume"), "fill volume") != receipt.volume_lots
                or position.get("identifier") != deal["position_id"]
                or position.get("symbol") != "XAUUSD"
                or position.get("magic") != KNOWN_MAGIC
                or position.get("type") != (
                    mt5.POSITION_TYPE_BUY if receipt.side == "BUY"
                    else mt5.POSITION_TYPE_SELL
                )
                or _decimal(position.get("volume"), "position volume")
                != receipt.volume_lots
                or _decimal(position.get("sl"), "position SL") != receipt.stop_loss
                or _decimal(position.get("tp"), "position TP") != receipt.take_profit
            ):
                return unknown()
            entry = _decimal(deal.get("price"), "actual fill price")
            if entry <= 0:
                return unknown()
            # Original admitted economics bound entry drift separately.
            if (
                (receipt.side == "BUY" and not (
                    receipt.stop_loss < entry < receipt.take_profit
                ))
                or (receipt.side == "SELL" and not (
                    receipt.take_profit < entry < receipt.stop_loss
                ))
            ):
                return unknown()
            symbol = _record(mt5.symbol_info("XAUUSD"), "symbol")
            tick_size = _decimal(symbol.get("trade_tick_size"), "tick size")
            if tick_size <= 0:
                return unknown()
            fill = QualifiedBrokerAck(
                setup_key=receipt.setup_key,
                account_fingerprint=fingerprint,
                position_id=deal["position_id"],
                order_ticket=receipt.order_ticket,
                entry_deal_ticket=deal["ticket"],
                side=receipt.side,
                volume_lots=receipt.volume_lots,
                entry_price=entry,
                stop_loss=receipt.stop_loss,
                take_profit=receipt.take_profit,
                tick_size=tick_size,
            )
            fill.validate(
                setup_key=receipt.setup_key,
                side=receipt.side, account_fingerprint=fingerprint,
            )
            return PendingOrderObservation("FILLED", fill)
        except (AttributeError, DemoSafetyError, TypeError, ValueError):
            return unknown()
