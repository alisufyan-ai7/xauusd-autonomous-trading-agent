"""UNDEPLOYED v1.2 read-only Exness XAUUSD evidence host.

Requires prospective owner-confirmed source-hash-pinned UTC packet. Never
invoke before owner first-run confirmation. NO order, margin calc, trading
configuration or account switch methods are invoked. NOTE MT5.initialize()
may launch a terminal; controlling PowerShell must attest an ALREADY RUNNING
exact terminal process before this code is reached. Still requires supervision.
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
    CaptureSafetyError, WindowContract, _identity_and_zero, _market, _timestamp,
)
from scripts.v11_windows_mt5_readonly_host import BoundReadOnlyMT5, _private_write

DESIGN_SHA = "847829378956670e8936bf46c82e685de41145fd"
PREP_SHA = "9d768fcfd160b3ccfc92ecef44fe040da6b77db6"
APPROVAL_MODE = "EXPLICIT_OWNER_APPROVED"
EXPECTED_IDENTITY = "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91"


def _hex(v: Any) -> bool:
    return type(v) is str and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _read_verified(path: Path, digest: str) -> dict[str, Any]:
    if not _hex(digest) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise CaptureSafetyError("prospective JSON registration SHA mismatch")
    try:
        item = json.loads(path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise CaptureSafetyError("registration not valid UTF-8 JSON") from exc
    if type(item) is not dict:
        raise CaptureSafetyError("registration object missing")
    return item


def _preregistered(record: dict[str, Any], owner_run_id: str) -> WindowContract:
    if (record.get("approved_pr13_design_sha") != DESIGN_SHA
            or record.get("approved_pr14_evidence_sha") != PREP_SHA
            or record.get("approval_for_vps_capture") != APPROVAL_MODE
            or record.get("owner_capture_decision") != "OWNER_APPROVED_READ_ONLY_XAUUSD_V11_CAPTURE"
            or record.get("exact_owner_approval_id") != owner_run_id
            or record.get("owner_first_run_confirmation_id") != owner_run_id
            or not owner_run_id or owner_run_id == "PENDING"
            or record.get("output_scope") != "PRIVATE_LOCAL_EXNESS_DEMO_ONLY"):
        raise CaptureSafetyError("owner exact-run scope and source lineage not approved")
    contract = WindowContract.from_record(record)
    if contract.expected_identity_sha256 != EXPECTED_IDENTITY:
        raise CaptureSafetyError("frozen demo account identity pin mismatch")
    overlap_start = _timestamp(record.get("v12_overlap_start_utc"))
    overlap_end = _timestamp(record.get("v12_overlap_end_utc"))
    if not contract.start_utc <= overlap_start < overlap_end <= contract.end_utc:
        raise CaptureSafetyError("v1.2 overlap is not entirely within 4h")
    if (record.get("calibration_status") != "NOT_ADMITTED"
            or record.get("tradeapi_disabled_required") is not True
            or record.get("known_positions_zero_required") is not True):
        raise CaptureSafetyError("calibration/trading authority escape")
    for required in (
        "holiday_dst_sha256", "bls_sha256", "bea_sha256",
        "fed_sha256", "census_sha256", "dol_sha256",
        "symbol_and_fee_source_sha256", "pre_demo_slippage_proxy_sha256",
        "gap_proxy_sha256", "independent_source_origin_review_sha256",
        "collector_ps_sha256", "verifier_ps_sha256",
        "risk_source_sha256", "read_only_core_source_sha256",
    ):
        if not _hex(record.get(required)):
            raise CaptureSafetyError("unverified official/broker/implementation source: " + required)
    if record.get("source_origin_review_is_not_hash_authentication") is not True:
        raise CaptureSafetyError("source-origin verification disclaimer missing")
    if (record.get("real_window_prospective_frozen") is not True
            or record.get("xauusd_date_specific_open_full") is not True
            or record.get("event_guard_healthy_now") is not True
            or record.get("window_no_blocked_events_verified") is not True
            or record.get("owner_validated_private_destination") is not True):
        raise CaptureSafetyError("session, guard or private destination not verified")
    return contract


def _summary(port: BoundReadOnlyMT5, expected_sha: str) -> dict[str, Any]:
    identity = _identity_and_zero(port, expected_sha)
    account = port.account_info()
    symbol = port.symbol_info("XAUUSD")
    terminal = port.terminal_info()
    if account is None or symbol is None or terminal is None:
        raise CaptureSafetyError("unknown account/symbol/terminal")
    a = account._asdict()
    s = symbol._asdict()
    t = terminal._asdict()
    # Keep account secret and unrelated terminal paths out of evidence.
    return {
        "demo_identity_sha256": identity["identity_sha256"],
        "utc_observed": datetime.now(UTC).isoformat(),
        "external_python_trading_disabled": bool(t.get("tradeapi_disabled")),
        "connected": bool(t.get("connected")),
        "balance": str(a.get("balance")), "equity": str(a.get("equity")),
        "margin": str(a.get("margin")),
        "margin_free": str(a.get("margin_free")),
        "currency": str(a.get("currency")),
        "symbol": "XAUUSD",
        "contract_size": str(s.get("trade_contract_size")),
        "tick_size": str(s.get("trade_tick_size")),
        "tick_loss_value": str(s.get("trade_tick_value_loss")),
        "tick_profit_value": str(s.get("trade_tick_value_profit")),
        "volume_min": str(s.get("volume_min")),
        "volume_max": str(s.get("volume_max")),
        "volume_step": str(s.get("volume_step")),
        "trade_stops_level": str(s.get("trade_stops_level")),
        "trade_freeze_level": str(s.get("trade_freeze_level")),
        "swap_long": str(s.get("swap_long")),
        "swap_short": str(s.get("swap_short")),
        "swap_mode": str(s.get("swap_mode")),
        "spread": str(s.get("spread")),
        "trade_mode": str(s.get("trade_mode")),
    }


def _history(mt5: Any, start: datetime, end: datetime) -> dict[str, Any]:
    # Only read this account's XAUUSD deals, not other symbols' trades.
    rows = mt5.history_deals_get(start - timedelta(days=7), end, group="XAUUSD")
    if rows is None:
        raise CaptureSafetyError("broker XAUUSD deal history inaccessible")
    return {
        "status": "READ_ONLY_ACCOUNT_SPECIFIC_HISTORY_NOT_RECONCILED",
        "window_start_utc": (start - timedelta(days=7)).isoformat(),
        "window_end_utc": end.isoformat(),
        "deal_count": len(rows),
        "deals": [
            {"timestamp_s": int(r.time), "symbol": str(r.symbol),
             "profit": str(r.profit), "commission": str(r.commission),
             "swap": str(r.swap), "fee": str(getattr(r, "fee", "UNKNOWN")),
             "volume": str(r.volume), "entry": int(r.entry),
             "type": int(r.type)}
            for r in rows if str(r.symbol) == "XAUUSD"
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OWNER-CONFIRMED ONLY — no broker orders")
    p.add_argument("--registration", type=Path, required=True)
    p.add_argument("--registration-sha256", required=True)
    p.add_argument("--host-sha256", required=True)
    p.add_argument("--owner-run-id", required=True)
    p.add_argument("--terminal-path", type=Path, required=True)
    p.add_argument("--private-output", type=Path, required=True)
    x = p.parse_args(argv)
    if sys.platform != "win32":
        raise CaptureSafetyError("Windows read-only scope only")
    if not _hex(x.host_sha256) or hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != x.host_sha256:
        raise CaptureSafetyError("host source not independently pinned")
    record = _read_verified(x.registration, x.registration_sha256)
    contract = _preregistered(record, x.owner_run_id)
    if not x.terminal_path.is_file() or x.terminal_path.name.lower() != "terminal64.exe":
        raise CaptureSafetyError("exact already-open terminal path missing")
    if x.private_output.exists() or not x.private_output.parent.is_dir():
        raise CaptureSafetyError("immutable private destination precondition failed")
    now = datetime.now(UTC)
    if not timedelta(0) <= contract.start_utc - now <= timedelta(minutes=5):
        raise CaptureSafetyError("run outside separately approved five-minute prewindow")
    # Call path explicitly, NO login/password/server inputs or configuration.
    mt5 = importlib.import_module("MetaTrader5")
    if not bool(mt5.initialize(str(x.terminal_path))):
        raise CaptureSafetyError("MT5 read-only attach failed")
    try:
        port = BoundReadOnlyMT5(mt5)
        before = _summary(port, contract.expected_identity_sha256)
        _market(port)
        result = rehearse_orchestrator(
            port, contract, now_utc=lambda: datetime.now(UTC),
            sleep_seconds=time.sleep, copy_ticks_all_flags=int(mt5.COPY_TICKS_ALL),
        )
        after = _summary(port, contract.expected_identity_sha256)
        raw = {
            "status": "RAW_PRIVATE_READ_ONLY_NOT_CALIBRATION_OR_EXECUTION",
            "registration_sha256": x.registration_sha256,
            "host_sha256": x.host_sha256,
            "window_start_utc": contract.start_utc.isoformat(),
            "window_end_utc": contract.end_utc.isoformat(),
            "v12_overlap_start_utc": record["v12_overlap_start_utc"],
            "v12_overlap_end_utc": record["v12_overlap_end_utc"],
            "account_before": before,
            "account_after": after,
            "symbol_snapshot": _market(port),
            "history": _history(mt5, contract.start_utc, contract.end_utc),
            "polls_sha256": result.polls_sha256,
            "ticks_sha256": result.ticks_sha256,
            "polls": [asdict(v) for v in result.polls],
            "ticks": [asdict(v) for v in result.ticks],
            "coverage": asdict(result.coverage),
            "actual_execution_slippage_measured": False,
            "numeric_costs_admitted": False,
            "order_actions": 0,
        }
        digest = _private_write(x.private_output, raw)
        print("PRIVATE_RAW_SHA256=" + digest)
        print("READ_ONLY_RAW_EVIDENCE_ONLY_NOT_CALIBRATION_ADMITTED")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
