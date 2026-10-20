"""APC DEMO single attended READ-ONLY MT5 preflight; NEVER execute without approval.

This source is intended for a one-shot PowerShell here-string piped into the
pinned existing Python interpreter via stdin (-B -I -), preventing legacy
PowerShell 5.1 -c quote mangling. It performs MT5 initialize(existing) but
NO order, login, symbol_select, history, file write or configuration action.
MT5 initialize can still launch/activate a terminal; supervision required.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import sys
import time
from typing import Any

PYTHON_PATH = r"C:\Program Files\Python312\python.exe"
MT5_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
EXPECTED_DIST_VERSION = "5.0.6090"
EXPECTED_FINGERPRINT = "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"
BROKER = "Exness Technologies Ltd"
SERVER = "Exness-MT5Trial15"
CURRENCY = "USD"
MAX_QUOTE_AGE_MS = 5000


def _row(item: Any) -> dict[str, Any]:
    if item is None:
        raise ValueError("UNKNOWN_MT5_RECORD")
    if isinstance(item, dict):
        return item
    if hasattr(item, "_asdict"):
        return dict(item._asdict())
    raise ValueError("INVALID_MT5_RECORD")


def _numeric(value: Any, name: str) -> float:
    import math

    if value is None or isinstance(value, bool):
        raise ValueError("MISSING_" + name)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("NONFINITE_" + name)
    return result


def inspect(mt5: Any, observed_msec: int) -> dict[str, Any]:
    """Pure source-data checks; caller manages MT5 attach and process snapshots."""
    t = _row(mt5.terminal_info())
    a = _row(mt5.account_info())
    if t.get("connected") is not True:
        raise ValueError("TERMINAL_DISCONNECTED")
    if t.get("tradeapi_disabled") is not True:
        raise ValueError("PREFLIGHT_REQUIRES_EXTERNAL_PYTHON_TRADING_DISABLED")
    if a.get("trade_mode") != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise ValueError("LIVE_OR_UNEXPECTED_ACCOUNT_MODE")
    if (a.get("company"), a.get("server"), a.get("currency")) != (
        BROKER, SERVER, CURRENCY
    ):
        raise ValueError("UNADMITTED_DEMO_BROKER_SERVER_CURRENCY")
    login = a.get("login")
    if type(login) is not int or login <= 0:
        raise ValueError("UNVERIFIED_LOGIN")
    fingerprint = hashlib.sha256(
        f"{BROKER}|{SERVER}|{login}|{CURRENCY}".encode()
    ).hexdigest()
    if fingerprint != EXPECTED_FINGERPRINT:
        raise ValueError("UNADMITTED_ACCOUNT_FINGERPRINT")
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        raise ValueError("EXPOSURE_UNKNOWN")
    if tuple(positions) or tuple(orders):
        raise ValueError("EXISTING_POSITIONS_OR_PENDING_ORDERS")
    info = _row(mt5.symbol_info("XAUUSD"))
    tick = _row(mt5.symbol_info_tick("XAUUSD"))
    if info.get("name") != "XAUUSD":
        raise ValueError("SYMBOL_NOT_EXACT_XAUUSD")
    if info.get("trade_mode") != mt5.SYMBOL_TRADE_MODE_FULL:
        raise ValueError("XAUUSD_NOT_FULLY_TRADEABLE")
    if info.get("currency_profit") != "USD":
        raise ValueError("XAUUSD_PROFIT_CURRENCY_NOT_USD")
    age = observed_msec - tick.get("time_msc", -1)
    if not isinstance(age, int) or age < 0 or age > MAX_QUOTE_AGE_MS:
        raise ValueError("STALE_OR_UNVERIFIED_QUOTE")
    bid = _numeric(tick.get("bid"), "BID")
    ask = _numeric(tick.get("ask"), "ASK")
    if not (0 < bid < ask <= bid + 1.0):
        raise ValueError("INVERTED_OR_EXCESSIVE_SPREAD")
    numeric_keys = (
        "trade_tick_size", "trade_tick_value_loss", "trade_contract_size",
        "volume_min", "volume_max", "volume_step", "point",
    )
    numbers = {name: _numeric(info.get(name), name) for name in numeric_keys}
    if any(value <= 0 for value in numbers.values()):
        raise ValueError("INVALID_SYMBOL_NUMERIC")
    filling_flags = info.get("filling_mode")
    if type(filling_flags) is not int or filling_flags & 3 == 0:
        raise ValueError("UNSUPPORTED_FOK_IOC_FILLING_MODE")
    if numbers["volume_min"] > 0.01 or numbers["volume_max"] < 0.01:
        raise ValueError("BROKER_REJECTS_001_LOT")
    grid = (0.01 - numbers["volume_min"]) / numbers["volume_step"]
    if abs(grid - round(grid)) > 1e-7:
        raise ValueError("BROKER_VOLUME_GRID_REJECTS_001")
    tick_usd = numbers["trade_tick_size"] * numbers["trade_contract_size"]
    if abs(numbers["trade_tick_value_loss"] - tick_usd) > tick_usd * 0.01:
        raise ValueError("LOSS_TICK_VALUE_CONTRACT_MISMATCH")
    margin = _numeric(a.get("margin"), "MARGIN")
    equity = _numeric(a.get("equity"), "EQUITY")
    balance = _numeric(a.get("balance"), "BALANCE")
    free = _numeric(a.get("margin_free"), "FREE_MARGIN")
    if margin < 0 or min(equity, balance, free) <= 0:
        raise ValueError("ACCOUNT_CASH_INVALID")
    return {
        "status": "READ_ONLY_DEMO_PREFLIGHT_PASS",
        "scope": "DEMO_CANARY_ONLY_NOT_ACTIVATED",
        "python_trading_disabled": True,
        "account_fingerprint_sha256": fingerprint,
        "company": BROKER, "server": SERVER, "currency": CURRENCY,
        "trade_mode": "DEMO", "positions": 0, "pending_orders": 0,
        "symbol": "XAUUSD", "tick_age_msec": age,
        "bid": bid, "ask": ask,
        "symbol_metadata": numbers,
        "trade_stops_level": info.get("trade_stops_level"),
        "trade_freeze_level": info.get("trade_freeze_level"),
        "symbol_filling_mode_flags": filling_flags,
        "account_equity_usd": equity,
        "account_balance_usd": balance,
        "account_margin_used_usd": margin,
        "account_free_margin_usd": free,
        "order_api_calls": 0,
        "canary_runtime_staged": False,
    }


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("WINDOWS_ONLY")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("PYTHON_NOT_312")
    if sys.executable.casefold() != PYTHON_PATH.casefold():
        raise RuntimeError("UNEXPECTED_PYTHON_EXECUTABLE")
    if importlib.metadata.version("MetaTrader5") != EXPECTED_DIST_VERSION:
        raise RuntimeError("UNEXPECTED_METATRADER5_DISTRIBUTION_VERSION")
    mt5 = importlib.import_module("MetaTrader5")
    if getattr(mt5, "__version__", None) != EXPECTED_DIST_VERSION:
        raise RuntimeError("UNEXPECTED_METATRADER5_MODULE_VERSION")
    # This may activate/spawn MT5 even though no trading methods are called.
    if not mt5.initialize(path=MT5_TERMINAL_PATH, timeout=10000):
        raise RuntimeError("MT5_ATTACH_FAILED")
    try:
        snapshot = inspect(mt5, int(time.time() * 1000))
        print(json.dumps(snapshot, sort_keys=True, allow_nan=False))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
