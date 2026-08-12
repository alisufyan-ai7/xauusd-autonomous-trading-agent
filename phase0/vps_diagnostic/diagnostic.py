"""Append-only, read-only XAUUSD session/VPS observer.

The program never sends, checks, modifies or cancels an order. It attaches to the
already-open terminal without credentials and requires tradeapi_disabled=True.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import platform
import secrets
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from readonly_mt5 import ReadOnlyMT5

VERSION = "0.2.3"
MANIFEST = "PACKAGE_MANIFEST.sha256"


class SafeStop(RuntimeError):
    pass


def plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "_asdict"):
        return {str(k): plain(v) for k, v in value._asdict().items()}
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return str(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(base: Path) -> None:
    path = base / MANIFEST
    if not path.is_file():
        raise SafeStop("package manifest missing")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        target = (base / relative).resolve()
        if target.parent != base.resolve() or not target.is_file():
            raise SafeStop(f"invalid package path: {relative}")
        if not hmac.compare_digest(expected, sha256_file(target)):
            raise SafeStop(f"package hash mismatch: {relative}")


class Redactor:
    def __init__(self) -> None:
        self.key = secrets.token_bytes(32)

    def token(self, namespace: str, value: Any) -> str:
        return "hmac-sha256:" + hmac.new(
            self.key, f"{namespace}:{value}".encode(), hashlib.sha256
        ).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def required_guard(api: Any) -> dict[str, Any]:
    terminal = plain(api.terminal_info())
    if not isinstance(terminal, dict):
        raise SafeStop(f"terminal_info unavailable: {api.last_error()}")
    if terminal.get("tradeapi_disabled") is not True:
        raise SafeStop("external Python trading is not disabled")
    return terminal


def fingerprint(api: Any, symbol: str, redactor: Redactor) -> dict[str, Any]:
    terminal = required_guard(api)
    account = plain(api.account_info())
    info = plain(api.symbol_info(symbol))
    if not isinstance(account, dict) or not isinstance(info, dict):
        raise SafeStop(f"account or symbol unavailable: {api.last_error()}")
    return {
        "account": redactor.token("account", account.get("login")),
        "server": redactor.token("server", account.get("server")),
        "company": account.get("company"),
        "currency": account.get("currency"),
        "trade_mode": account.get("trade_mode"),
        "margin_mode": account.get("margin_mode"),
        "terminal_build": terminal.get("build"),
        "terminal_version": plain(api.version()),
        "symbol": symbol,
    }


def symbol_conditions(api: Any, symbol: str) -> dict[str, Any]:
    """Capture broker conditions as observations, never as account identity.

    These properties may legitimately change at a session boundary or when the
    broker updates instrument conditions.  Their changes are evidence, not a
    reason to misclassify the account/terminal identity as having drifted.
    """
    info = plain(api.symbol_info(symbol))
    if not isinstance(info, dict):
        raise SafeStop(f"symbol unavailable: {api.last_error()}")
    return {k: info.get(k) for k in (
        "digits", "point", "trade_mode", "trade_exemode", "filling_mode",
        "order_mode", "order_gtc_mode", "trade_calc_mode", "trade_contract_size",
        "trade_tick_size", "trade_tick_value", "trade_tick_value_profit",
        "trade_tick_value_loss", "volume_min", "volume_max", "volume_step",
        "volume_limit", "trade_stops_level", "trade_freeze_level", "spread",
        "spread_float", "swap_mode", "swap_long", "swap_short",
        "swap_rollover3days", "currency_base", "currency_profit", "currency_margin"
    )}


def append_record(handle, record: dict[str, Any], prior_hash: str) -> str:
    record["prior_record_sha256"] = prior_hash
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(encoded).hexdigest()
    handle.write(encoded.decode())
    handle.flush()
    os.fsync(handle.fileno())
    return digest


def run(api: Any, output: Path, symbol: str, duration: int, interval: float) -> dict[str, Any]:
    if duration < 1 or interval <= 0:
        raise SafeStop("duration and interval must be positive")
    if output.exists():
        raise SafeStop("refusing to overwrite output directory")
    output.mkdir(parents=True)
    redactor = Redactor()
    if not api.initialize():
        raise SafeStop(f"MT5 attach failed: {api.last_error()}")
    start_mono = time.monotonic()
    boot_id = str(uuid.uuid4())
    prior = "0" * 64
    sequence = 0
    baseline = None
    stop_reason = "duration_complete"
    observations = output / "observations.jsonl"
    try:
        baseline = fingerprint(api, symbol, redactor)
        baseline_hash = hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
        (output / "fingerprint.json").write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        prior_conditions = None
        with observations.open("x", encoding="utf-8", newline="\n") as handle:
            while time.monotonic() - start_mono < duration:
                scheduled = time.monotonic()
                terminal = required_guard(api)
                current = fingerprint(api, symbol, redactor)
                current_hash = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
                if current_hash != baseline_hash:
                    stop_reason = "fingerprint_drift"
                    raise SafeStop(stop_reason)
                conditions = symbol_conditions(api, symbol)
                conditions_hash = hashlib.sha256(json.dumps(conditions, sort_keys=True).encode()).hexdigest()
                conditions_changed = prior_conditions is not None and conditions != prior_conditions
                tick = plain(api.symbol_info_tick(symbol))
                receipt = datetime.now(timezone.utc)
                tick_epoch = tick.get("time_msc", 0) / 1000 if isinstance(tick, dict) else 0
                tick_age = receipt.timestamp() - tick_epoch if tick_epoch else None
                connected = terminal.get("connected") is True
                fresh = connected and tick_age is not None and -2 <= tick_age <= max(30.0, interval * 3)
                record = {
                    "schema": "gate0-vps-observation-1.0",
                    "version": VERSION,
                    "boot_id": boot_id,
                    "sequence": sequence,
                    "observed_utc": utc(),
                    "monotonic_seconds": round(time.monotonic() - start_mono, 6),
                    "connected": connected,
                    "tradeapi_disabled": True,
                    "health": "HEALTHY" if fresh else "UNHEALTHY",
                    "tick_time_msc": tick.get("time_msc") if isinstance(tick, dict) else None,
                    "bid": tick.get("bid") if isinstance(tick, dict) else None,
                    "ask": tick.get("ask") if isinstance(tick, dict) else None,
                    "spread_price": (tick.get("ask") - tick.get("bid")) if isinstance(tick, dict) and isinstance(tick.get("ask"), (int, float)) and isinstance(tick.get("bid"), (int, float)) else None,
                    "symbol_conditions": conditions,
                    "symbol_conditions_sha256": conditions_hash,
                    "symbol_conditions_changed": conditions_changed,
                    "tick_age_seconds": round(tick_age, 3) if tick_age is not None else None,
                    "deadline_lateness_seconds": round(max(0.0, time.monotonic() - scheduled), 6),
                }
                prior = append_record(handle, record, prior)
                prior_conditions = conditions
                sequence += 1
                remaining = interval - (time.monotonic() - scheduled)
                if remaining > 0:
                    time.sleep(remaining)
        required_guard(api)
    finally:
        api.shutdown()
    summary = {
        "status": "PASS" if stop_reason == "duration_complete" else "FAIL",
        "version": VERSION,
        "symbol": symbol,
        "started_utc": datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - (time.monotonic() - start_mono), timezone.utc).isoformat(),
        "ended_utc": utc(),
        "observation_count": sequence,
        "final_record_sha256": prior,
        "stop_reason": stop_reason,
        "claim_limit": "Observation evidence only; this run cannot authorize trading or prove a complete weekly session schedule.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--duration-seconds", type=int, default=86400)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    args = parser.parse_args()
    try:
        verify_manifest(Path(__file__).resolve().parent)
        result = run(ReadOnlyMT5, args.output, args.symbol, args.duration_seconds, args.interval_seconds)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "PASS" else 2
    except SafeStop as exc:
        print(f"SAFE STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
