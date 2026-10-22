"""Account-bound read-only MT5 reconciliation for one known DEMO position.

This is a component of the future QualifiedDemoBrokerPort, NOT a broker order
sender or an execution permit. In particular, a missing position is never
enough to declare CLOSED: the exact position_id's entry AND final exit deals
must reconcile. MetaQuotes documents history_deals_get(position=...) as a
DEAL_POSITION_ID filter, not an order-ticket filter.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from .continuous_coordinator import QualifiedBrokerAck
from .envelope import DemoSafetyError
from .mt5_demo import _decimal, _record

KNOWN_MAGIC = 260101
EXPECTED_COMPANY = "Exness Technologies Ltd"
EXPECTED_SERVER = "Exness-MT5Trial15"
KnownState = Literal["OPEN", "CLOSED", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class KnownPositionBinding:
    """Persist this receipt DURABLY at ACK, not only in volatile RAM.

    position_id is POSITION_IDENTIFIER / DEAL_POSITION_ID, which must not
    be confused with the order/deal ticket returned by order_send.
    """
    position_id: int
    entry_order: int
    entry_deal: int
    account_fingerprint: str
    side: str
    volume: Decimal
    protective_sl: Decimal
    protective_tp: Decimal
    tick_size: Decimal

    def __post_init__(self) -> None:
        if (
            type(self.position_id) is not int or self.position_id <= 0
            or type(self.entry_order) is not int or self.entry_order <= 0
            or type(self.entry_deal) is not int or self.entry_deal <= 0
            or len(self.account_fingerprint) != 64
            or any(c not in "0123456789abcdef" for c in self.account_fingerprint)
            or self.side not in ("BUY", "SELL")
            or any(
                type(x) is not Decimal or not x.is_finite() or x <= 0
                for x in (
                    self.volume, self.protective_sl, self.protective_tp,
                    self.tick_size,
                )
            )
            or self.volume != Decimal("0.01")
        ):
            raise DemoSafetyError("incomplete immutable known-position binding")


def _match_price(value: Any, expected: Decimal, tick: Decimal) -> bool:
    try:
        got = _decimal(value, "position protective level")
    except DemoSafetyError:
        return False
    return got > 0 and abs(got - expected) <= tick / 2


def observe_known_mt5_position(
    mt5: Any, *, binding: KnownPositionBinding, now: datetime
) -> KnownState:
    """Read MT5 only. Unknown evidence returns UNKNOWN; wrong account raises.

    The caller must have already initialized the exact admitted terminal.
    This observer does NOT call order_check, order_send, symbol_select, login,
    initialize or shutdown. It is deliberately conservative about broker
    adjustments, partial/opening fills, reversing, foreign exposure, and
    incomplete history.
    """
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise DemoSafetyError("known-position observation needs UTC time")
    terminal = _record(mt5.terminal_info(), "terminal_info")
    account = _record(mt5.account_info(), "account_info")
    if terminal.get("connected") is not True:
        return "UNKNOWN"
    if (
        type(account.get("trade_mode")) is not int
        or account["trade_mode"] != 0
        or account.get("company") != EXPECTED_COMPANY
        or account.get("server") != EXPECTED_SERVER
        or account.get("currency") != "USD"
        or type(account.get("login")) is not int
        or account["login"] <= 0
    ):
        raise DemoSafetyError("wrong or LIVE account in position reconciliation")
    fingerprint = hashlib.sha256(
        f"{EXPECTED_COMPANY}|{EXPECTED_SERVER}|{account['login']}|USD".encode()
    ).hexdigest()
    if fingerprint != binding.account_fingerprint:
        raise DemoSafetyError("known-position account fingerprint changed")

    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        return "UNKNOWN"
    positions_list, orders_list = tuple(positions), tuple(orders)
    if orders_list or len(positions_list) > 1:
        return "UNKNOWN"
    if positions_list:
        try:
            position = _record(positions_list[0], "position")
            if (
                position.get("symbol") != "XAUUSD"
                or position.get("identifier") != binding.position_id
                or position.get("magic") != KNOWN_MAGIC
                or position.get("type") != getattr(
                    mt5, "POSITION_TYPE_BUY" if binding.side == "BUY"
                    else "POSITION_TYPE_SELL", None
                )
                or not _match_price(
                    position.get("sl"), binding.protective_sl, binding.tick_size
                )
                or not _match_price(
                    position.get("tp"), binding.protective_tp, binding.tick_size
                )
            ):
                return "UNKNOWN"
        except DemoSafetyError:
            return "UNKNOWN"

    # position= is the exact MetaQuotes DEAL_POSITION_ID filter.
    raw = mt5.history_deals_get(position=binding.position_id)
    if raw is None:
        return "UNKNOWN"
    rows: list[dict[str, Any]] = []
    for item in raw:
        try:
            row = _record(item, "position deal")
        except DemoSafetyError:
            return "UNKNOWN"
        if (
            row.get("position_id") != binding.position_id
            or row.get("symbol") != "XAUUSD"
            or type(row.get("ticket")) is not int
            or row["ticket"] <= 0
            or type(row.get("order")) is not int
            or row["order"] <= 0
            or type(row.get("time_msc")) is not int
            or row["time_msc"] <= 0
            or datetime.fromtimestamp(row["time_msc"] / 1000, UTC) > now
        ):
            return "UNKNOWN"
        rows.append(row)
    if len({r["ticket"] for r in rows}) != len(rows):
        return "UNKNOWN"

    entry_code = getattr(mt5, "DEAL_ENTRY_IN", None)
    exit_code = getattr(mt5, "DEAL_ENTRY_OUT", None)
    buy_code = getattr(mt5, "DEAL_TYPE_BUY", None)
    sell_code = getattr(mt5, "DEAL_TYPE_SELL", None)
    if None in (entry_code, exit_code, buy_code, sell_code):
        return "UNKNOWN"
    own_type = buy_code if binding.side == "BUY" else sell_code
    other_type = sell_code if binding.side == "BUY" else buy_code
    entries = [d for d in rows if d.get("entry") == entry_code]
    if len(entries) != 1:
        return "UNKNOWN"
    original = entries[0]
    if (
        original.get("ticket") != binding.entry_deal
        or original.get("order") != binding.entry_order
        or original.get("type") != own_type
        or original.get("magic") != KNOWN_MAGIC
    ):
        return "UNKNOWN"
    try:
        original_volume = _decimal(original.get("volume"), "opening volume")
    except DemoSafetyError:
        return "UNKNOWN"
    if original_volume != binding.volume:
        return "UNKNOWN"

    closed = Decimal(0)
    for d in rows:
        if d is original:
            continue
        if d.get("entry") != exit_code or d.get("type") != other_type:
            return "UNKNOWN"
        # Broker-initiated SL/TP exits may have magic 0; exact position ID,
        # symbol, exit direction and volume still must reconcile.
        if d.get("magic") not in (0, KNOWN_MAGIC):
            return "UNKNOWN"
        try:
            portion = _decimal(d.get("volume"), "closing volume")
        except DemoSafetyError:
            return "UNKNOWN"
        if portion <= 0:
            return "UNKNOWN"
        closed += portion
    if closed > binding.volume:
        return "UNKNOWN"
    remaining = binding.volume - closed
    if positions_list:
        try:
            active_volume = _decimal(
                _record(positions_list[0], "position").get("volume"),
                "position volume"
            )
        except DemoSafetyError:
            return "UNKNOWN"
        return "OPEN" if remaining > 0 and active_volume == remaining else "UNKNOWN"
    # Exact opening and closing broker deals plus flat account: never infer a
    # closure just from a missing position or an order_send DONE retcode.
    return "CLOSED" if closed > 0 and remaining == 0 else "UNKNOWN"


class KnownMT5PositionPort:
    """Read-only implementation of coordinator's known_position_state method.

    The full future broker port must durably persist a matching binding
    BEFORE reporting ACK; reconstructing it from only an order ticket is
    prohibited. This class implements no submission method.
    """

    def __init__(self, mt5: Any, *, binding: KnownPositionBinding) -> None:
        self.mt5 = mt5
        self.binding = binding

    def known_position_state(
        self, receipt: QualifiedBrokerAck, now: datetime
    ) -> KnownState:
        # The durable coordinator ACK must correspond to this exact
        # account/entry/position binding; no ticket-only promotion.
        if (
            receipt.position_id != self.binding.position_id
            or receipt.order_ticket != self.binding.entry_order
            or receipt.entry_deal_ticket != self.binding.entry_deal
            or receipt.account_fingerprint != self.binding.account_fingerprint
            or receipt.side != self.binding.side
            or receipt.volume_lots != self.binding.volume
            or receipt.stop_loss != self.binding.protective_sl
            or receipt.take_profit != self.binding.protective_tp
            or receipt.tick_size != self.binding.tick_size
        ):
            return "UNKNOWN"
        return observe_known_mt5_position(
            self.mt5, binding=self.binding, now=now
        )
