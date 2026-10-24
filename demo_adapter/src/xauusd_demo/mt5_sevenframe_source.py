"""Exact DEMO-terminal XAUUSD seven-timeframe completed-bar market source.

Reads from the SAME already initialized MT5 instance as the one S2 sender.
MT5 copy_rates_from_pos start_pos=1 excludes the *forming* zero-index bar.
No orders, login, symbol selection, terminal setting changes or network calls.

Official MetaQuotes reference:
https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from operator import index
from typing import Any

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe
from xauusd_agent.market.models import Quote

from .envelope import DemoSafetyError
from .mt5_demo import _decimal, _record

_COUNTS: dict[ContextTimeframe, int] = {
    ContextTimeframe.W1: 110,
    ContextTimeframe.D1: 370,
    ContextTimeframe.H4: 350,
    ContextTimeframe.H1: 600,
    ContextTimeframe.M15: 1100,
    ContextTimeframe.M5: 240,
    ContextTimeframe.M1: 240,
}


@dataclass(frozen=True, slots=True)
class SevenFrameObservation:
    observed_utc: datetime
    bars: dict[ContextTimeframe, tuple[ContextBar, ...]]
    quote: Quote
    broker_spread: Decimal
    tick_size: Decimal
    complete_m15_close_utc: datetime


def _utc(seconds: Any, label: str) -> datetime:
    if type(seconds) is not int or seconds <= 0:
        raise DemoSafetyError(f"{label} UTC seconds invalid")
    try:
        return datetime.fromtimestamp(seconds, UTC)
    except (ValueError, OSError, OverflowError) as exc:
        raise DemoSafetyError(f"{label} UTC timestamp invalid") from exc


class ReadOnlyMT5SevenFrameSource:
    """Capture immutable broker-supplied completed bars, never trade or infer."""

    def __init__(self, mt5: Any) -> None:
        self._mt5 = mt5

    def latest_m15_close(self, *, now: datetime) -> datetime | None:
        """Cheap 1-bar probe; call full seven-frame capture only on new bar."""
        mt5 = self._mt5
        code = getattr(mt5, "TIMEFRAME_M15", None)
        if code is None:
            return None
        rows = mt5.copy_rates_from_pos("XAUUSD", code, 1, 1)
        if rows is None or len(rows) != 1:
            return None
        try:
            latest = _utc(index(rows[0]["time"]), "latest M15 bar")
        except (TypeError, KeyError, ValueError, OverflowError):
            return None
        close = latest + timedelta(minutes=15)
        return close if close <= now else None

    def capture(self, *, now: datetime) -> SevenFrameObservation:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise DemoSafetyError("seven-frame capture requires exact UTC")
        broker = self._mt5
        account = _record(broker.account_info(), "account")
        terminal = _record(broker.terminal_info(), "terminal")
        if (
            terminal.get("connected") is not True
            or account.get("trade_mode") != 0
            or account.get("company") != "Exness Technologies Ltd"
            or account.get("server") != "Exness-MT5Trial15"
            or account.get("currency") != "USD"
        ):
            raise DemoSafetyError("seven-frame source not connected to pinned DEMO")
        symbol = _record(broker.symbol_info("XAUUSD"), "XAUUSD symbol")
        tick_size = _decimal(symbol.get("trade_tick_size"), "tick size")
        if tick_size <= 0:
            raise DemoSafetyError("tick size invalid")
        tick = _record(broker.symbol_info_tick("XAUUSD"), "XAUUSD tick")
        bid = _decimal(tick.get("bid"), "bid")
        ask = _decimal(tick.get("ask"), "ask")
        tick_msc = tick.get("time_msc")
        if type(tick_msc) is not int or tick_msc <= 0:
            raise DemoSafetyError("broker tick milliseconds missing")
        broker_utc = datetime.fromtimestamp(tick_msc / 1000, UTC)
        if (
            bid <= 0 or ask <= bid
            or bid % tick_size or ask % tick_size
            or broker_utc > now + timedelta(seconds=1)
            or now - broker_utc > timedelta(seconds=5)
        ):
            raise DemoSafetyError("broker quote stale, off grid or crossed")
        quote = Quote(
            symbol="XAUUSD", broker_time=broker_utc,
            received_time=now, bid=bid, ask=ask, tick_size=tick_size,
            sequence=tick_msc,
        )
        output: dict[ContextTimeframe, tuple[ContextBar, ...]] = {}
        for name, count in _COUNTS.items():
            timeframe_code = getattr(broker, f"TIMEFRAME_{name.value}", None)
            if timeframe_code is None:
                raise DemoSafetyError(f"MT5 {name.value} timeframe absent")
            raw = broker.copy_rates_from_pos("XAUUSD", timeframe_code, 1, count)
            if raw is None or len(raw) < count:
                raise DemoSafetyError(f"{name.value} historic closed bars short")
            ordered = []
            for row in raw:
                try:
                    epoch = row["time"]
                    stamp = _utc(index(epoch), "bar")
                    values = {
                        field: _decimal(row[field], field)
                        for field in ("open", "high", "low", "close")
                    }
                    vol = int(row["tick_volume"])
                    if isinstance(epoch, bool) or vol < 0:
                        raise DemoSafetyError("invalid broker bar schema")
                    bar = ContextBar(
                        timeframe=name, open_time=stamp, tick_volume=vol,
                        **values,
                    )
                    if bar.close_time > now:
                        raise DemoSafetyError("MT5 supplied incomplete bar")
                    ordered.append(bar)
                except (TypeError, KeyError, ValueError, OverflowError) as exc:
                    raise DemoSafetyError(f"{name.value} source malformed") from exc
            ordered.sort(key=lambda bar: bar.open_time)
            if len({bar.open_time for bar in ordered}) != len(ordered):
                raise DemoSafetyError(f"{name.value} duplicated completed bar")
            if any(a.open_time >= b.open_time for a, b in zip(ordered, ordered[1:], strict=False)):
                raise DemoSafetyError(f"{name.value} bar timestamp ordering invalid")
            output[name] = tuple(ordered)
        m15 = output[ContextTimeframe.M15][-1].close_time
        return SevenFrameObservation(
            observed_utc=now, bars=output, quote=quote,
            broker_spread=quote.spread, tick_size=tick_size,
            complete_m15_close_utc=m15,
        )
