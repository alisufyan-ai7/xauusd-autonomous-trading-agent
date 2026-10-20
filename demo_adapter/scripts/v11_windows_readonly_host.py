"""Four-hour owner-gated DEMO-ADMIT v1.1 read-only evidence collector.

Source preparation and tests do not import MT5. The real adapter is dynamically
imported ONLY after a separately authorized run record, exact code hash and
terminal singleton have been verified by the attended Windows launcher.
This is NOT an execution/risk admission, and cannot send/check an order.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Protocol

# Python -I deliberately omits working/script directory; add only this reviewed
# project-local scripts root (its bytes are separately checked by the launcher).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.v11_readonly_collector import (
    CaptureSafetyError,
    WindowContract,
    _identity_and_zero,
    _market,
    _object,
)

SYMBOL = "XAUUSD"
TERMINAL_EXE = r"C:\Program Files\MetaTrader 5\terminal64.exe"
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"
EXPECTED_TICK_FLAGS = 1  # MT5 COPY_TICKS_INFO: real bid/ask updates
SLOTS = 2880
SLOT_SECONDS = 5
MAX_TICKS = 1500000

# Only these MT5 methods may be used for the one evidence run, plus
# initialize/shutdown lifecycle with an already-existing terminal.
READ_CALLS = frozenset({
    "terminal_info", "account_info", "symbol_info", "symbol_info_tick",
    "positions_get", "orders_get", "copy_ticks_range", "history_deals_get",
})
LIFECYCLE_CALLS = frozenset({"initialize", "shutdown"})
FORBIDDEN_NAMES = frozenset({
    "order_send", "order_check", "order_calc_margin", "order_calc_profit",
    "login", "symbol_select", "history_orders_get", "positions_total",
})


class TickPort(Protocol):
    def terminal_info(self) -> Any: ...
    def account_info(self) -> Any: ...
    def symbol_info(self, symbol: str) -> Any: ...
    def symbol_info_tick(self, symbol: str) -> Any: ...
    def positions_get(self) -> Any: ...
    def orders_get(self) -> Any: ...
    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> Any: ...
    def history_deals_get(self, start: datetime, end: datetime) -> Any: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


def sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def canonical_json(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n").encode()


def _digest_ok(text: object) -> bool:
    return (type(text) is str and len(text) == 64
            and all(c in "0123456789abcdef" for c in text))


def validate_run_record(
    record: dict[str, Any], source: bytes, exact_record_sha256: str
) -> WindowContract:
    """Do all source/owner checks BEFORE importing MetaTrader5."""
    if not _digest_ok(exact_record_sha256):
        raise CaptureSafetyError("run-record hash pin missing")
    if sha256(canonical_json(record)) != exact_record_sha256:
        raise CaptureSafetyError("run-record SHA mismatch")
    if record.get("classification") != "DEMO_LIFECYCLE_ONLY_V1_1_READ_ONLY":
        raise CaptureSafetyError("not a bounded demo read-only capture")
    if record.get("owner_approved_read_only_capture") is not True:
        raise CaptureSafetyError("no separate owner authorization")
    if record.get("terminal_exe") != TERMINAL_EXE:
        raise CaptureSafetyError("terminal executable unpinned")
    if type(record.get("expected_terminal_pid")) is not int:
        raise CaptureSafetyError("terminal PID missing")
    if record["expected_terminal_pid"] <= 0:
        raise CaptureSafetyError("invalid terminal PID")
    if record.get("symbol") != SYMBOL or record.get("volume_max") != "0.01":
        raise CaptureSafetyError("symbol/volume scope mismatch")
    if record.get("mt5_external_python_trading_must_be_disabled") is not True:
        raise CaptureSafetyError("external Python trade disable not bound")
    if not _digest_ok(record.get("exact_collector_source_sha256")):
        raise CaptureSafetyError("collector SHA missing")
    if sha256(source) != record["exact_collector_source_sha256"]:
        raise CaptureSafetyError("collector source SHA mismatch")
    from scripts import v11_readonly_collector as primitive

    primitive_file = Path(primitive.__file__).resolve()
    if primitive_file != Path(__file__).resolve().with_name("v11_readonly_collector.py"):
        raise CaptureSafetyError("unapproved read-only primitive path")
    if sha256(primitive_file.read_bytes()) != record.get("exact_readonly_primitive_sha256"):
        raise CaptureSafetyError("primitive/source SHA mismatch")
    for field in (
        "exact_collector_static_allowlist_verification_sha256",
        "holiday_and_reopening_exclusion_source_sha256",
    ):
        if not _digest_ok(record.get(field)):
            raise CaptureSafetyError(f"missing prospective {field}")
    tol = record.get("tick_pair_tolerance_ms")
    if type(tol) is not int or not 0 <= tol <= 1000:
        raise CaptureSafetyError("tick pairing tolerance must be preregistered")
    if record.get("session_event_eligibility_prechecked") is not True:
        raise CaptureSafetyError("session/event eligibility not pre-registered")
    if record.get("raw_evidence_private_local_only") is not True:
        raise CaptureSafetyError("private evidence boundary missing")
    # Assert immutable original contract and separate owner approval.
    return WindowContract.from_record(record)


def safe_snapshot(port: TickPort, contract: WindowContract, now: datetime) -> dict[str, Any]:
    before = _identity_and_zero(port, contract.expected_identity_sha256)
    market = _market(port)
    after = _identity_and_zero(port, contract.expected_identity_sha256)
    tick_ms = int(market["tick_time_msc"])
    host_ms = int(now.timestamp() * 1000)
    if not 0 <= host_ms - tick_ms <= 5000:
        raise CaptureSafetyError("stale or future tick / clock skew")
    if now.tzinfo != UTC:
        raise CaptureSafetyError("local clock not UTC")
    return {
        "observed_utc": now.isoformat(),
        "observed_ms": host_ms,
        "tick_time_ms": tick_ms,
        "bid": market["bid"],
        "ask": market["ask"],
        "identity_before_sha": before["identity_sha256"],
        "identity_after_sha": after["identity_sha256"],
    }


def _tick_row(raw: Any) -> dict[str, Any]:
    # MT5 returns numpy structured rows; synthetic fakes may supply dicts.
    value = raw if isinstance(raw, dict) else {
        key: raw[key] for key in ("time_msc", "bid", "ask")
    }
    stamp = int(value["time_msc"])
    from decimal import Decimal

    bid = Decimal(str(value["bid"]))
    ask = Decimal(str(value["ask"]))
    if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask <= bid:
        raise CaptureSafetyError("invalid genuine bid/ask tick")
    return {"time_msc": stamp, "bid": str(bid), "ask": str(ask)}


def _number(value: Any, key: str) -> str:
    from decimal import Decimal

    if value is None:
        raise CaptureSafetyError(f"missing broker metadata {key}")
    n = Decimal(str(value))
    if not n.is_finite():
        raise CaptureSafetyError(f"nonfinite broker metadata {key}")
    return str(n)


def account_risk_snapshot(port: TickPort) -> dict[str, str]:
    account = _object(port.account_info(), "account_info")
    values = {}
    for key in ("balance", "equity", "margin", "margin_free"):
        values[key] = _number(account.get(key), key)
    if any(__import__("decimal").Decimal(values[key]) < 0
           for key in ("balance", "equity", "margin", "margin_free")):
        raise CaptureSafetyError("negative account risk fields")
    return values


def symbol_cash_snapshot(port: TickPort) -> dict[str, str]:
    info = _object(port.symbol_info(SYMBOL), "symbol_info")
    fields = (
        "trade_tick_size", "trade_tick_value_loss", "trade_tick_value_profit",
        "trade_contract_size", "volume_min", "volume_step", "point",
        "trade_stops_level", "trade_freeze_level", "swap_long", "swap_short",
        "swap_mode",
    )
    values = {key: _number(info.get(key), key) for key in fields}
    for key in fields[:7]:
        if __import__("decimal").Decimal(values[key]) <= 0:
            raise CaptureSafetyError(f"nonpositive USD conversion metadata {key}")
    return values


def _fee_deal(raw: Any) -> dict[str, Any]:
    # No raw IDs, login, ticket, order ID, comment, client identity or secrets.
    from decimal import Decimal

    row = _object(raw, "history_deal")
    if str(row.get("symbol", "")) != SYMBOL:
        raise CaptureSafetyError("unrelated historical deal in fee evidence")
    fields = ("volume", "commission", "swap", "fee")
    result: dict[str, Any] = {"time_msc": int(row["time_msc"])}
    for field in fields:
        if row.get(field) is None:
            raise CaptureSafetyError("fee history field missing; do not use zero")
        value = Decimal(str(row[field]))
        if not value.is_finite():
            raise CaptureSafetyError("nonfinite account-specific fee history")
        result[field] = str(value)
    return result


def collect_window(
    port: TickPort,
    contract: WindowContract,
    *,
    now_fn: Callable[[], datetime] = utc_now,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Use an injected strictly read-only port; fail closed on any incomplete slot."""
    if now_fn() > contract.start_utc or contract.start_utc - now_fn() > timedelta(minutes=5):
        raise CaptureSafetyError("not within five minutes before run window")
    _identity_and_zero(port, contract.expected_identity_sha256)
    account_begin = account_risk_snapshot(port)
    symbol_begin = symbol_cash_snapshot(port)
    observations: list[dict[str, Any]] = []
    for slot in range(SLOTS):
        target = contract.start_utc + timedelta(seconds=slot * SLOT_SECONDS)
        while (delay := (target - now_fn()).total_seconds()) > 0:
            sleep_fn(min(delay, 1))
        now = now_fn()
        if now < target or now >= target + timedelta(seconds=SLOT_SECONDS):
            raise CaptureSafetyError("missed 5s observation slot")
        # It is intentionally strict (100% if no missing), not an optimistic fill.
        observed = safe_snapshot(port, contract, now)
        observed["slot"] = slot
        observations.append(observed)
    if now_fn() < contract.end_utc:
        sleep_fn((contract.end_utc - now_fn()).total_seconds())
    if now_fn() > contract.end_utc + timedelta(seconds=5):
        raise CaptureSafetyError("capture ended late")
    _identity_and_zero(port, contract.expected_identity_sha256)
    ticks_raw = port.copy_ticks_range(
        SYMBOL, contract.start_utc, contract.end_utc, EXPECTED_TICK_FLAGS
    )
    if ticks_raw is None or len(ticks_raw) > MAX_TICKS:
        raise CaptureSafetyError("unknown/oversized MT5 tick source")
    ticks = [_tick_row(row) for row in ticks_raw]
    if not ticks:
        raise CaptureSafetyError("no genuine tick evidence")
    start_ms = int(contract.start_utc.timestamp() * 1000)
    end_ms = int(contract.end_utc.timestamp() * 1000)
    timestamps = [t["time_msc"] for t in ticks]
    if any(type(t) is not int or t < start_ms or t >= end_ms for t in timestamps):
        raise CaptureSafetyError("tick outside exact UTC run window")
    if timestamps != sorted(set(timestamps)):
        raise CaptureSafetyError("unordered or duplicate tick stamps")
    # Read 90d of ALREADY EXISTING history: an account-specific commission/swap
    # evidence candidate; no new trades. Zero existing history is NOT proof zero.
    old = contract.start_utc - timedelta(days=90)
    deals_raw = port.history_deals_get(old, contract.start_utc)
    if deals_raw is None:
        raise CaptureSafetyError("account fee history unavailable")
    fees = []
    for raw in deals_raw:
        detail = _object(raw, "history_deal")
        if detail.get("symbol") == SYMBOL:
            fees.append(_fee_deal(detail))
    _identity_and_zero(port, contract.expected_identity_sha256)
    account_end = account_risk_snapshot(port)
    symbol_end = symbol_cash_snapshot(port)
    if symbol_begin != symbol_end:
        raise CaptureSafetyError("broker symbol cash metadata changed during capture")
    return {
        "schema": "DEMO_V11_PRIVATE_READONLY_CAPTURE_V1",
        "account_before": account_begin,
        "account_after": account_end,
        "symbol_cash_metadata": symbol_begin,
        "calibration_admitted": False,
        "broker_orders_sent": 0,
        "start": contract.start_utc.isoformat(),
        "end": contract.end_utc.isoformat(),
        "registration_sha256": contract.registration_sha256,
        "symbol": SYMBOL,
        "samples": observations,
        "ticks": ticks,
        "historical_fee_deals": fees,
        "fees_evidenced": bool(fees),
        "fee_zero_proven": False,
        "swap_zero_proven": False,
    }


