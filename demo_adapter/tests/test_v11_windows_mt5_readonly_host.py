"""Synthetic and static tests; NEVER execute the broker-facing host main."""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.v11_readonly_collector import CaptureSafetyError
from scripts import v11_windows_mt5_readonly_host as host


def document() -> dict[str, Any]:
    login_hash = hashlib.sha256(
        b"Exness Technologies Ltd|Exness-MT5Trial15|12345678|USD"
    ).hexdigest()
    return {
        "exact_window_start_utc": "2026-10-19T13:00:00Z",
        "exact_window_end_utc": "2026-10-19T17:00:00Z",
        "expected_demo_identity_fingerprint_sha256": login_hash,
        "registration_sha256": "1" * 64,
        "exact_collector_source_sha256": "2" * 64,
        "broker_xauusd_session_source_sha256": "3" * 64,
        "official_event_guard_health_and_event_schedule_sha256": "4" * 64,
        "exact_owner_approval_id": "SYNTHETIC_TEST_NOT_REAL_OWNER_APPROVAL",
        "approval_for_vps_capture": "EXPLICIT_OWNER_APPROVED",
        "owner_capture_decision": host.APPROVAL_TOKEN,
        "output_scope": "PRIVATE_LOCAL_EXNESS_DEMO_ONLY",
    }


def stored(tmp_path: Path, record: dict[str, Any]) -> tuple[Path, str, str]:
    path = tmp_path / "synthetic_window.json"
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    host_digest = hashlib.sha256(Path(host.__file__).read_bytes()).hexdigest()
    return path, digest, host_digest


def test_synthetic_future_record_is_parseable_but_not_approval(
    tmp_path: Path,
) -> None:
    path, digest, source = stored(tmp_path, document())
    result = host._read_registration(path, digest, source)
    assert result.end_utc - result.start_utc == timedelta(hours=4)
    assert result.exact_owner_approval_id.startswith("SYNTHETIC")


@pytest.mark.parametrize(("field", "value"), [
    ("approval_for_vps_capture", "REQUIRED_SEPARATELY"),
    ("owner_capture_decision", "NOT_APPROVED"),
    ("output_scope", "PUBLIC_REPO"),
    ("exact_window_end_utc", "2026-10-19T18:00:00Z"),
    ("exact_window_start_utc", "2026-10-18T13:00:00Z"),
])
def test_incomplete_or_wrong_owner_scope_blocks_record(
    tmp_path: Path, field: str, value: str,
) -> None:
    record = document()
    record[field] = value
    path, digest, source = stored(tmp_path, record)
    with pytest.raises(CaptureSafetyError):
        host._read_registration(path, digest, source)


def test_modified_registration_or_host_pin_blocks(
    tmp_path: Path,
) -> None:
    path, digest, source = stored(tmp_path, document())
    with pytest.raises(CaptureSafetyError, match="file hash mismatch"):
        host._read_registration(path, "f" * 64, source)
    with pytest.raises(CaptureSafetyError, match="host source hash mismatch"):
        host._read_registration(path, digest, "f" * 64)


def test_private_output_is_exclusive_and_hashes_exact_bytes(tmp_path: Path) -> None:
    filename = tmp_path / "private_synthetic.json"
    digest = host._private_write(
        filename, {"status": "REPLAY_ONLY", "value": "2000.20"}
    )
    assert filename.exists()
    assert hashlib.sha256(filename.read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        host._private_write(filename, {"status": "REPLAY_ONLY"})


def test_broker_port_exposes_only_explicit_read_facade() -> None:
    class FakeMetaTrader:
        COPY_TICKS_ALL = 1

        def __getattr__(self, name: str) -> object:
            if name in ("terminal_info", "account_info", "positions_get",
                        "orders_get", "symbol_info", "symbol_info_tick",
                        "copy_ticks_range"):
                return lambda *args: SimpleNamespace(name=name, args=args)
            raise AssertionError("not a permitted API: " + name)

    port = host.BoundReadOnlyMT5(FakeMetaTrader())
    assert port.terminal_info().name == "terminal_info"
    assert port.symbol_info("XAUUSD").name == "symbol_info"
    with pytest.raises(CaptureSafetyError):
        port.symbol_info("EURUSD")
    with pytest.raises(CaptureSafetyError):
        port.copy_ticks_range("EURUSD", None, None, 1)
    assert not hasattr(port, "order_send")
    assert not hasattr(port, "order_check")


def test_host_source_has_no_order_capability_or_scheduler_mutation() -> None:
    import inspect

    source = inspect.getsource(host)
    for forbidden in (
        "order_send(", "order_check(", "order_calc_margin(",
        "order_calc_profit(", "symbol_select(", "login(", "order_modify(",
        "schedule_task(", "subprocess.", "os.system(",
    ):
        assert forbidden not in source
    assert "mt5.initialize()" in source
    assert "mt5.shutdown()" in source
    assert "APPROVAL_TOKEN" in source
    assert "PRIVATE_LOCAL_EXNESS_DEMO_ONLY" in source
