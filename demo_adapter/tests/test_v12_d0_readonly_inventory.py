"""D0 owner-independent synthetic tests: no live MT5, no broker or orders."""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.v12_d0_readonly_inventory import (
    DiscoveryBlocked,
    _identity,
    _private_write_exclusive,
    observe_only,
)

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "demo_adapter/scripts/v12_d0_readonly_inventory.py"
PS = ROOT / "demo_adapter/scripts/v12-d0-readonly-inventory.ps1"


class FakeReadonlyPort:
    def __init__(
        self, *, connected: bool = True, disabled: bool = True,
        positions: tuple = (), orders: tuple = (),
        login: int = 12345678, trade_mode: int = 0,
    ) -> None:
        self.connected = connected
        self.disabled = disabled
        self.positions = positions
        self.orders = orders
        self.login = login
        self.trade_mode = trade_mode
        self.calls: list[str] = []

    def terminal_info(self) -> dict:
        self.calls.append("terminal_info")
        return {"connected": self.connected, "tradeapi_disabled": self.disabled}

    def account_info(self) -> dict:
        self.calls.append("account_info")
        return {
            "company": "Exness Technologies Ltd",
            "server": "Exness-MT5Trial15", "currency": "USD",
            "login": self.login, "trade_mode": self.trade_mode,
        }

    def positions_get(self) -> tuple:
        self.calls.append("positions_get")
        return self.positions

    def orders_get(self) -> tuple:
        self.calls.append("orders_get")
        return self.orders

    def symbol_info(self, symbol: str) -> dict:
        self.calls.append("symbol_info")
        assert symbol == "XAUUSD"
        return {
            "name": "XAUUSD",
            "trade_mode": 4,
            "trade_contract_size": 100,
            "trade_tick_value_loss": 1.0,
            "currency_profit": "USD",
            "swap_long": -10,
        }

    def symbol_info_tick(self, symbol: str) -> dict:
        self.calls.append("symbol_info_tick")
        assert symbol == "XAUUSD"
        return {"time": 1792490000, "time_msc": 1792490000000,
                "bid": 4100, "ask": 4100.3}


def test_synthetic_demo_pass_does_not_qualify_four_hours() -> None:
    # The frozen fingerprint value depends on the separately provisioned
    # admitted demo login. A synthetic login is never an authenticated account.
    p = FakeReadonlyPort()
    with pytest.raises(DiscoveryBlocked, match="unadmitted account fingerprint"):
        observe_only(p)
    assert not any(x.startswith("order_") for x in p.calls)


@pytest.mark.parametrize("changes", [
    {"connected": False}, {"disabled": False},
    {"positions": ({"ticket": 1},)}, {"orders": ({"ticket": 1},)},
    {"trade_mode": 2},
])
def test_fail_closed_before_symbol_read(changes: dict) -> None:
    p = FakeReadonlyPort(**changes)
    with pytest.raises(DiscoveryBlocked):
        observe_only(p)
    assert "symbol_info" not in p.calls
    assert "symbol_info_tick" not in p.calls


def test_unknown_missing_or_live_identity_fails_before_symbol() -> None:
    for login in (0, -1, 12345678):
        p = FakeReadonlyPort(login=login)
        with pytest.raises(DiscoveryBlocked):
            _identity(p)
        assert "symbol_info" not in p.calls


def test_exclusive_private_bytes_and_no_implicit_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "immutable-private.json"
    a = {"schema": "SYNTHETIC", "execution_allowed": False}
    digest = _private_write_exclusive(target, a)
    import hashlib
    assert digest == hashlib.sha256(target.read_bytes()).hexdigest()
    assert json.loads(target.read_text()) == a
    with pytest.raises(FileExistsError):
        _private_write_exclusive(target, a)


