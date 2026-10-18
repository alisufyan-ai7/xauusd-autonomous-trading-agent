"""Strict read-only port decorator durably captures partial poll/tick evidence.

No MT5 import, no trading capability. Every actual polled quote is written and
fsynced BEFORE returned to the already-frozen v1.1 core. True-tick range batches
are journaled with source order and flags before returned. Full data may be
large; if a write blocks or fails it ABORTS capture rather than skipping slots.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from scripts.v12_attempt_journal import AttemptJournal


def _mapping(record: Any, label: str) -> dict[str, Any]:
    if hasattr(record, "_asdict"):
        record = record._asdict()
    if type(record) is not dict:
        raise ValueError(label + ": unavailable broker data")
    return record


class JournaledReadOnlyPort:
    def __init__(self, port: Any, journal: AttemptJournal) -> None:
        self._port = port
        self._journal = journal
        self._poll_index = 0
        self._chunk_index = 0

    def terminal_info(self) -> Any:
        value = self._port.terminal_info()
        info = _mapping(value, "terminal_info")
        self._journal.append("TERMINAL_READ", {
            "connected": info.get("connected") is True,
            "external_python_trading_disabled": info.get("tradeapi_disabled") is True,
        })
        return value

    def account_info(self) -> Any:
        value = self._port.account_info()
        self._journal.append("ACCOUNT_READ", {"present": value is not None})
        return value

    def positions_get(self) -> Any:
        value = self._port.positions_get()
        self._journal.append("POSITIONS_READ", {
            "count": None if value is None else len(value)
        })
        return value

    def orders_get(self) -> Any:
        value = self._port.orders_get()
        self._journal.append("ORDERS_READ", {
            "count": None if value is None else len(value)
        })
        return value

    def symbol_info(self, symbol: str) -> Any:
        if symbol != "XAUUSD":
            raise ValueError("only admitted XAUUSD read allowed")
        value = self._port.symbol_info(symbol)
        self._journal.append("SYMBOL_READ", {"name": symbol, "present": value is not None})
        return value

    def symbol_info_tick(self, symbol: str) -> Any:
        if symbol != "XAUUSD":
            raise ValueError("only admitted XAUUSD quote allowed")
        tick = self._port.symbol_info_tick(symbol)
        if tick is not None:
            entry = _mapping(tick, "symbol_info_tick")
            self._journal.append("POLL_QUOTE", {
                "ordinal": self._poll_index,
                "source_time_msc": int(entry["time_msc"]),
                "bid": str(entry["bid"]),
                "ask": str(entry["ask"]),
            })
            self._poll_index += 1
        else:
            self._journal.append("POLL_MISSING", {"ordinal": self._poll_index})
        return tick

    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> Any:
        if symbol != "XAUUSD":
            raise ValueError("only admitted XAUUSD tick range allowed")
        rows = self._port.copy_ticks_range(symbol, start, end, flags)
        if rows is None:
            self._journal.append("TRUE_TICK_RANGE_FAILED", {
                "ordinal": self._chunk_index,
                "start_utc": start.isoformat(),
                "end_utc": end.isoformat(),
            })
            return None
        durable = []
        for ordinal, row in enumerate(rows):
            parsed = _mapping(row, "true_tick")
            durable.append({
                "ordinal": ordinal,
                "time_msc": int(parsed["time_msc"]),
                "time": int(parsed["time"]),
                "bid": str(parsed["bid"]),
                "ask": str(parsed["ask"]),
                "flags": int(parsed["flags"]),
            })
        self._journal.append("TRUE_TICK_RANGE", {
            "chunk_ordinal": self._chunk_index,
            "start_utc": start.isoformat(),
            "end_utc": end.isoformat(),
            "raw_records": durable,
        })
        self._chunk_index += 1
        return rows
