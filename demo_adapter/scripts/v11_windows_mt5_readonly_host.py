"""UNDEPLOYED future Windows read-only MT5 host for the v1.1 4-hour collector.

NEVER run without separate owner approval for the exact dated VPS capture.
There is NO trading/order method in this module. It cannot enable Python
trading, select an account, switch broker symbols, arm a permit, or submit,
check, modify, or close orders. This is not a calibration admission or
authorization token implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.v11_capture_orchestrator import rehearse_orchestrator
from scripts.v11_readonly_collector import (
    CaptureSafetyError,
    WindowContract,
    _identity_and_zero,
)

APPROVAL_TOKEN = "OWNER_APPROVED_READ_ONLY_XAUUSD_V11_CAPTURE"
SCOPED_PLATFORM = "win32"


class BoundReadOnlyMT5:
    """Only the allow-listed MT5 read calls. Never expose the module itself."""

    def __init__(self, source: Any) -> None:
        self._source = source

    def terminal_info(self) -> Any:
        return self._source.terminal_info()

    def account_info(self) -> Any:
        return self._source.account_info()

    def positions_get(self) -> Any:
        return self._source.positions_get()

    def orders_get(self) -> Any:
        return self._source.orders_get()

    def symbol_info(self, symbol: str) -> Any:
        if symbol != "XAUUSD":
            raise CaptureSafetyError("non-XAUUSD symbol query forbidden")
        return self._source.symbol_info(symbol)

    def symbol_info_tick(self, symbol: str) -> Any:
        if symbol != "XAUUSD":
            raise CaptureSafetyError("non-XAUUSD symbol query forbidden")
        return self._source.symbol_info_tick(symbol)

    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> Any:
        if symbol != "XAUUSD" or flags != int(self._source.COPY_TICKS_ALL):
            raise CaptureSafetyError("non-allowlisted MT5 tick read")
        return self._source.copy_ticks_range(symbol, start, end, flags)


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_registration(
    path: Path, expected_sha: str, expected_script_sha: str
) -> WindowContract:
    if (len(expected_sha) != 64 or len(expected_script_sha) != 64
            or not all(c in "0123456789abcdef" for c in
                       expected_sha + expected_script_sha)):
        raise CaptureSafetyError("independently supplied hashes missing")
    contents = path.read_bytes()
    if _hash(contents) != expected_sha:
        raise CaptureSafetyError("exact registered run file hash mismatch")
    if _hash(Path(__file__).read_bytes()) != expected_script_sha:
        raise CaptureSafetyError("reviewed Windows host source hash mismatch")
    try:
        record = json.loads(contents)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CaptureSafetyError("run registration is not JSON") from exc
    if not isinstance(record, dict):
        raise CaptureSafetyError("invalid run registration root")
    if record.get("owner_capture_decision") != APPROVAL_TOKEN:
        raise CaptureSafetyError("run has no explicit separate owner decision")
    if record.get("output_scope") != "PRIVATE_LOCAL_EXXESS_DEMO_ONLY":
        raise CaptureSafetyError("private output scope not registered")
    contract = WindowContract.from_record(record)
    if contract.start_utc.weekday() >= 5:
        raise CaptureSafetyError("weekend/reopen observation not eligible")
    if contract.end_utc - contract.start_utc != timedelta(hours=4):
        raise CaptureSafetyError("four-hour target missing")
    # No statement that a caller-filled string authenticates independent
    # owners, brokers, Event Guard, clocks, or research coverage.
    return contract


def _private_write(path: Path, payload: dict[str, Any]) -> str:
    # Do not write private broker data into repository or replace evidence.
    dest = path.resolve()
    repository = Path(__file__).resolve().parents[2]
    if dest == repository or repository in dest.parents:
        raise CaptureSafetyError("private raw evidence cannot live in repository")
    if not dest.parent.exists():
        raise CaptureSafetyError("private output directory must pre-exist")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(dest, flags, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    return _hash(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DO NOT RUN without separately approved Windows read-only VPS capture"
    )
    parser.add_argument("--exact-registration-json", type=Path, required=True)
    parser.add_argument("--expected-registration-sha256", required=True)
    parser.add_argument("--expected-host-source-sha256", required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--separate-owner-approval", required=True)
    args = parser.parse_args(argv)

    # This intentionally requires a future *specific* authorization. No
    # binary can independently tell whether the owner actually granted it.
    if args.separate_owner_approval != APPROVAL_TOKEN:
        raise CaptureSafetyError("separate owner capture approval not supplied")
    if sys.platform != SCOPED_PLATFORM:
        raise CaptureSafetyError("real MT5 read-only host is Windows-only")
    contract = _read_registration(
        args.exact_registration_json,
        args.expected_registration_sha256,
        args.expected_host_source_sha256,
    )
    if not contract.exact_owner_approval_id.strip():
        raise CaptureSafetyError("run ID not approved")
    if args.private_output.exists():
        raise CaptureSafetyError("immutable private evidence destination exists")

    now = datetime.now(UTC)
    if now > contract.start_utc or contract.start_utc - now > timedelta(minutes=5):
        raise CaptureSafetyError("must start within 5 min before exact registered window")

    # The only dynamic import is here, after strict offline config/time gates.
    # initialize attaches the existing terminal; it never logs into or
    # switches accounts. Terminal identity and tradeapi_disabled are checked
    # before the first broker quote and again through the capture lifecycle.
    mt5 = importlib.import_module("MetaTrader5")
    if not bool(mt5.initialize()):
        raise CaptureSafetyError("existing MT5 terminal read initialization failed")
    try:
        port = BoundReadOnlyMT5(mt5)
        _identity_and_zero(port, contract.expected_identity_sha256)
        result = rehearse_orchestrator(
            port, contract, now_utc=lambda: datetime.now(UTC),
            sleep_seconds=time.sleep,
            copy_ticks_all_flags=int(mt5.COPY_TICKS_ALL),
        )
        payload = {
            "scope": "DEMO_LIFECYCLE_ONLY",
            "status": "RAW_READ_ONLY_QUOTE_EVIDENCE_NOT_CALIBRATION",
            "registered_window_start": contract.start_utc.isoformat(),
            "registered_window_end": contract.end_utc.isoformat(),
            "registration_sha256": args.expected_registration_sha256,
            "host_sha256": args.expected_host_source_sha256,
            "polls_sha256": result.polls_sha256,
            "ticks_sha256": result.ticks_sha256,
            "coverage": asdict(result.coverage),
            "polls": [asdict(x) for x in result.polls],
            "ticks": [asdict(x) for x in result.ticks],
        }
        digest = _private_write(args.private_output, payload)
        # Print only SHA and classification, not identity or private quotes.
        print("PRIVATE_RAW_SHA256=" + digest)
        print("READ_ONLY_QUOTE_EVIDENCE_NOT_CALIBRATION_ADMITTED")
        return 0
    finally:
        # This shuts down the Python MT5 connection only; it does NOT change
        # broker positions, MT5 application state, or task scheduling.
        mt5.shutdown()


if __name__ == "__main__":
    # This main exists solely for a later owner-approved, exact-file Windows
    # execution. CI tests never call it and never connect to MT5.
    raise SystemExit(main())