def test_no_trade_or_terminal_configuration_method_exposed() -> None:
    from scripts import v12_d0_readonly_inventory
    source = inspect.getsource(v12_d0_readonly_inventory)
    for forbidden in (
        "order_send(", "order_check(", "order_calc_margin(", "order_calc_profit(",
        "symbol_select(", "terminal_login(", "position_close(", "history_deals_get(",
        "positions_total(", "orders_total(", "mt5.login(", "mt5.symbol_select(",
        "mt5.order_", "subprocess.",
    ):
        assert forbidden not in source
    ps_source = PS.read_text(encoding="utf-8")
    for forbidden in (
        "Register-ScheduledTask", "Set-ScheduledTask", "order_send",
        "order_check", "order_calc_margin", "symbol_select", "login -",
    ):
        assert forbidden not in ps_source
    assert "OWNER_APPROVED_EXACT_D0_INVENTORY_ONLY_NO_TRADING" in ps_source


@pytest.mark.skipif(sys.platform != "win32", reason="native PS5.1 AST validation on Windows")
def test_native_ps51_syntax_only() -> None:
    shell = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    assert shell.is_file()
    script = (
        "$errors=$null; $tokens=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + str(PS).replace("'", "''") + "',[ref]$tokens,[ref]$errors)|Out-Null; "
        "if($errors.Count -gt 0){$errors|Format-List;exit 29};"
        "'PS51_PARSE_PASS'"
    )
    result = subprocess.run(  # noqa: S603
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_registration_remains_d0_and_not_v12_4h() -> None:
    # D0 contract is a different artifact; frozen 240-minute registration
    # must never be populated merely because metadata were discovered.
    frozen = ROOT / (
        "phase0/roadmap/DEMO_V12_EXACT_FIRST_READONLY_RUN_UNFROZEN_TEMPLATE_2026-10-19.json"
    )
    packet = json.loads(frozen.read_text("utf-8"))
    assert packet["exact_window_start_utc"] is None
    assert packet["exact_window_end_utc"] is None
    assert packet["v12_overlap_start_utc"] is None
    assert packet["owner_first_run_confirmation_id"] is None
    assert packet["real_window_prospective_frozen"] is False


def test_single_d0_snapshot_synthetic_match_never_admits_market(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib

    from scripts import v12_d0_readonly_inventory

    expected = hashlib.sha256(
        b"Exness Technologies Ltd|Exness-MT5Trial15|12345678|USD"
    ).hexdigest()
    monkeypatch.setattr(v12_d0_readonly_inventory, "EXPECTED_IDENTITY", expected)
    fake = FakeReadonlyPort()
    result = observe_only(fake)
    assert result["account"]["external_python_trading_disabled"] is True
    assert result["account"]["known_positions"] == 0
    assert result["symbol"]["trade_mode"] == "4"
    assert result["tick"]["bid"] == "4100"
    assert result["session_interpretation"].startswith("NOT_ADMITTED_")
    assert result["actual_current_stressed_costs_admitted"] is False
    assert result["trading_orders_permitted"] is False
    assert result["event_guard_health_known"] is False
    assert result["order_actions"] == 0
    assert fake.calls.count("positions_get") == 2
    assert fake.calls.count("orders_get") == 2
    assert fake.calls.count("symbol_info") == 1
    assert fake.calls.count("symbol_info_tick") == 1


def test_d0_prospective_contract_source_byte_pins() -> None:
    import hashlib

    record = ROOT / (
        "phase0/roadmap/"
        "DEMO_V12_D0_DIAGNOSTIC_NOT_CAPTURE_FROZEN_REGISTRATION_2026-10-20.json"
    )
    doc = json.loads(record.read_text("utf-8"))
    pins = {
        PS: doc["collector_ps_sha256"],
        HOST: doc["host_sha256"],
        ROOT / "demo_adapter/scripts/v12_attempt_journal.py":
            doc["attempt_journal_sha256"],
    }
    for file, pin in pins.items():
        assert hashlib.sha256(file.read_bytes()).hexdigest() == pin, file
        assert b"\r\n" not in file.read_bytes()
    assert doc["broker_trading_allowed"] is False
    assert doc["four_hour_capture_allowed"] is False
    assert doc["vps_mt5_execution_authorized_in_git"] is False
    assert doc["owner_d0_confirmation"] is None
    assert doc["full_4h_observation_start_utc"] is None
    assert doc["actual_cost_admission_allowed"] is False
