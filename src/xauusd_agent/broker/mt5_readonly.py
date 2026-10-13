"""Read-only MetaTrader 5 adapter used by the execution-disabled PCR-3 host.

The adapter intentionally exposes observation methods only. Every observation
rechecks the MT5 terminal guard that disables automated trading via the
external Python API. If that guard is absent or the terminal disconnects, the
adapter fails closed before returning broker or market data.
"""

from __future__ import annotations

import hashlib
import importlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from xauusd_agent.market import Bar, Quote, Timeframe

from .observation import (
    AccountFingerprint,
    AccountObservation,
    BuildFingerprint,
    OrderObservation,
    PositionObservation,
    SymbolFingerprint,
)


class MT5ReadOnlyError(RuntimeError):
    """Raised when MT5 cannot satisfy the read-only execution-disabled contract."""


def _record(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        raise MT5ReadOnlyError(f"{label} returned no data")
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    raise MT5ReadOnlyError(f"{label} returned an unsupported record type")


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise MT5ReadOnlyError(f"{field} is not a decimal value") from exc
    if not result.is_finite():
        raise MT5ReadOnlyError(f"{field} is not finite")
    return result


def _utc_from_epoch(value: Any, *, milliseconds: bool = False) -> datetime:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise MT5ReadOnlyError("MT5 timestamp is invalid") from exc
    if milliseconds:
        number /= 1000.0
    return datetime.fromtimestamp(number, tz=UTC)


class MT5ReadOnlyAdapter:
    """Read-only broker and market adapter with a guard check on every call."""

    def __init__(self, module: Any | None = None) -> None:
        self._mt5 = module
        self._initialized = False

    def initialize(self) -> None:
        if self._mt5 is None:
            try:
                self._mt5 = importlib.import_module("MetaTrader5")
            except ImportError as exc:
                raise MT5ReadOnlyError("MetaTrader5 package is unavailable") from exc
        if not bool(self._mt5.initialize()):
            raise MT5ReadOnlyError(f"MT5 initialize failed: {self._mt5.last_error()}")
        self._initialized = True
        try:
            self._guard()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._initialized and self._mt5 is not None:
            self._mt5.shutdown()
        self._initialized = False

    def __enter__(self) -> "MT5ReadOnlyAdapter":
        self.initialize()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _guard(self) -> dict[str, Any]:
        if not self._initialized or self._mt5 is None:
            raise MT5ReadOnlyError("MT5 adapter is not initialized")
        terminal = _record(self._mt5.terminal_info(), "terminal_info")
        if terminal.get("tradeapi_disabled") is not True:
            raise MT5ReadOnlyError("MT5 external-Python trading protection is not enabled")
        if terminal.get("connected") is not True:
            raise MT5ReadOnlyError("MT5 terminal is not connected")
        return terminal

    def _account(self) -> dict[str, Any]:
        self._guard()
        assert self._mt5 is not None
        return _record(self._mt5.account_info(), "account_info")

    def observe_account(self) -> AccountObservation:
        account = self._account()
        server = str(account.get("server") or "")
        broker = str(account.get("company") or "")
        currency = str(account.get("currency") or "")
        login = str(account.get("login") or "")
        fingerprint = hashlib.sha256(
            f"{broker}|{server}|{login}|{currency}".encode("utf-8")
        ).hexdigest()
        return AccountObservation(
            observed_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            connected=True,
            trading_api_disabled=True,
            equity=_decimal(account.get("equity"), "account equity"),
            free_margin=_decimal(account.get("margin_free"), "account free margin"),
            margin_used=_decimal(account.get("margin"), "account margin"),
            fingerprint=AccountFingerprint(
                broker=broker,
                server=server,
                account_id_sha256=fingerprint,
                currency=currency,
                leverage=int(account.get("leverage") or 0),
                account_mode=str(account.get("trade_mode") or ""),
            ),
        )

    def observe_symbol_fingerprint(self, symbol: str) -> SymbolFingerprint:
        if symbol != "XAUUSD":
            raise MT5ReadOnlyError("production candidate is bound to XAUUSD")
        self._guard()
        assert self._mt5 is not None
        info = _record(self._mt5.symbol_info(symbol), "symbol_info")
        return SymbolFingerprint(
            symbol=symbol,
            path=str(info.get("path") or ""),
            digits=int(info.get("digits") or 0),
            point=_decimal(info.get("point"), "symbol point"),
            contract_size=_decimal(info.get("trade_contract_size"), "contract size"),
            volume_min=_decimal(info.get("volume_min"), "volume_min"),
            volume_max=_decimal(info.get("volume_max"), "volume_max"),
            volume_step=_decimal(info.get("volume_step"), "volume_step"),
        )

    def observe_build_fingerprint(self) -> BuildFingerprint:
        terminal = self._guard()
        assert self._mt5 is not None
        return BuildFingerprint(
            terminal_name=str(terminal.get("name") or ""),
            terminal_company=str(terminal.get("company") or ""),
            terminal_build=int(terminal.get("build") or 0),
            python_bridge_version=str(getattr(self._mt5, "__version__", "")),
        )

    def _position_side(self, value: Any) -> str:
        assert self._mt5 is not None
        buy = int(getattr(self._mt5, "POSITION_TYPE_BUY", 0))
        sell = int(getattr(self._mt5, "POSITION_TYPE_SELL", 1))
        if int(value) == buy:
            return "BUY"
        if int(value) == sell:
            return "SELL"
        raise MT5ReadOnlyError("unsupported MT5 position side")

    def _order_side(self, value: Any) -> str:
        assert self._mt5 is not None
        buy_types = {
            int(getattr(self._mt5, name))
            for name in (
                "ORDER_TYPE_BUY",
                "ORDER_TYPE_BUY_LIMIT",
                "ORDER_TYPE_BUY_STOP",
                "ORDER_TYPE_BUY_STOP_LIMIT",
            )
            if hasattr(self._mt5, name)
        }
        sell_types = {
            int(getattr(self._mt5, name))
            for name in (
                "ORDER_TYPE_SELL",
                "ORDER_TYPE_SELL_LIMIT",
                "ORDER_TYPE_SELL_STOP",
                "ORDER_TYPE_SELL_STOP_LIMIT",
            )
            if hasattr(self._mt5, name)
        }
        numeric = int(value)
        if numeric in buy_types:
            return "BUY"
        if numeric in sell_types:
            return "SELL"
        raise MT5ReadOnlyError("unsupported MT5 order side")

    def observe_positions(self) -> tuple[PositionObservation, ...]:
        self._guard()
        assert self._mt5 is not None
        raw = self._mt5.positions_get()
        if raw is None:
            raise MT5ReadOnlyError(f"positions_get failed: {self._mt5.last_error()}")
        output: list[PositionObservation] = []
        for item in raw:
            row = _record(item, "position")
            output.append(
                PositionObservation(
                    position_id=str(row.get("ticket") or row.get("identifier") or ""),
                    symbol=str(row.get("symbol") or ""),
                    side=self._position_side(row.get("type")),
                    volume_lots=_decimal(row.get("volume"), "position volume"),
                )
            )
        return tuple(output)

    def observe_orders(self) -> tuple[OrderObservation, ...]:
        self._guard()
        assert self._mt5 is not None
        raw = self._mt5.orders_get()
        if raw is None:
            raise MT5ReadOnlyError(f"orders_get failed: {self._mt5.last_error()}")
        output: list[OrderObservation] = []
        for item in raw:
            row = _record(item, "order")
            volume = row.get("volume_current")
            if volume in (None, 0, 0.0):
                volume = row.get("volume_initial")
            output.append(
                OrderObservation(
                    order_id=str(row.get("ticket") or ""),
                    symbol=str(row.get("symbol") or ""),
                    side=self._order_side(row.get("type")),
                    volume_lots=_decimal(volume, "order volume"),
                    state=str(row.get("state") or ""),
                )
            )
        return tuple(output)

    def read_latest_quote(self, *, symbol: str, as_of: datetime) -> Quote | None:
        if symbol != "XAUUSD":
            raise MT5ReadOnlyError("production candidate is bound to XAUUSD")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise MT5ReadOnlyError("as_of must be timezone-aware")
        self._guard()
        assert self._mt5 is not None
        tick_raw = self._mt5.symbol_info_tick(symbol)
        if tick_raw is None:
            return None
        tick = _record(tick_raw, "symbol_info_tick")
        info = _record(self._mt5.symbol_info(symbol), "symbol_info")
        tick_size = info.get("trade_tick_size") or info.get("point")
        if tick.get("time_msc") is not None:
            broker_time = _utc_from_epoch(tick["time_msc"], milliseconds=True)
            sequence = int(tick["time_msc"])
        else:
            broker_time = _utc_from_epoch(tick.get("time"))
            sequence = int(float(tick.get("time") or 0) * 1000)
        return Quote(
            symbol=symbol,
            broker_time=broker_time,
            received_time=as_of.astimezone(UTC),
            bid=_decimal(tick.get("bid"), "bid"),
            ask=_decimal(tick.get("ask"), "ask"),
            tick_size=_decimal(tick_size, "tick_size"),
            sequence=max(sequence, 0),
        )

    def read_completed_bars(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        as_of: datetime,
        limit: int,
    ) -> tuple[Bar, ...]:
        if symbol != "XAUUSD":
            raise MT5ReadOnlyError("production candidate is bound to XAUUSD")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise MT5ReadOnlyError("as_of must be timezone-aware")
        if limit <= 0:
            raise MT5ReadOnlyError("bar limit must be positive")
        self._guard()
        assert self._mt5 is not None
        names = {
            Timeframe.M15: "TIMEFRAME_M15",
            Timeframe.H1: "TIMEFRAME_H1",
            Timeframe.H4: "TIMEFRAME_H4",
        }
        mt5_timeframe = getattr(self._mt5, names[timeframe])
        rows = self._mt5.copy_rates_from_pos(symbol, mt5_timeframe, 1, limit)
        if rows is None:
            raise MT5ReadOnlyError(f"copy_rates_from_pos failed: {self._mt5.last_error()}")
        bars: list[Bar] = []
        for row in rows:
            bars.append(
                Bar(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=_utc_from_epoch(row["time"]),
                    open=_decimal(row["open"], "bar open"),
                    high=_decimal(row["high"], "bar high"),
                    low=_decimal(row["low"], "bar low"),
                    close=_decimal(row["close"], "bar close"),
                    tick_volume=int(row["tick_volume"]),
                )
            )
        bars.sort(key=lambda item: item.open_time)
        return tuple(bars)

    def preflight(self) -> dict[str, object]:
        account = self.observe_account()
        symbol = self.observe_symbol_fingerprint("XAUUSD")
        build = self.observe_build_fingerprint()
        positions = self.observe_positions()
        orders = self.observe_orders()
        return {
            "connected": account.connected,
            "trading_api_disabled": account.trading_api_disabled,
            "symbol": symbol.symbol,
            "broker": account.fingerprint.broker,
            "server": account.fingerprint.server,
            "account_id_sha256": account.fingerprint.account_id_sha256,
            "terminal_build": build.terminal_build,
            "python_bridge_version": build.python_bridge_version,
            "open_positions": len(positions),
            "pending_orders": len(orders),
            "execution_enabled": False,
            "broker_action_count": 0,
        }
