"""Single, comprehensive owner-run MT5 read-only broker evidence collector.

Uses the existing Exness Pro DEMO connection, never changes account/symbol,
places/checks/cancels no orders, and never asserts calibrated Policy A
or live-production readiness. One invocation captures all currently observable
account/symbol/history/timeframe/monetary fields plus a prospective 4h
5-second quote window. Evidence is kept locally, not in a GitHub repository.

Historic tick lookback is only background context, NOT a substitute for
the owner-preregistered v1.1 prospective window or official event evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

# -I ignores PYTHONPATH and the current directory. Explicitly bind all
# THREE import roots to the exported source tree, not installed/editable
# packages from the VPS or Git worktree. Import resolution must be safe even
# under -I -S (no site packages) before touching MetaTrader5.
_STAGED_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_STAGED_REPO_ROOT / "src"))
sys.path.insert(0, str(_STAGED_REPO_ROOT / "demo_adapter"))
sys.path.insert(0, str(_STAGED_REPO_ROOT / "demo_adapter" / "src"))

from xauusd_demo.broker_money_readonly import (  # noqa: E402, I001
    EXPECTED_ACCOUNT_SHA256, EXPECTED_COMPANY, EXPECTED_SERVER,
    inspect_real_demo_money,
)
from xauusd_demo.envelope import DemoSafetyError  # noqa: E402
from xauusd_demo.mt5_demo import _decimal, _record  # noqa: E402
from scripts.v11_quote_coverage import (  # noqa: E402
    QuoteCoverageError, QuoteSample, evaluate_quote_coverage,
)

SYMBOL = "XAUUSD"
SAMPLE_SECONDS = 5
WINDOW_SECONDS = 4 * 60 * 60
MAX_TICKS = 1_500_000
HISTORY_FROM = datetime(2000, 1, 1, tzinfo=UTC)
UTC_CLOCK_SKEW_SECONDS = 5
READONLY_METHODS = (
    "initialize", "shutdown", "terminal_info", "account_info", "symbol_info",
    "symbol_info_tick", "positions_get", "orders_get", "history_deals_get",
    "history_orders_get", "copy_ticks_range", "copy_rates_from_pos",
    "order_calc_profit", "order_calc_margin",
)
FORBIDDEN_METHODS = (
    "order_send", "order_check", "login", "symbol_select",
    "order_delete", "order_modify",
)


# Fixed, source-reviewed reasons only. Never echo str(exc) from an MT5,
# filesystem or history exception: it may contain sensitive account data.
_SAFE_GUARD_CODES: dict[str, str] = {
    "MT5 disconnected or external Python trading not disabled":
        "DEMO_TERMINAL_DISCONNECTED_OR_PYTHON_TRADING_ENABLED",
    "unexpected Exness Pro MT5 DEMO account":
        "DEMO_IDENTITY_FIELDS_INVALID",
    "broker account fingerprint mismatched": "DEMO_FINGERPRINT_MISMATCH",
    "pending orders or positions present; no new risk admission":
        "EXPOSURE_NOT_ZERO",
    "XAUUSD broker tick stale / future": "QUOTE_STALE_OR_FUTURE",
    "unusable XAUUSD broker bid/ask": "QUOTE_INVALID_OR_CROSSED",
    "broker minimum lot exceeds frozen 0.01": "BROKER_MIN_LOT_EXCEEDS_CAP",
    "nonpositive tick size": "BROKER_TICK_SIZE_INVALID",
    "broker returned unusable margin": "BROKER_MARGIN_INVALID",
    "broker stop loss must be negative": "BROKER_STOP_CASH_SIGN_INVALID",
    "MT5 account identity or cash changed during source read":
        "ACCOUNT_CHANGED_DURING_READ",
    "terminal disconnected or external Python trading not disabled":
        "LEGACY_TERMINAL_DISCONNECTED_OR_PYTHON_TRADING_ENABLED",
    "MT5 account is not DEMO": "LEGACY_NOT_DEMO",
    "Exness account broker/server/currency mismatch":
        "LEGACY_BROKER_IDENTITY_INVALID",
    "MT5 DEMO fingerprint mismatch": "LEGACY_FINGERPRINT_MISMATCH",
    "zero open orders and positions not established":
        "LEGACY_EXPOSURE_NOT_ZERO",
    "XAUUSD instrument is not in full trading mode":
        "LEGACY_SYMBOL_NOT_FULL_TRADING",
    "broker symbol cash/tick/lot specification invalid":
        "LEGACY_SYMBOL_CASH_OR_LOT_SPEC_INVALID",
    "MT5 tick stale or future": "LEGACY_QUOTE_STALE_OR_FUTURE",
    "crossed or unusable XAUUSD quote": "LEGACY_QUOTE_INVALID",
    "account balance/equity/margin invalid": "LEGACY_ACCOUNT_MONEY_INVALID",
    "broker history_deals_get returned no data": "LEGACY_DEAL_HISTORY_MISSING",
    "broker hypothetical protective loss or margin invalid":
        "LEGACY_CALCULATION_INVALID",
    "complete deal history unavailable": "HISTORY_DEALS_UNAVAILABLE",
    "historical orders unavailable": "HISTORY_ORDERS_UNAVAILABLE",
    "empty or oversized tick source": "HISTORICAL_TICKS_EMPTY_OR_OVERSIZED",
    "invalid historical tick time/order/quote":
        "HISTORICAL_TICK_ORDER_OR_PRICE_INVALID",
    "tick time_msc missing": "HISTORICAL_TICK_TIME_MISSING",
    "prospective quote slot missed": "PROSPECTIVE_SLOT_MISSED",
}
for _frame in ("M1", "M5", "M15", "H1", "H4", "D1", "W1"):
    _SAFE_GUARD_CODES[f"missing MT5 {_frame} history"] = (
        f"FRAME_{_frame}_MISSING"
    )


def _safe_guard_code(exc: Exception) -> str:
    """Classify ONLY known fixed safety-check strings; redact everything else."""
    if not isinstance(exc, DemoSafetyError):
        return "UNCLASSIFIED_REDACTED"
    return _SAFE_GUARD_CODES.get(str(exc), "UNCLASSIFIED_REDACTED")


def _utc_time(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise DemoSafetyError("UTC clock required")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _numeric(value: Any, label: str) -> str:
    return str(_decimal(value, label))


def _rows(raw: Any, label: str) -> list[Any]:
    if raw is None:
        raise DemoSafetyError(f"{label} unavailable")
    return list(raw)


def _millis(row: Any) -> int:
    if isinstance(row, dict):
        value = row.get("time_msc")
    else:
        try:
            value = row["time_msc"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise DemoSafetyError("tick time_msc missing") from exc
    if type(value) is not int:
        # numpy scalar integers are not Python int: normalize with a strict
        # roundtrip check, never interpret floating quote timestamps.
        if type(value) is float or value is None:
            raise DemoSafetyError("tick timestamp type invalid")
        try:
            stamp = int(value)
        except (TypeError, ValueError) as exc:
            raise DemoSafetyError("tick timestamp invalid") from exc
    else:
        stamp = value
    if stamp <= 0:
        raise DemoSafetyError("nonpositive broker tick timestamp")
    return stamp


def _field(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError, ValueError):
        return None


class MT5ReadOnlySurface:
    """Explicit method allowlist; the trading methods are never reachable."""

    def __init__(self, raw: Any) -> None:
        self.__raw = raw
        for method in READONLY_METHODS:
            if not callable(getattr(raw, method, None)):
                raise DemoSafetyError(f"missing MT5 read method: {method}")

    def __getattr__(self, method: str) -> Any:
        if method in READONLY_METHODS:
            return getattr(self.__raw, method)
        if method.startswith(("TIMEFRAME_", "ORDER_TYPE_", "COPY_TICKS_", "SYMBOL_")):
            value = getattr(self.__raw, method, None)
            if type(value) is int:
                return value
        raise DemoSafetyError(f"MT5 function not in read-only allowlist: {method}")


def _identity(mt5: MT5ReadOnlySurface, *, require_flat: bool) -> dict[str, Any]:
    terminal = _record(mt5.terminal_info(), "terminal")
    account = _record(mt5.account_info(), "account")
    if terminal.get("connected") is not True or terminal.get("tradeapi_disabled") is not True:
        raise DemoSafetyError("MT5 disconnected or external Python trading not disabled")
    if (
        type(account.get("trade_mode")) is not int or account["trade_mode"] != 0
        or account.get("company") != EXPECTED_COMPANY
        or account.get("server") != EXPECTED_SERVER
        or account.get("currency") != "USD"
        or type(account.get("login")) is not int
        or account["login"] <= 0
    ):
        raise DemoSafetyError("unexpected Exness Pro MT5 DEMO account")
    digest = hashlib.sha256(
        f"{account['company']}|{account['server']}|{account['login']}|USD".encode()
    ).hexdigest()
    if digest != EXPECTED_ACCOUNT_SHA256:
        raise DemoSafetyError("broker account fingerprint mismatched")
    orders = _rows(mt5.orders_get(), "orders_get")
    positions = _rows(mt5.positions_get(), "positions_get")
    if require_flat and (orders or positions):
        raise DemoSafetyError("pending orders or positions present; no new risk admission")
    return {
        "account_fingerprint_sha256": digest,
        "demo_mode": True,
        "tradeapi_disabled": True,
        "terminal_trade_allowed": bool(terminal.get("trade_allowed")) if
            terminal.get("trade_allowed") is not None else "UNKNOWN",
        "account_trade_allowed": bool(account.get("trade_allowed")) if
            account.get("trade_allowed") is not None else "UNKNOWN",
        "positions_count": len(positions),
        "orders_count": len(orders),
        "balance_usd": _numeric(account.get("balance"), "balance"),
        "equity_usd": _numeric(account.get("equity"), "equity"),
        "margin_usd": _numeric(account.get("margin"), "margin"),
        "free_margin_usd": _numeric(account.get("margin_free"), "margin_free"),
        "leverage": account.get("leverage") if type(account.get("leverage")) is int else None,
        "margin_level_pct": (
            _numeric(account["margin_level"], "margin_level")
            if account.get("margin_level") is not None else None
        ),
    }


def symbol_details(mt5: MT5ReadOnlySurface, now: datetime) -> dict[str, Any]:
    _utc_time(now)
    info = _record(mt5.symbol_info(SYMBOL), "symbol info")
    tick = _record(mt5.symbol_info_tick(SYMBOL), "symbol tick")
    required = (
        "trade_tick_size", "trade_tick_value_loss", "trade_tick_value_profit",
        "trade_contract_size", "point", "volume_min", "volume_max",
        "volume_step", "trade_stops_level", "trade_freeze_level",
        "swap_long", "swap_short", "swap_mode",
    )
    data: dict[str, Any] = {}
    for key in required:
        data[key] = _numeric(info.get(key), key)
    for key in (
        "digits", "trade_mode", "trade_exemode", "trade_calc_mode",
        "filling_mode", "expiration_mode", "order_mode",
    ):
        value = info.get(key)
        data[key] = value if type(value) is int else None
    for key in ("bid", "ask"):
        data[key] = _numeric(tick.get(key), key)
    stamp = _millis(tick)
    observed = datetime.fromtimestamp(stamp / 1000, UTC)
    if observed > now + timedelta(seconds=1) or now - observed > timedelta(
        seconds=UTC_CLOCK_SKEW_SECONDS
    ):
        raise DemoSafetyError("XAUUSD broker tick stale / future")
    if Decimal(data["bid"]) <= 0 or Decimal(data["ask"]) <= Decimal(data["bid"]):
        raise DemoSafetyError("unusable XAUUSD broker bid/ask")
    data["tick_time_utc"] = observed.isoformat()
    data["spread_price"] = str(Decimal(data["ask"]) - Decimal(data["bid"]))
    if Decimal(data["volume_min"]) > Decimal("0.01"):
        raise DemoSafetyError("broker minimum lot exceeds frozen 0.01")
    if Decimal(data["trade_tick_size"]) <= 0:
        raise DemoSafetyError("nonpositive tick size")
    return data


def money_matrix(mt5: MT5ReadOnlySurface, symbol: dict[str, Any]) -> list[dict[str, str]]:
    """Actual broker profit and incremental margin for both 0.01-lot sides."""
    tick = Decimal(symbol["trade_tick_size"])
    if tick <= 0:
        raise DemoSafetyError("no tick grid")
    result: list[dict[str, str]] = []
    for side in ("BUY", "SELL"):
        direction = getattr(mt5, "ORDER_TYPE_BUY" if side == "BUY" else "ORDER_TYPE_SELL")
        entry = Decimal(symbol["ask"] if side == "BUY" else symbol["bid"])
        margin = _decimal(mt5.order_calc_margin(
            direction, SYMBOL, 0.01, float(entry)
        ), "broker margin")
        if margin <= 0:
            raise DemoSafetyError("broker returned unusable margin")
        for distance in (Decimal("2"), Decimal("5"), Decimal("10")):
            stop = entry - distance if side == "BUY" else entry + distance
            stop = (stop / tick).to_integral_value() * tick
            loss = _decimal(mt5.order_calc_profit(
                direction, SYMBOL, 0.01, float(entry), float(stop)
            ), "broker stop loss")
            if stop <= 0 or loss >= 0:
                raise DemoSafetyError("broker stop loss must be negative")
            result.append({
                "side": side, "lots": "0.01", "entry": str(entry),
                "stop": str(stop), "stop_distance_price": str(distance),
                "broker_loss_cash_usd": str(-loss),
                "broker_incremental_margin_usd": str(margin),
                "conservative_2x_broker_margin_usd": str(2 * margin),
            })
    return result


def history_summary(mt5: MT5ReadOnlySurface, now: datetime) -> dict[str, Any]:
    _utc_time(now)
    deals = _rows(mt5.history_deals_get(HISTORY_FROM, now), "complete deal history")
    orders = _rows(mt5.history_orders_get(HISTORY_FROM, now), "historical orders")
    fees: list[dict[str, Any]] = []
    cashflow = Decimal(0)
    fee_rows_missing = 0
    deal_types: dict[str, int] = {}
    for raw in deals:
        row = _record(raw, "historical deal")
        key = str(row.get("type", "MISSING"))
        deal_types[key] = deal_types.get(key, 0) + 1
        for field in ("profit", "commission", "swap", "fee"):
            if field in row:
                cashflow += _decimal(row[field], f"history {field}")
            else:
                fee_rows_missing += 1
        if row.get("symbol") == SYMBOL:
            if all(row.get(k) is not None for k in (
                "time_msc", "volume", "commission", "swap", "fee", "profit",
            )):
                fees.append({
                    "time_msc": _millis(row),
                    "volume": _numeric(row["volume"], "deal volume"),
                    "commission_usd": _numeric(row["commission"], "commission"),
                    "swap_usd": _numeric(row["swap"], "swap"),
                    "fee_usd": _numeric(row["fee"], "fee"),
                    "profit_usd": _numeric(row["profit"], "profit"),
                    "entry_class": str(row.get("entry", "UNKNOWN")),
                })
            else:
                fee_rows_missing += 1
    return {
        "history_from_utc": HISTORY_FROM.isoformat(),
        "history_through_utc": now.isoformat(),
        "all_broker_deal_count": len(deals),
        "all_history_order_count": len(orders),
        "all_history_cashflows_if_reported_usd": str(cashflow),
        "account_deal_types_counts": deal_types,
        "fee_rows_missing": fee_rows_missing,
        "xauusd_fee_rows": fees,
        "xauusd_fee_rows_count": len(fees),
        "fee_zero_proven": False,
        "complete_history_proven": False,
        "cash_journal_authorized": False,
    }


def rate_coverage(mt5: MT5ReadOnlySurface) -> dict[str, Any]:
    frames = (
        ("M1", "TIMEFRAME_M1", 2000), ("M5", "TIMEFRAME_M5", 1200),
        ("M15", "TIMEFRAME_M15", 1200), ("H1", "TIMEFRAME_H1", 1200),
        ("H4", "TIMEFRAME_H4", 1200), ("D1", "TIMEFRAME_D1", 370),
        ("W1", "TIMEFRAME_W1", 110),
    )
    out: dict[str, Any] = {}
    for name, const, count in frames:
        timeframe = getattr(mt5, const)
        bars = _rows(mt5.copy_rates_from_pos(SYMBOL, timeframe, 0, count),
                     f"{name} rates")
        if not bars:
            raise DemoSafetyError(f"missing MT5 {name} history")
        first, last = bars[0], bars[-1]
        stamps = [_field(row, "time") for row in bars]
        if any(value is None for value in stamps):
            raise DemoSafetyError(f"{name} bar timestamps incomplete")
        out[name] = {
            "bar_count": len(bars),
            "first_bar_utc": datetime.fromtimestamp(int(_field(first, "time")), UTC).isoformat(),
            "last_bar_utc": datetime.fromtimestamp(int(_field(last, "time")), UTC).isoformat(),
            "bar_times_sha256": _sha([int(x) for x in stamps]),
            "last_bar_open": _numeric(_field(last, "open"), f"{name} open"),
            "last_bar_close": _numeric(_field(last, "close"), f"{name} close"),
            "live_current_bar_included": True,
            "completed_bar_strategy_admitted": False,
        }
    return out


def tick_window(
    mt5: MT5ReadOnlySurface, start: datetime, end: datetime, *,
    on_tick: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    _utc_time(start)
    _utc_time(end)
    if end <= start or end - start > timedelta(hours=4):
        raise DemoSafetyError("tick window invalid")
    ticks = _rows(mt5.copy_ticks_range(
        SYMBOL, start, end, mt5.COPY_TICKS_INFO
    ), "tick window")
    if not ticks or len(ticks) > MAX_TICKS:
        raise DemoSafetyError("empty or oversized tick source")
    bid_min, bid_max = Decimal("Infinity"), Decimal("-Infinity")
    spread_min, spread_max = Decimal("Infinity"), Decimal("-Infinity")
    earliest: int | None = None
    latest: int | None = None
    digest = hashlib.sha256()
    previous = 0
    max_adjacent_tick_jump = Decimal(0)
    max_intertick_gap_ms = 0
    last_bid: Decimal | None = None
    for raw in ticks:
        stamp = _millis(raw)
        bid = _decimal(_field(raw, "bid"), "tick bid")
        ask = _decimal(_field(raw, "ask"), "tick ask")
        if (
            stamp < int(start.timestamp() * 1000) or
            stamp > int(end.timestamp() * 1000) or
            stamp < previous or bid <= 0 or ask <= bid
        ):
            raise DemoSafetyError("invalid historical tick time/order/quote")
        if previous:
            max_intertick_gap_ms = max(max_intertick_gap_ms, stamp - previous)
            if last_bid is not None:
                max_adjacent_tick_jump = max(
                    max_adjacent_tick_jump, abs(bid - last_bid)
                )
        previous = stamp
        last_bid = bid
        if on_tick is not None:
            on_tick({"time_msc": stamp, "bid": str(bid), "ask": str(ask)})
        earliest = stamp if earliest is None else earliest
        latest = stamp
        bid_min, bid_max = min(bid_min, bid), max(bid_max, bid)
        spread = ask - bid
        spread_min, spread_max = min(spread_min, spread), max(spread_max, spread)
        digest.update(_canonical([stamp, str(bid), str(ask)]))
    return {
        "start_utc": start.isoformat(), "end_utc": end.isoformat(),
        "tick_count": len(ticks), "first_tick_msc": earliest,
        "last_tick_msc": latest, "tick_bid_min": str(bid_min),
        "tick_bid_max": str(bid_max), "spread_min_price": str(spread_min),
        "spread_max_price": str(spread_max),
        "max_adjacent_bid_jump_price": str(max_adjacent_tick_jump),
        "max_intertick_gap_ms": max_intertick_gap_ms,
        "sanitized_tick_sha256": digest.hexdigest(),
        "independently_admitted_prospective_v11_evidence": False,
    }


def collect_static(
    mt5: MT5ReadOnlySurface, now: datetime, *,
    on_historical_tick: Callable[[dict[str, Any]], None] | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """One comprehensive account, quote, history, risk, bar and past-tick read.

    Stage callbacks contain *constant* safety codes, never raw broker data.
    They preserve diagnostic provenance if a source guard fails closed.
    """
    _utc_time(now)

    def stage(code: str) -> None:
        if on_stage is not None:
            on_stage(code)

    stage("STATIC_ACCOUNT_IDENTITY_AND_EXPOSURE")
    before = _identity(mt5, require_flat=True)
    stage("STATIC_SYMBOL_QUOTE_AND_CONTRACT")
    symbol = symbol_details(mt5, now)
    stage("STATIC_BROKER_PROFIT_AND_MARGIN")
    money = money_matrix(mt5, symbol)
    # Run the existing strict broker-money validator immediately while its
    # attached quote remains fresh; slow history/rates reads follow afterward.
    stage("STATIC_LEGACY_BROKER_MONEY_GUARD")
    legacy_money = inspect_real_demo_money(mt5, now=now)
    stage("STATIC_ACCOUNT_DEAL_ORDER_HISTORY")
    history = history_summary(mt5, now)
    stage("STATIC_SEVEN_TIMEFRAME_BARS")
    frames = rate_coverage(mt5)
    stage("STATIC_HISTORICAL_BROKER_TICKS")
    ticks = tick_window(
        mt5, now - timedelta(hours=4), now,
        on_tick=on_historical_tick,
    )
    stage("STATIC_FINAL_IDENTITY_AND_EXPOSURE")
    after = _identity(mt5, require_flat=True)
    if (
        before["account_fingerprint_sha256"] != after["account_fingerprint_sha256"]
        or before["balance_usd"] != after["balance_usd"]
        or before["equity_usd"] != after["equity_usd"]
    ):
        raise DemoSafetyError("MT5 account identity or cash changed during source read")
    return {
        "schema": "EXNESS_DEMO_COMPREHENSIVE_READONLY_V1",
        "capture_started_utc": now.isoformat(),
        "account_before": before, "account_after": after,
        "symbol": symbol, "broker_money_0_01": money,
        "prior_money_inspector": legacy_money,
        "historical_cash_and_fee_evidence": history,
        "seven_frame_coverage": frames, "past_four_hour_tick_context": ticks,
        "official_events_source_authenticated": False,
        "session_holiday_source_authenticated": False,
        "v11_cost_calibration_admitted": False,
        "policy_a_execution_admitted": False,
        "broker_order_check_calls": 0, "broker_order_send_calls": 0,
        "live_real_money_authorized": False,
    }


def collect_prospective_quotes(
    mt5: MT5ReadOnlySurface, *,
    start: datetime,
    now_fn: Callable[[], datetime],
    sleep_fn: Callable[[float], None],
    duration_seconds: int = WINDOW_SECONDS,
    sample_seconds: int = SAMPLE_SECONDS,
    on_sample: Callable[[dict[str, Any]], None] | None = None,
    on_tick: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Exactly one prospective contiguous window; no synthetic backfilling.

    The default is a four-hour run of 5-second snapshots. All official source
    and owner-preregistration evidence remains independently unadmitted.
    """
    _utc_time(start)
    if duration_seconds <= 0 or duration_seconds % sample_seconds:
        raise DemoSafetyError("prospective sampling duration invalid")
    if sample_seconds <= 0:
        raise DemoSafetyError("prospective sampling cadence invalid")
    if (now_fn() - start).total_seconds() > sample_seconds:
        raise DemoSafetyError("sampling start was missed")
    samples = 0
    spread_min = Decimal("Infinity")
    spread_max = Decimal("-Infinity")
    hash_samples = hashlib.sha256()
    for i in range(duration_seconds // sample_seconds):
        target = start + timedelta(seconds=i * sample_seconds)
        while (wait := (target - now_fn()).total_seconds()) > 0:
            sleep_fn(min(wait, 1.0))
        stamp = now_fn()
        if stamp < target or stamp >= target + timedelta(seconds=sample_seconds):
            raise DemoSafetyError("prospective quote slot missed")
        if i % 12 == 0:
            _identity(mt5, require_flat=True)
        symbol = symbol_details(mt5, stamp)
        row = {
            "slot": i, "observed_utc": stamp.isoformat(),
            "bid": symbol["bid"], "ask": symbol["ask"],
            "tick_time_utc": symbol["tick_time_utc"],
        }
        if on_sample is not None:
            on_sample(row)
        hash_samples.update(_canonical(row))
        spread = Decimal(symbol["spread_price"])
        spread_min = min(spread_min, spread)
        spread_max = max(spread_max, spread)
        samples += 1
    finish = start + timedelta(seconds=duration_seconds)
    while (wait := (finish - now_fn()).total_seconds()) > 0:
        sleep_fn(min(wait, 1.0))
    if now_fn() > finish + timedelta(seconds=sample_seconds):
        raise DemoSafetyError("prospective window ended late")
    _identity(mt5, require_flat=True)
    broker_ticks = tick_window(mt5, start, finish, on_tick=on_tick)
    return {
        "expected_slots": duration_seconds // sample_seconds,
        "observed_slots": samples,
        "start_utc": start.isoformat(), "end_utc": finish.isoformat(),
        "quote_spread_min": str(spread_min),
        "quote_spread_max": str(spread_max),
        "quote_samples_sha256": hash_samples.hexdigest(),
        "broker_tick_summary": broker_ticks,
        "prospective_observation_complete": True,
        "owner_preregistration_independently_verified": False,
        "official_news_session_prechecked": False,
        "calibration_admitted": False,
    }




def private_v11_quote_proxy(
    *, start: datetime, end: datetime, polls_path: Path, ticks_path: Path
) -> dict[str, Any]:
    """Run strict OFFLINE quote coverage from the same private raw capture.

    A failure records usable evidence without inventing a zero fee/slippage or
    asking the operator to repeat an otherwise successful four-hour reading.
    """
    def read_rows(path: Path) -> list[dict[str, Any]]:
        with path.open(encoding="utf-8") as handle:
            return [json.loads(row) for row in handle if row.strip()]

    polls = [
        QuoteSample(
            int(datetime.fromisoformat(x["observed_utc"]).timestamp() * 1000),
            str(x["bid"]), str(x["ask"]),
        )
        for x in read_rows(polls_path)
    ]
    ticks = [
        QuoteSample(int(x["time_msc"]), str(x["bid"]), str(x["ask"]))
        for x in read_rows(ticks_path)
    ]
    try:
        outcome = evaluate_quote_coverage(
            start, end, polls, ticks, pair_tolerance_ms=1000,
        )
    except QuoteCoverageError as exc:
        return {
            "status": "QUOTE_COVERAGE_FAIL_CLOSED_NOT_ADMITTED",
            "failure_class": type(exc).__name__,
            "failure_reason": str(exc),
            "adverse_cost_usd_admitted": False,
        }
    return asdict(outcome) | {
        "adverse_cost_usd_admitted": False,
        "official_event_and_session_preregistration_admitted": False,
    }

def _write_private(path: Path, content: bytes) -> None:
    # Exclusive creation prevents overwriting an earlier evidence capture.
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()


def _public_summary(report: dict[str, Any]) -> dict[str, Any]:
    account = report.get("account_before", {})
    extra = report.get("prospective_window") or {}
    frame = report.get("seven_frame_coverage", {})
    return {
        "schema": "EXNESS_DEMO_READONLY_SHAREABLE_SUMMARY_V1",
        "capture_id_sha256": _sha(report),
        "status": report.get("status"),
        "account_fingerprint_matches_pinned_demo": account.get(
            "account_fingerprint_sha256"
        ) == EXPECTED_ACCOUNT_SHA256,
        "broker": EXPECTED_COMPANY, "server": EXPECTED_SERVER,
        "lot_verified": "0.01",
        "zero_positions": account.get("positions_count") == 0,
        "zero_pending_orders": account.get("orders_count") == 0,
        "seven_frame_counts": {
            k: v.get("bar_count") for k, v in frame.items()
        },
        "real_money_matrix": report.get("broker_money_0_01"),
        "historical_fee_rows": report.get(
            "historical_cash_and_fee_evidence", {}
        ).get("xauusd_fee_rows_count"),
        "four_hour_quote_slots": extra.get("observed_slots"),
        "four_hour_quote_proxy": report.get("v11_quote_proxy"),
        "four_hour_tick_count": extra.get("broker_tick_summary", {}).get("tick_count"),
        "full_policy_a_admitted": False,
        "official_event_guard_admitted": False,
        "order_check_calls": 0, "order_send_calls": 0,
        "live_real_money_authorized": False,
        "limitations": [
            "MT5 cannot independently prove future official calendar news validity",
            "Historic tick data do not substitute for prospectively registered v1.1",
            "No real execution fees/slippage/gaps if no broker XAUUSD deals",
            "No account-switch, trade-toggle or broker order action performed",
        ],
    }


def _pinned_local_import_check() -> bool:
    """No MT5 attach, no network, no side effects. Verify all source origins."""
    import xauusd_agent

    import scripts.v11_quote_coverage as quote_module
    import xauusd_demo

    expected = (
        (_STAGED_REPO_ROOT / "src" / "xauusd_agent" / "__init__.py").resolve(),
        (_STAGED_REPO_ROOT / "demo_adapter" / "src" / "xauusd_demo" /
         "__init__.py").resolve(),
        (_STAGED_REPO_ROOT / "demo_adapter" / "scripts" /
         "v11_quote_coverage.py").resolve(),
    )
    origins = (
        Path(xauusd_agent.__file__ or "").resolve(),
        Path(xauusd_demo.__file__ or "").resolve(),
        Path(quote_module.__file__ or "").resolve(),
    )
    return origins == expected


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One-shot real MT5 DEMO read-only evidence")
    parser.add_argument("--confirm-owner-readonly", action="store_true")
    parser.add_argument("--self-check-imports", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prospective-four-hours", action="store_true")
    args = parser.parse_args(argv)
    if args.self_check_imports:
        # This path is callable under python -I -S without MetaTrader5 or any
        # third-party packages. It does NOT initialize/attach to the terminal.
        if args.confirm_owner_readonly or args.prospective_four_hours or args.output:
            print("PINNED_IMPORT_PREFLIGHT_INVALID_ARGUMENTS")
            return 2
        if not _pinned_local_import_check():
            print("PINNED_IMPORT_PREFLIGHT_SOURCE_MISMATCH")
            return 1
        print("PINNED_LOCAL_IMPORT_PREFLIGHT_PASS_NO_MT5")
        return 0
    if not args.confirm_owner_readonly:
        print("NOT_RUN_OWNER_READONLY_CONFIRMATION_REQUIRED")
        return 2
    if args.output is None or args.output.exists() or not args.output.is_absolute():
        print("NOT_RUN_PRIVATE_EVIDENCE_DIRECTORY_MUST_BE_NEW_ABSOLUTE")
        return 2
    mt5: MT5ReadOnlySurface | None = None
    initialized = False
    report: dict[str, Any] = {"status": "INCOMPLETE_FAIL_CLOSED_NO_ORDER"}
    failure_stage = "MT5_MODULE_IMPORT"

    def mark_stage(code: str) -> None:
        nonlocal failure_stage
        failure_stage = code

    try:
        raw = importlib.import_module("MetaTrader5")
        mark_stage("MT5_READONLY_METHOD_ALLOWLIST")
        mt5 = MT5ReadOnlySurface(raw)
        mark_stage("MT5_INITIALIZE")
        if not mt5.initialize():
            raise DemoSafetyError("attached MT5 terminal initialize failed")
        initialized = True
        now = datetime.now(UTC)
        mark_stage("PRIVATE_EVIDENCE_DIRECTORY_CREATE")
        args.output.mkdir(parents=True, exist_ok=False)
        mark_stage("STATIC_BROKER_OBSERVATIONS")
        with (args.output / "past_four_hour_broker_ticks.jsonl").open("xb") as stream:
            def write_historic(row: dict[str, Any]) -> None:
                stream.write(_canonical(row))
            report.update(collect_static(
                mt5, now, on_historical_tick=write_historic,
                on_stage=mark_stage,
            ))
        report["status"] = "STATIC_COMPLETE_FOUR_HOUR_PENDING"
        mark_stage("STATIC_EVIDENCE_SEAL")
        _write_private(args.output / "static_evidence.json", _canonical(report))
        if args.prospective_four_hours:
            mark_stage("PROSPECTIVE_REGISTRATION")
            # Durable source/timing registration is written BEFORE the first
            # observation; unknown official event/session provenance is null.
            start = datetime.now(UTC) + timedelta(seconds=3)
            finish = start + timedelta(seconds=WINDOW_SECONDS)
            registration = {
                "schema": "ONE_RUN_4H_SOURCE_PROSPECTIVE_REGISTRATION_V1",
                "written_before_first_sample_utc": datetime.now(UTC).isoformat(),
                "start_utc": start.isoformat(), "end_utc": finish.isoformat(),
                "sample_seconds": SAMPLE_SECONDS,
                "expected_slots": WINDOW_SECONDS // SAMPLE_SECONDS,
                "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "account_fingerprint_sha256": EXPECTED_ACCOUNT_SHA256,
                "owner_attended_readonly_confirmation": True,
                "official_event_and_session_sha256": None,
                "accepted_v11_preregistration": False,
                "broker_order_actions": 0,
            }
            _write_private(
                args.output / "prospective_run_registration.json",
                _canonical(registration),
            )
            report["prospective_registration_sha256"] = _sha(registration)
            poll_file = args.output / "prospective_quote_samples.jsonl"
            tick_file = args.output / "prospective_broker_ticks.jsonl"
            with poll_file.open("xb") as samples, tick_file.open("xb") as ticks:
                def write_row(row: dict[str, Any]) -> None:
                    samples.write(_canonical(row))
                    samples.flush()

                def write_tick(row: dict[str, Any]) -> None:
                    ticks.write(_canonical(row))

                mark_stage("PROSPECTIVE_FOUR_HOUR_SAMPLING")
                report["prospective_window"] = collect_prospective_quotes(
                    mt5, start=start, now_fn=lambda: datetime.now(UTC),
                    sleep_fn=time.sleep, on_sample=write_row, on_tick=write_tick,
                )
            mark_stage("OFFLINE_QUOTE_COVERAGE")
            report["v11_quote_proxy"] = private_v11_quote_proxy(
                start=start, end=finish, polls_path=poll_file, ticks_path=tick_file,
            )
            report["status"] = "COMPLETE_READONLY_NOT_ADMITTED"
        else:
            report["status"] = "STATIC_COMPLETE_PROSPECTIVE_NOT_COLLECTED"
        mark_stage("FINAL_EVIDENCE_SEAL")
        _write_private(args.output / "complete_evidence.json", _canonical(report))
        summary = _public_summary(report)
        _write_private(args.output / "shareable_summary.json", _canonical(summary))
        print(json.dumps(summary, sort_keys=True))
        return 0
    except Exception as exc:
        # Never print raw account, historic trade IDs or MT5 exception detail.
        failure = {
            "status": "FAIL_CLOSED_NO_ORDER",
            "error_type": type(exc).__name__,
            "safe_guard_code": _safe_guard_code(exc),
            # Only a fixed source-code stage label: no exception string,
            # account identity, tickets, history, credentials or raw MT5 data.
            "failure_stage": failure_stage,
            "private_static_evidence_present": (
                args.output / "static_evidence.json"
            ).is_file(),
            "private_prospective_registration_present": (
                args.output / "prospective_run_registration.json"
            ).is_file(),
            "output_location": "PRIVATE_LOCAL_ONLY",
            "order_check_calls": 0, "order_send_calls": 0,
            "no_retry_without_source_review": True,
        }
        if args.output.exists():
            try:
                _write_private(args.output / "failure.json", _canonical(failure))
            except OSError:
                pass
        print(json.dumps(failure, sort_keys=True))
        return 1
    finally:
        if initialized and mt5 is not None:
            mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(run())
