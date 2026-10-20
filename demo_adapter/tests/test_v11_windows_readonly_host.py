"""Native/synthetic safety tests; no real MT5 or VPS access."""
from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts import v11_windows_readonly_host as collector
from scripts.v11_readonly_collector import CaptureSafetyError, WindowContract

ROOT = Path(__file__).resolve().parents[2]
WINDOW = ROOT / "phase0/roadmap/DEMO_LIFECYCLE_V1_1_CAPTURE_WINDOW_TEMPLATE_2026-10-18.json"
PS = ROOT / "demo_adapter/scripts/v11_windows_readonly_capture.ps1"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _run_record() -> dict[str, Any]:
    reg = json.loads(WINDOW.read_text(encoding="utf-8"))
    now = datetime(2026, 10, 21, 13, tzinfo=UTC)
    reg.update({
        "classification": "DEMO_LIFECYCLE_ONLY_V1_1_READ_ONLY",
        "owner_approved_read_only_capture": True,
        "symbol": "XAUUSD",
        "volume_max": "0.01",
        "expected_terminal_pid": 6216,
        "terminal_exe": collector.TERMINAL_EXE,
        "exact_window_start_utc": now.isoformat(),
        "exact_window_end_utc": (now + timedelta(hours=4)).isoformat(),
        "expected_demo_identity_fingerprint_sha256": _sha(
            b"Exness Technologies Ltd|Exness-MT5Trial15|12345678|USD"
        ),
        "registration_sha256": "a" * 64,
        "exact_owner_approval_id": "SYNTHETIC_OWNER_APPROVAL_ONLY",
        "approval_for_vps_capture": "EXPLICIT_OWNER_APPROVED",
        "exact_collector_source_sha256": _sha(inspect.getsource(collector).encode()),
        "exact_readonly_primitive_sha256": _sha(
            (ROOT / "demo_adapter/scripts/v11_readonly_collector.py").read_bytes()
        ),
        "exact_collector_static_allowlist_verification_sha256": "b" * 64,
        "broker_xauusd_session_source_sha256": "c" * 64,
        "official_event_guard_health_and_event_schedule_sha256": "d" * 64,
        "holiday_and_reopening_exclusion_source_sha256": "e" * 64,
        "tick_pair_tolerance_ms": 100,
        "session_event_eligibility_prechecked": True,
        "raw_evidence_private_local_only": True,
        "mt5_external_python_trading_must_be_disabled": True,
    })
    return reg


class FakePort:
    def __init__(self, start: datetime) -> None:
        self.clock = start
        self.calls: list[str] = []
        self.login = 12345678
        self.disabled = True
        self.open_positions: tuple[Any, ...] = ()
        self.pending_orders: tuple[Any, ...] = ()
        self.ticks = [
            {"time_msc": int((start + timedelta(seconds=x)).timestamp() * 1000),
             "bid": "2000.00", "ask": "2000.25"}
            for x in range(14400)
        ]

    def terminal_info(self) -> dict[str, Any]:
        self.calls.append("terminal_info")
        return {"connected": True, "tradeapi_disabled": self.disabled}

    def account_info(self) -> dict[str, Any]:
        self.calls.append("account_info")
        return {
            "company": "Exness Technologies Ltd",
            "server": "Exness-MT5Trial15", "login": self.login,
            "currency": "USD", "trade_mode": 0,
            "balance": 10000, "equity": 10000, "margin": 0, "margin_free": 10000,
        }

    def symbol_info(self, symbol: str) -> dict[str, Any]:
        self.calls.append("symbol_info")
        assert symbol == "XAUUSD"
        return {
            "trade_tick_size": 0.01, "trade_tick_value_loss": 1,
            "trade_tick_value_profit": 1, "trade_contract_size": 100,
            "volume_min": 0.01, "volume_step": 0.01,
            "point": 0.01, "trade_stops_level": 10,
            "trade_freeze_level": 10, "swap_long": -3, "swap_short": -3,
            "swap_mode": 0,
        }

    def symbol_info_tick(self, symbol: str) -> dict[str, Any]:
        self.calls.append("symbol_info_tick")
        return {
            "time_msc": int(self.clock.timestamp() * 1000),
            "bid": 2000, "ask": 2000.25,
        }

    def positions_get(self) -> tuple[Any, ...]:
        self.calls.append("positions_get")
        return self.open_positions

    def orders_get(self) -> tuple[Any, ...]:
        self.calls.append("orders_get")
        return self.pending_orders

    def copy_ticks_range(
        self, symbol: str, start: datetime, end: datetime, flags: int
    ) -> list[dict[str, Any]]:
        self.calls.append("copy_ticks_range")
        assert flags == collector.EXPECTED_TICK_FLAGS
        assert symbol == "XAUUSD"
        return self.ticks

    def history_deals_get(
        self, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        self.calls.append("history_deals_get")
        return [
            {
                "symbol": "XAUUSD", "time_msc": int(start.timestamp() * 1000),
                "volume": 0.01, "commission": -0.07, "swap": -0.10, "fee": 0,
                "login": 12345678, "ticket": 777777,
            }
        ]


class FakeClock:
    def __init__(self, start: datetime, port: FakePort) -> None:
        self.now = start
        self.port = port

    def read(self) -> datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)
        self.port.clock = self.now


