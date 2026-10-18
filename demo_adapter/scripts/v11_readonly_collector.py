"""Offline-preparable, read-only MT5 capture primitive for v1.1.

DO NOT deploy or call with a real terminal until separately approved.
This module never imports, initializes, logs into, or selects MT5.
A future separately reviewed runner must bind the approved read-only port
and exact run-specific UTC window; this module cannot place or check trades.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol


class CaptureSafetyError(ValueError):
    """Missing or invalid provenance or broker read-only response."""


class ReadOnlyMT5Port(Protocol):
    """Strictly bounded read capability supplied by a separate authorized host."""

    def terminal_info(self) -> Any: ...
    def account_info(self) -> Any: ...
    def symbol_info(self, symbol: str) -> Any: ...
    def symbol_info_tick(self, symbol: str) -> Any: ...
    def positions_get(self) -> Any: ...
    def orders_get(self) -> Any: ...
    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> Any: ...


def _object(data: Any, label: str) -> dict[str, Any]:
    if data is None:
        raise CaptureSafetyError(f"{label}: unavailable")
    if isinstance(data, dict):
        return dict(data)
    if hasattr(data, "_asdict"):
        return dict(data._asdict())
    raise CaptureSafetyError(f"{label}: not an immutable/readable record")


def _timestamp(ts: str) -> datetime:
    if not isinstance(ts, str):
        raise CaptureSafetyError("UTC timestamp is missing")
    try:
        value = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureSafetyError("bad UTC timestamp") from exc
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise CaptureSafetyError("timestamp must carry UTC offset")
    return value.astimezone(UTC)


def _sha_valid(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value
    )


@dataclass(frozen=True)
class WindowContract:
    start_utc: datetime
    end_utc: datetime
    expected_identity_sha256: str
    registration_sha256: str
    collector_source_sha256: str
    broker_session_source_sha256: str
    event_guard_source_sha256: str
    exact_owner_approval_id: str

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> WindowContract:
        # Template has all of these as null; it intentionally cannot run.
        keys = (
            "exact_window_start_utc", "exact_window_end_utc",
            "expected_demo_identity_fingerprint_sha256",
            "registration_sha256", "exact_collector_source_sha256",
            "broker_xauusd_session_source_sha256",
            "official_event_guard_health_and_event_schedule_sha256",
            "exact_owner_approval_id",
        )
        if any(record.get(key) is None for key in keys):
            raise CaptureSafetyError("incomplete prospective owner-approved run record")
        if record.get("approval_for_vps_capture") != "EXPLICIT_OWNER_APPROVED":
            raise CaptureSafetyError("no separate capture approval")
        start = _timestamp(record["exact_window_start_utc"])
        end = _timestamp(record["exact_window_end_utc"])
        if end - start != timedelta(hours=4):
            raise CaptureSafetyError("not an exact contiguous four-hour UTC window")
        digest_keys = (
            "expected_demo_identity_fingerprint_sha256",
            "registration_sha256", "exact_collector_source_sha256",
            "broker_xauusd_session_source_sha256",
            "official_event_guard_health_and_event_schedule_sha256",
        )
        if any(not _sha_valid(record.get(key)) for key in digest_keys):
            raise CaptureSafetyError("invalid source or identity digest")
        approval = record["exact_owner_approval_id"]
        if not isinstance(approval, str) or not approval.strip():
            raise CaptureSafetyError("empty owner approval identifier")
        return cls(
            start, end, record["expected_demo_identity_fingerprint_sha256"],
            record["registration_sha256"], record["exact_collector_source_sha256"],
            record["broker_xauusd_session_source_sha256"],
            record["official_event_guard_health_and_event_schedule_sha256"],
            approval,
        )


def _identity_and_zero(port: ReadOnlyMT5Port, expected_sha: str) -> dict[str, str]:
    terminal = _object(port.terminal_info(), "terminal_info")
    account = _object(port.account_info(), "account_info")
    if terminal.get("connected") is not True:
        raise CaptureSafetyError("terminal not connected")
    if terminal.get("tradeapi_disabled") is not True:
        raise CaptureSafetyError("external Python trading must remain disabled")
    # Caller must separately prove account trade_mode == MT5 DEMO enum.
    if account.get("trade_mode") != 0:
        raise CaptureSafetyError("account is not demo")
    broker = account.get("company")
    server = account.get("server")
    currency = account.get("currency")
    login = account.get("login")
    if not all(type(x) is str and x for x in (broker, server, currency)):
        raise CaptureSafetyError("broker/server/currency identity is missing")
    if type(login) is not int or login <= 0:
        raise CaptureSafetyError("account login not present for local digest")
    digest = hashlib.sha256(
        f"{broker}|{server}|{login}|{currency}".encode()
    ).hexdigest()
    if digest != expected_sha:
        raise CaptureSafetyError("account fingerprint mismatch")
    if (broker != "Exness Technologies Ltd" or server != "Exness-MT5Trial15"
            or currency != "USD"):
        raise CaptureSafetyError("unexpected account scope")
    positions = port.positions_get()
    orders = port.orders_get()
    if positions is None or orders is None:
        raise CaptureSafetyError("exposure unknown")
    if tuple(positions) or tuple(orders):
        raise CaptureSafetyError("nonzero demo exposure")
    return {"identity_sha256": digest, "external_python_trading": "DISABLED",
            "open_positions": "0", "pending_orders": "0"}


def _market(port: ReadOnlyMT5Port) -> dict[str, str]:
    info = _object(port.symbol_info("XAUUSD"), "symbol_info")
    tick = _object(port.symbol_info_tick("XAUUSD"), "symbol_info_tick")
    # Preserve strings without downcasting prices to binary float.
    for key in ("bid", "ask", "time_msc"):
        if tick.get(key) is None:
            raise CaptureSafetyError(f"missing tick {key}")
    for key in ("trade_tick_size", "trade_tick_value_loss", "trade_contract_size",
                "point", "trade_stops_level"):
        if info.get(key) is None:
            raise CaptureSafetyError(f"missing symbol {key}")
    return {
        "bid": str(tick["bid"]), "ask": str(tick["ask"]),
        "tick_time_msc": str(tick["time_msc"]),
        "tick_size": str(info["trade_tick_size"]),
        "tick_value_loss": str(info["trade_tick_value_loss"]),
        "contract_size": str(info["trade_contract_size"]),
        "point": str(info["point"]),
        "stops_level": str(info["trade_stops_level"]),
    }


def read_only_preflight(
    port: ReadOnlyMT5Port, contract: WindowContract
) -> dict[str, Any]:
    """Single deterministic mockable read; does not start a capture/runner."""
    before = _identity_and_zero(port, contract.expected_identity_sha256)
    market = _market(port)
    after = _identity_and_zero(port, contract.expected_identity_sha256)
    return {
        "schema": "demo-v11-readonly-preflight-1",
        "scope": "DEMO_LIFECYCLE_ONLY",
        "window_start_utc": contract.start_utc.isoformat(),
        "window_end_utc": contract.end_utc.isoformat(),
        "identity_before": before, "identity_after": after,
        "symbol_snapshot": market,
        "source_provenance": {
            "preregistration_sha256": contract.registration_sha256,
            "collector_sha256": contract.collector_source_sha256,
            "session_sha256": contract.broker_session_source_sha256,
            "event_guard_sha256": contract.event_guard_source_sha256,
        },
        "calibration_status": "NOT_ADMITTED",
        "broker_order_actions": 0,
    }


def canonical_sha256(data: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