class MT5ReadOnlyAdapter:
    """Closed allowlist of accessors. No caller gets the raw MT5 module."""

    def __init__(self, raw: Any) -> None:
        self.__raw = raw

    def terminal_info(self) -> Any:
        return self.__raw.terminal_info()

    def account_info(self) -> Any:
        return self.__raw.account_info()

    def symbol_info(self, symbol: str) -> Any:
        return self.__raw.symbol_info(symbol)

    def symbol_info_tick(self, symbol: str) -> Any:
        return self.__raw.symbol_info_tick(symbol)

    def positions_get(self) -> Any:
        return self.__raw.positions_get()

    def orders_get(self) -> Any:
        return self.__raw.orders_get()

    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> Any:
        return self.__raw.copy_ticks_range(symbol, start, end, flags)

    def history_deals_get(self, start: datetime, end: datetime) -> Any:
        return self.__raw.history_deals_get(start, end)


def run_authorized(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-record", required=True)
    parser.add_argument("--run-record-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    # In isolated Python (-B -I) only. No module imported until all checks.
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise CaptureSafetyError("Python must run with -B -I")
    if os.name != "nt" or sys.version_info[:2] != (3, 12):
        raise CaptureSafetyError("Windows/Python3.12 required")
    if Path(sys.executable).resolve().as_posix().casefold() != (
        Path(PYTHON_EXE).resolve().as_posix().casefold()
    ):
        raise CaptureSafetyError("unapproved Python executable")

    source = Path(__file__).read_bytes()
    record = json.loads(Path(args.run_record).read_bytes())
    if not isinstance(record, dict):
        raise CaptureSafetyError("run record must be object")
    contract = validate_run_record(record, source, args.run_record_sha256)
    output = Path(args.output_dir)
    if output.exists() or output.is_symlink():
        raise CaptureSafetyError("output directory already exists: no retry")
    # Private directory only, no relative paths or existing symlink ancestors.
    if not output.is_absolute() or any(p.is_symlink() for p in output.parents):
        raise CaptureSafetyError("unsafe output path")
    if contract.start_utc < utc_now():
        raise CaptureSafetyError("run window already started; no retrospective run")
    # OS singleton/path/PID was separately checked by the Windows PS5.1 wrapper
    # immediately before launching Python; repeated immediately afterward.
    mt5 = importlib.import_module("MetaTrader5")
    if not mt5.initialize(path=TERMINAL_EXE, timeout=10000):
        raise CaptureSafetyError("read-only attachment failed closed")
    try:
        port = MT5ReadOnlyAdapter(mt5)
        _identity_and_zero(port, contract.expected_identity_sha256)
        result = collect_window(port, contract)
        # Create output ONLY after complete, verified four-hour collection.
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
        target = output / "private_evidence.json"
        with target.open("xb") as file:
            raw = canonical_json(result)
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        report = {
            "status": "RAW_CAPTURE_COMPLETE_NOT_CALIBRATION_ADMITTED",
            "private_evidence_sha256": sha256(raw),
            "run_record_sha256": args.run_record_sha256,
            "collector_sha256": sha256(source),
            "sample_count": len(result["samples"]),
            "tick_count": len(result["ticks"]),
            "fee_history_count": len(result["historical_fee_deals"]),
            "broker_actions": 0,
        }
        with (output / "manifest.json").open("xb") as file:
            file.write(canonical_json(report))
        print(json.dumps(report, sort_keys=True))
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_authorized())
