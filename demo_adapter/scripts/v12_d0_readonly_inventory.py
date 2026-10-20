"""D0 SOURCE DISCOVERY ONLY — never v1.2 qualifying 240-minute capture.

Permitted MT5 methods: initialize(existing confirmed terminal), terminal_info,
account_info, positions_get, orders_get, symbol_info(XAUUSD),
symbol_info_tick(XAUUSD), shutdown. NO order*, history or configuration calls.
Caller owns run approval and private directory; evidence may discover facts but
is not an authenticated source/session/Event Guard, calibration or trade permit.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.v12_attempt_journal import AttemptJournal, attempt_path

EXPECTED_DESIGN = "847829378956670e8936bf46c82e685de41145fd"
EXPECTED_V12_BLOB = "c7dcf520fe2a3b12437cec6a1b5dd06c25494d5f"
EXPECTED_IDENTITY = "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"


class DiscoveryBlocked(ValueError):
    pass


def _sha(s: object) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(
        x in "0123456789abcdef" for x in s
    )


def _row(value: Any, label: str) -> dict[str, Any]:
    if hasattr(value, "_asdict"):
        value = value._asdict()
    if not isinstance(value, dict):
        raise DiscoveryBlocked("missing " + label)
    return value


def _identity(mt5: Any) -> dict[str, Any]:
    terminal = _row(mt5.terminal_info(), "terminal")
    account = _row(mt5.account_info(), "account")
    if terminal.get("connected") is not True:
        raise DiscoveryBlocked("terminal disconnected")
    if terminal.get("tradeapi_disabled") is not True:
        raise DiscoveryBlocked("external Python trading is not disabled")
    if account.get("trade_mode") != 0:
        raise DiscoveryBlocked("not MT5 DEMO")
    broker = account.get("company")
    server = account.get("server")
    currency = account.get("currency")
    login = account.get("login")
    if not all(isinstance(z, str) and z for z in (broker, server, currency)):
        raise DiscoveryBlocked("unverifiable company/server/currency")
    if type(login) is not int or login <= 0:
        raise DiscoveryBlocked("account login missing")
    digest = hashlib.sha256(
        f"{broker}|{server}|{login}|{currency}".encode()
    ).hexdigest()
    if digest != EXPECTED_IDENTITY:
        raise DiscoveryBlocked("unadmitted account fingerprint")
    if (
        broker != "Exness Technologies Ltd"
        or server != "Exness-MT5Trial15"
        or currency != "USD"
    ):
        raise DiscoveryBlocked("nonadmitted Exness DEMO identity")
    positions = mt5.positions_get()
    pending = mt5.orders_get()
    if positions is None or pending is None:
        raise DiscoveryBlocked("unknown positions/orders")
    if tuple(positions) or tuple(pending):
        raise DiscoveryBlocked("nonzero positions/orders")
    return {
        "identity_sha256": digest,
        "account_mode": "DEMO",
        "account_currency": currency,
        "exness_company": broker,
        "exness_server": server,
        "external_python_trading_disabled": True,
        "known_positions": 0,
        "known_pending_orders": 0,
    }


SYMBOL_KEYS = (
    "name", "visible", "select", "trade_mode", "trade_calc_mode",
    "trade_contract_size", "trade_tick_size", "trade_tick_value",
    "trade_tick_value_profit", "trade_tick_value_loss",
    "currency_base", "currency_profit", "currency_margin",
    "volume_min", "volume_max", "volume_step", "point",
    "trade_stops_level", "trade_freeze_level",
    "swap_mode", "swap_long", "swap_short", "swap_rollover3days",
    "spread", "spread_float", "digits", "time", "start_time",
    "expiration_time",
)
TICK_KEYS = ("time", "time_msc", "bid", "ask", "last", "volume", "flags")


def observe_only(mt5: Any) -> dict[str, Any]:
    """Mockable single, bounded source discovery; NO symbol_select or orders."""
    before = _identity(mt5)
    observed = datetime.now(UTC)
    info = _row(mt5.symbol_info("XAUUSD"), "XAUUSD symbol")
    tick_obj = mt5.symbol_info_tick("XAUUSD")
    tick = _row(tick_obj, "XAUUSD tick") if tick_obj is not None else None
    after = _identity(mt5)
    if before != after:
        raise DiscoveryBlocked("account/exposure changed across diagnostic")
    if info.get("name") != "XAUUSD":
        raise DiscoveryBlocked("exact symbol mismatch")
    return {
        "mode": "D0_ONLY_ONE_READ_NO_FOUR_HOUR_COHORT",
        "captured_utc": observed.isoformat(),
        "account": before,
        "symbol": {k: str(info[k]) if info.get(k) is not None else None
                   for k in SYMBOL_KEYS},
        "tick": {k: str(tick[k]) if tick.get(k) is not None else None
                 for k in TICK_KEYS} if tick is not None else None,
        "session_interpretation": "NOT_ADMITTED_SYMBOL_TRADE_MODE_AND_ONE_QUOTE_NOT_PROOF_OF_FOUR_HOURS",
        "actual_current_stressed_costs_admitted": False,
        "trading_orders_permitted": False,
        "event_guard_health_known": False,
        "real_execution_slippage_measured": False,
        "actual_broker_commission_verified": False,
        "order_actions": 0,
    }


def _private_write_exclusive(target: Path, data: dict[str, Any]) -> str:
    payload = (json.dumps(data, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_BINARY", 0), 0o600)
    try:
        if os.write(fd, payload) != len(payload):
            raise DiscoveryBlocked("private evidence short write")
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(payload).hexdigest()


def run(args: argparse.Namespace) -> int:
    if sys.platform != "win32":
        raise DiscoveryBlocked("Windows MT5 diagnostic only")
    host_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if not _sha(args.host_sha256) or host_sha != args.host_sha256:
        raise DiscoveryBlocked("self SHA pin mismatch")
    registration_bytes = args.registration.read_bytes()
    reg_sha = hashlib.sha256(registration_bytes).hexdigest()
    if not _sha(args.registration_sha256) or reg_sha != args.registration_sha256:
        raise DiscoveryBlocked("prospective D0 registration hash invalid")
    try:
        contract = json.loads(registration_bytes)
    except (ValueError, UnicodeError) as exc:
        raise DiscoveryBlocked("registration malformed") from exc
    if (
        contract.get("mode") != "D0_SOURCE_DISCOVERY_SINGLE_SNAPSHOT_ONLY"
        or contract.get("approved_pr13_sha") != EXPECTED_DESIGN
        or contract.get("approved_v12_prereg_git_blob") != EXPECTED_V12_BLOB
        or contract.get("expected_demo_fingerprint_sha256") != EXPECTED_IDENTITY
        or contract.get("host_sha256") != host_sha
        or contract.get("attempt_journal_sha256") != args.attempt_journal_sha256
        or contract.get("broker_trading_allowed") is not False
        or contract.get("four_hour_capture_allowed") is not False
        or contract.get("actual_cost_admission_allowed") is not False
        or contract.get("vps_mt5_execution_authorized_in_git") is not False
    ):
        raise DiscoveryBlocked("D0 contract invalid or authority broadened")
    if not args.owner_d0_confirmed:
        raise DiscoveryBlocked("separate owner D0 run confirmation required")
    if not args.terminal.is_file() or args.terminal.name.lower() != "terminal64.exe":
        raise DiscoveryBlocked("already-running exact terminal not found")
    root = Path(__file__).resolve().parents[2]
    private_dir = args.private_dir.resolve()
    if not private_dir.is_dir() or root == private_dir or root in private_dir.parents:
        raise DiscoveryBlocked("private evidence directory unavailable/outside worktree required")
    if not _sha(args.attempt_journal_sha256):
        raise DiscoveryBlocked("journal source hash missing")
    journal_src = Path(__file__).with_name("v12_attempt_journal.py")
    if hashlib.sha256(journal_src.read_bytes()).hexdigest() != args.attempt_journal_sha256:
        raise DiscoveryBlocked("journal source hash mismatch")
    ledger_path = attempt_path(private_dir, args.registration_sha256)
    if ledger_path.exists():
        raise DiscoveryBlocked("same registration already attempted")
    journal = AttemptJournal(
        ledger_path, args.registration_sha256,
        "D0_SINGLE_SNAPSHOT_SOURCE_DISCOVERY_NOT_4H_V12_CAPTURE",
    )
    initialized = False
    mt5: Any = None
    try:
        journal.append("ATTACH_REQUESTED", {
            "read_only": True, "terminal_name": "terminal64.exe",
            "actual_4h_capture": False, "order_actions": 0,
        })
        mt5 = importlib.import_module("MetaTrader5")
        if not mt5.initialize(str(args.terminal)):
            raise DiscoveryBlocked("existing-terminal read-only attachment failed")
        initialized = True
        record = observe_only(mt5)
        record["registration_sha256"] = args.registration_sha256
        record["source_host_sha256"] = host_sha
        record["attempt_journal_filename"] = ledger_path.name
        # No trading calls or session/cost admission. This is just inventory.
        digest = _private_write_exclusive(
            private_dir / ("v12-d0-inventory-" + args.registration_sha256 + ".json"),
            record,
        )
        journal.append("PRIVATE_INVENTORY_RAW_SHA256", {"sha256": digest})
        mt5.shutdown()
        initialized = False
        journal.success(digest)
        print("D0_RAW_INVENTORY_SHA256=" + digest)
        print("D0_PRIVATE_JOURNAL_FILENAME=" + ledger_path.name)
        print("D0_NOT_4H_CAPTURE_NOT_SOURCE_ADMISSION_NOT_TRADING")
        return 0
    except BaseException as exc:
        try:
            journal.failed(type(exc).__name__)
        except BaseException:
            print("D0_INCOMPLETE_FAIL_CLOSED_JOURNAL", file=sys.stderr)
        raise
    finally:
        if initialized and mt5 is not None:
            try:
                mt5.shutdown()
            except BaseException:
                print("D0_MT5_SHUTDOWN_UNKNOWN", file=sys.stderr)
        journal.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D0 only, owner-gated offline source discovery")
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--host-sha256", required=True)
    parser.add_argument("--attempt-journal-sha256", required=True)
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--owner-d0-confirmed", action="store_true")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
