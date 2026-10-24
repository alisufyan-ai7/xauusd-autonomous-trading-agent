"""Broker-owned, durable break-even/trailing SL protection for known DEMO only.

This class never initiates an entry, creates or closes unknown positions,
changes lots, widens stops, or allows LIVE. Before modification it proves
the exact deal-backed owned position through the existing reconciliation
engine. Each modification is write-ahead journaled, sent once, and confirmed
against actual MT5 position SL/TP; ambiguity blocks future modifications.
The original fill receipt remains immutable in the coordinator.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Any

from .continuous_coordinator import QualifiedBrokerAck
from .envelope import DemoSafetyError
from .known_position_reconciliation import (
    KnownPositionBinding,
    observe_known_mt5_position,
)
from .mt5_demo import DemoMT5Adapter, _decimal, _record


@dataclass(frozen=True, slots=True)
class ProtectionResult:
    state: str
    action: str


class KnownDemoProtectionManager:
    def __init__(self, path: Path, *, adapter: DemoMT5Adapter) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS protection ("
            "position_id INTEGER PRIMARY KEY, account TEXT NOT NULL,"
            "initial_sl TEXT NOT NULL, original_tp TEXT NOT NULL,"
            "current_sl TEXT NOT NULL, next_sl TEXT,"
            "state TEXT NOT NULL, updated_utc TEXT NOT NULL)"
        )
        self._db.commit()
        self._adapter = adapter

    def __enter__(self) -> KnownDemoProtectionManager:
        return self

    def __exit__(self, *_: object) -> None:
        self._db.close()

    def _record(self, receipt: QualifiedBrokerAck, now: datetime) -> tuple:
        row = self._db.execute(
            "SELECT account,initial_sl,original_tp,current_sl,next_sl,state "
            "FROM protection WHERE position_id=?",
            (receipt.position_id,),
        ).fetchone()
        if row is None:
            self._db.execute(
                "INSERT INTO protection VALUES (?,?,?,?,?,?,?,?)",
                (
                    receipt.position_id, receipt.account_fingerprint,
                    str(receipt.stop_loss), str(receipt.take_profit),
                    str(receipt.stop_loss), None, "ACKNOWLEDGED",
                    now.isoformat(),
                ),
            )
            self._db.commit()
            row = (
                receipt.account_fingerprint, str(receipt.stop_loss),
                str(receipt.take_profit), str(receipt.stop_loss), None,
                "ACKNOWLEDGED",
            )
        if (
            row[0] != receipt.account_fingerprint
            or Decimal(row[1]) != receipt.stop_loss
            or Decimal(row[2]) != receipt.take_profit
        ):
            raise DemoSafetyError("protection receipt identity mismatch")
        return row

    def _write(
        self, receipt: QualifiedBrokerAck, state: str, now: datetime,
        *, current: Decimal, next_stop: Decimal | None,
    ) -> None:
        self._db.execute(
            "UPDATE protection SET current_sl=?,next_sl=?,state=?,updated_utc=? "
            "WHERE position_id=?",
            (
                str(current), str(next_stop) if next_stop is not None else None,
                state, now.isoformat(), receipt.position_id,
            ),
        )
        self._db.commit()

    @staticmethod
    def _quantize(price: Decimal, tick: Decimal, *, upwards: bool) -> Decimal:
        return (
            (price / tick).to_integral_value(
                rounding=ROUND_CEILING if upwards else ROUND_FLOOR
            ) * tick
        )

    def observe_and_manage(
        self, receipt: QualifiedBrokerAck, *, now: datetime,
    ) -> ProtectionResult:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("position manager requires UTC")
        receipt.validate(
            setup_key=receipt.setup_key,
            account_fingerprint=receipt.account_fingerprint, side=receipt.side,
        )
        adapter = self._adapter
        adapter._identity_guard(require_execution_enabled=True)
        mt5: Any = adapter._mt5
        if mt5 is None:
            raise DemoSafetyError("broker terminal not initialized")
        row = self._record(receipt, now)
        account, _, _, current_text, candidate_text, stage = row
        old_stop = Decimal(current_text)
        # A crash after an order_send may leave SENT_UNCERTAIN.
        # Only a proven changed broker SL is an admissible recovery.
        if stage not in ("ACKNOWLEDGED", "SENT_UNCERTAIN"):
            raise DemoSafetyError("prior protective modification unresolved")
        positions = mt5.positions_get()
        orders = mt5.orders_get()
        if positions is None or orders is None or len(tuple(orders)) != 0:
            raise DemoSafetyError("position observation unavailable or foreign order")
        positions = tuple(positions)
        pos = _record(positions[0], "known position") if len(positions) == 1 else None
        effective_stop = old_stop
        if stage == "SENT_UNCERTAIN":
            if candidate_text is None or pos is None:
                raise DemoSafetyError("unresolved protective modification")
            proposed = Decimal(candidate_text)
            if _decimal(pos.get("sl"), "broker stop") != proposed:
                raise DemoSafetyError("broker modification ambiguous; no retry")
            effective_stop = proposed
            self._write(
                receipt, "ACKNOWLEDGED", now,
                current=proposed, next_stop=None,
            )
        binding = KnownPositionBinding(
            position_id=receipt.position_id, entry_order=receipt.order_ticket,
            entry_deal=receipt.entry_deal_ticket,
            account_fingerprint=account, side=receipt.side,
            volume=receipt.volume_lots, protective_sl=effective_stop,
            protective_tp=receipt.take_profit, tick_size=receipt.tick_size,
        )
        state = observe_known_mt5_position(mt5, binding=binding, now=now)
        if state != "OPEN":
            return ProtectionResult(state, "BROKER_POSITION_NOT_OPEN")
        if pos is None:
            raise DemoSafetyError("position OPEN without unique broker position")
        if (
            pos.get("identifier") != receipt.position_id
            or pos.get("symbol") != "XAUUSD"
            or pos.get("magic") != 260101
            or type(pos.get("ticket")) is not int
        ):
            raise DemoSafetyError("SLTP target not the known position ticket")
        quote = _record(mt5.symbol_info_tick("XAUUSD"), "management quote")
        info = _record(mt5.symbol_info("XAUUSD"), "symbol")
        msc = quote.get("time_msc")
        if type(msc) is not int or msc <= 0:
            raise DemoSafetyError("missing management quote timestamp")
        tick_at = datetime.fromtimestamp(msc / 1000, UTC)
        if tick_at > now + timedelta(seconds=1) or now-tick_at > timedelta(seconds=2):
            return ProtectionResult("OPEN", "QUOTE_NOT_FRESH")
        bid = _decimal(quote.get("bid"), "bid")
        ask = _decimal(quote.get("ask"), "ask")
        tick = receipt.tick_size
        if bid <= 0 or ask <= bid:
            raise DemoSafetyError("invalid management bid or ask")
        risk = (
            receipt.entry_price - receipt.stop_loss if receipt.side == "BUY"
            else receipt.stop_loss - receipt.entry_price
        )
        if risk <= 0:
            raise DemoSafetyError("original broker stop risk invalid")
        favorable = (
            bid - receipt.entry_price if receipt.side == "BUY"
            else receipt.entry_price - ask
        )
        if favorable < risk * Decimal("1.2"):
            return ProtectionResult("OPEN", "WAIT_BREAKEVEN_THRESHOLD")
        point = _decimal(info.get("point"), "point")
        stops = max(
            int(info.get("trade_stops_level") or 0),
            int(info.get("trade_freeze_level") or 0),
            3,
        )
        min_distance = point * Decimal(stops + 2)
        spread_reserve = max((ask-bid)*Decimal(2), tick*Decimal(2))
        if receipt.side == "BUY":
            proposed = self._quantize(
                receipt.entry_price + spread_reserve,
                tick, upwards=True,
            )
            if favorable >= risk * Decimal("2"):
                proposed = max(
                    proposed,
                    self._quantize(
                        bid-risk*Decimal("0.7"), tick, upwards=False,
                    ),
                )
            eligible = old_stop + tick <= proposed < bid-min_distance
        else:
            proposed = self._quantize(
                receipt.entry_price - spread_reserve,
                tick, upwards=False,
            )
            if favorable >= risk * Decimal("2"):
                proposed = min(
                    proposed,
                    self._quantize(
                        ask+risk*Decimal("0.7"), tick, upwards=True,
                    ),
                )
            eligible = ask+min_distance < proposed <= old_stop-tick
        if not eligible:
            return ProtectionResult("OPEN", "NO_SAFE_SL_TIGHTENING")
        # Persist UNKNOWN before any broker write. No blind retry after crash.
        self._write(
            receipt, "SENT_UNCERTAIN", now,
            current=old_stop, next_stop=proposed,
        )
        payload = {
            "action": mt5.TRADE_ACTION_SLTP, "symbol": "XAUUSD",
            "position": pos["ticket"], "sl": float(proposed),
            "tp": float(receipt.take_profit), "magic": 260101,
        }
        try:
            check = _record(mt5.order_check(payload), "SLTP check")
            if int(check.get("retcode", -1)) != 0:
                # Broker check denied before sending; restore known old stop.
                self._write(
                    receipt, "ACKNOWLEDGED", now,
                    current=old_stop, next_stop=None,
                )
                return ProtectionResult("OPEN", "BROKER_SLTP_CHECK_DENIED")
            result = _record(mt5.order_send(payload), "SLTP result")
            if result.get("retcode") != mt5.TRADE_RETCODE_DONE:
                raise DemoSafetyError("uncertain SLTP modification")
            after = mt5.positions_get()
            if after is None or len(tuple(after)) != 1:
                raise DemoSafetyError("SLTP broker acknowledgment not reconciled")
            observed = _record(tuple(after)[0], "post-SLTP position")
            if (
                observed.get("identifier") != receipt.position_id
                or _decimal(observed.get("sl"), "modified SL") != proposed
                or _decimal(observed.get("tp"), "modified TP")
                != receipt.take_profit
            ):
                raise DemoSafetyError("SLTP outcome not confirmed")
        except Exception as exc:
            # Leave SENT_UNCERTAIN in durable DB; broker may have acted.
            raise DemoSafetyError("broker SLTP uncertain; freeze management") from exc
        self._write(
            receipt, "ACKNOWLEDGED", now,
            current=proposed, next_stop=None,
        )
        return ProtectionResult("OPEN", "BROKER_STOP_TIGHTENED")