def _contract(record: dict[str, Any]) -> WindowContract:
    return WindowContract.from_record(record)


def test_no_foreign_mt5_methods_in_capture_source() -> None:
    src = inspect.getsource(collector)
    for illegal in collector.FORBIDDEN_NAMES:
        assert illegal + "(" not in src
    assert "import MetaTrader5" not in src
    assert "mt5.order" not in src
    assert collector.LIFECYCLE_CALLS == {"initialize", "shutdown"}
    assert "MetaTrader5" not in sys.modules


def test_source_hash_and_owner_registration_fail_closed() -> None:
    doc = _run_record()
    source = Path(collector.__file__).read_bytes()
    doc["exact_collector_source_sha256"] = _sha(source)
    pin = _sha(collector.canonical_json(doc))
    contract = collector.validate_run_record(doc, source, pin)
    assert contract.end_utc - contract.start_utc == timedelta(hours=4)
    for field, replacement in (
        ("owner_approved_read_only_capture", False),
        ("approval_for_vps_capture", "REQUIRED_SEPARATELY"),
        ("terminal_exe", "C:\\Wrong\\terminal64.exe"),
        ("tick_pair_tolerance_ms", None),
        ("symbol", "EURUSD"),
        ("exact_readonly_primitive_sha256", "f" * 64),
        ("mt5_external_python_trading_must_be_disabled", False),
    ):
        other = {**doc, field: replacement}
        with pytest.raises(CaptureSafetyError):
            collector.validate_run_record(other, source, _sha(collector.canonical_json(other)))


def test_synthetic_exact_4h_capture_with_fee_redaction() -> None:
    doc = _run_record()
    start = datetime.fromisoformat(doc["exact_window_start_utc"])
    port = FakePort(start)
    clock = FakeClock(start, port)
    result = collector.collect_window(
        port, _contract(doc), now_fn=clock.read, sleep_fn=clock.sleep
    )
    assert len(result["samples"]) == 2880
    assert len(result["ticks"]) == 14400
    assert len(result["historical_fee_deals"]) == 1
    assert result["fees_evidenced"] is True
    assert result["fee_zero_proven"] is False
    assert result["broker_orders_sent"] == 0
    assert result["account_after"]["balance"] == "10000"
    assert result["symbol_cash_metadata"]["trade_contract_size"] == "100"
    assert "777777" not in json.dumps(result)
    assert "12345678" not in json.dumps(result)
    assert set(port.calls) <= collector.READ_CALLS


@pytest.mark.parametrize("type_", ["account", "position", "permission"])
def test_untrusted_broker_state_aborts_without_order(type_: str) -> None:
    doc = _run_record()
    start = datetime.fromisoformat(doc["exact_window_start_utc"])
    port = FakePort(start)
    if type_ == "account":
        port.login = 999
    elif type_ == "position":
        port.open_positions = (object(),)
    else:
        port.disabled = False
    clock = FakeClock(start, port)
    with pytest.raises(CaptureSafetyError):
        collector.collect_window(
            port, _contract(doc), now_fn=clock.read, sleep_fn=clock.sleep
        )
    assert set(port.calls) <= collector.READ_CALLS


def test_price_and_fee_fields_reject_nonfinite_and_missing() -> None:
    with pytest.raises(CaptureSafetyError):
        collector._tick_row({"time_msc": 1234, "bid": "NaN", "ask": "2"})
    with pytest.raises(CaptureSafetyError):
        collector._fee_deal({"symbol": "XAUUSD", "time_msc": 0,
                             "volume": 0.01, "commission": None, "swap": 0})


@pytest.mark.skipif(sys.platform != "win32", reason="native PS5.1 Windows only")
def test_powershell51_launcher_ast_parser_without_running() -> None:
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    ps = str(PS).replace("'", "''")
    command = (
        "$t=$null;$e=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + ps + "',[ref]$t,[ref]$e)|Out-Null;"
        "if($e.Count){$e|Format-List;exit 9};"
        "'V11_NATIVE_PS51_SYNTAX_PASS'"
    )
    output = subprocess.run(  # noqa: S603 (parser only, no launcher execution)
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert output.returncode == 0, output.stdout + output.stderr
    assert "V11_NATIVE_PS51_SYNTAX_PASS" in output.stdout
    source = PS.read_text(encoding="utf-8")
    assert "order_send" not in source
    assert "Register-ScheduledTask" not in source
    assert "Start-ScheduledTask" not in source
    assert "Get-FileHash" in source
