import ast
import unittest
from datetime import datetime, timezone
from pathlib import Path

from phase0.validation.vps_reliability.fault_drill_state import observe


HERE = Path(__file__).resolve().parent
WRAPPER = HERE / "run_g0_07_fault_drill.ps1"


class Rec:
    def __init__(self, **values):
        self.values = values

    def _asdict(self):
        return self.values


class FakeAPI:
    attached = True
    connected = True
    disabled = True
    tick_msc = int(datetime.now(timezone.utc).timestamp() * 1000)

    @classmethod
    def initialize(cls):
        return cls.attached

    @classmethod
    def shutdown(cls):
        return True

    @classmethod
    def terminal_info(cls):
        return Rec(connected=cls.connected, tradeapi_disabled=cls.disabled, build=6104)

    @classmethod
    def symbol_info_tick(cls, symbol):
        return Rec(time_msc=cls.tick_msc)


class FaultDrillOrchestratorTests(unittest.TestCase):
    def setUp(self):
        FakeAPI.attached = True
        FakeAPI.connected = True
        FakeAPI.disabled = True
        FakeAPI.tick_msc = int(datetime.now(timezone.utc).timestamp() * 1000)

    def test_state_check_requires_disabled_barrier(self):
        FakeAPI.disabled = False
        result = observe(FakeAPI, "HEALTHY")
        self.assertEqual("FAIL_CLOSED", result["status"])
        self.assertEqual("EXTERNAL_PYTHON_TRADING_NOT_DISABLED", result["reason"])

    def test_state_check_distinguishes_disconnect_and_healthy_recovery(self):
        FakeAPI.connected = False
        self.assertEqual("READY", observe(FakeAPI, "DISCONNECTED")["status"])
        self.assertEqual("WAIT", observe(FakeAPI, "HEALTHY")["status"])
        FakeAPI.connected = True
        self.assertEqual("READY", observe(FakeAPI, "HEALTHY")["status"])

    def test_state_check_waits_for_terminal_and_fresh_tick(self):
        FakeAPI.attached = False
        self.assertEqual("MT5_NOT_READY", observe(FakeAPI, "HEALTHY")["reason"])
        FakeAPI.attached = True
        FakeAPI.tick_msc = 0
        self.assertEqual("FRESH_TICK_NOT_AVAILABLE", observe(FakeAPI, "HEALTHY")["reason"])

    def test_state_check_has_no_mutation_or_process_network_control(self):
        source = HERE / "fault_drill_state.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        forbidden_imports = {"subprocess", "socket", "requests", "smtplib", "telegram"}
        forbidden_calls = {
            "order_send", "order_check", "order_calc_margin", "positions_get",
            "orders_get", "login", "symbol_select", "system", "popen", "run", "Popen",
        }
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                calls.add(node.func.id if isinstance(node.func, ast.Name)
                          else node.func.attr if isinstance(node.func, ast.Attribute) else "")
        self.assertFalse(imports & forbidden_imports)
        self.assertFalse(calls & forbidden_calls)

    def test_wrapper_contains_exact_frozen_sequence_and_scenario_ids(self):
        text = WRAPPER.read_text(encoding="utf-8")
        frozen = [
            "BASELINE", "DISCONNECT", "RECONNECT", "PYTHON_RESTART",
            "MT5_RESTART", "WINDOWS_RESTART", "CLOCK_CHECK", "BUILD_CHECK",
        ]
        block = text[text.index("$FrozenEvents = @("):text.index("$ScenarioIds = @{")]
        quoted = [token for token in frozen if f'"{token}"' in block]
        self.assertEqual(frozen, quoted)
        for scenario in (
            "VPS-R31-DISCONNECT-1", "VPS-R31-RECONNECT-1",
            "VPS-R31-PYTHON-RESTART-1", "VPS-R31-MT5-RESTART-1",
            "VPS-R31-WINDOWS-RESTART-1", "VPS-R31-CLOCK-CHECK-1",
            "VPS-R31-BUILD-CHECK-1",
        ):
            self.assertIn(scenario, text)

    def test_wrapper_preserves_all_fail_closed_boundaries(self):
        text = WRAPPER.read_text(encoding="utf-8")
        for required in (
            "Capture-Exposure -Phase \"PRE_DRILL\"",
            "Capture-Exposure -Phase \"POST_RECOVERY\"",
            "--verify-reconciliation",
            "--pre-sha256",
            "--post-sha256",
            "Assert-ExactPrefix",
            "tradeapi_disabled",
            "Wait-ReadOnlyState",
            "Register-NetworkWatchdog",
            "Restore-NetworkAndRemoveWatchdog",
            "New-ScheduledTaskTrigger -AtLogOn",
            "Assert-WindowsRestartOccurred",
            "final_matrix_record_sha256",
            "git pull --ff-only origin main",
            "CloseMainWindow",
            "TimeoutSeconds 150",
            "AddMinutes(4)",
            "more than one active IPv4 default-route adapter",
        ):
            self.assertIn(required, text)

    def test_wrapper_has_no_broker_or_trading_mutation(self):
        text = WRAPPER.read_text(encoding="utf-8").lower()
        for forbidden in (
            "order_send", "order_check", "order_calc_margin", "positions_get",
            "orders_get", "symbol_select", "mt5.login", "trade request",
            "stop-process -id $terminal.id -force",
        ):
            self.assertNotIn(forbidden, text)

    def test_wrapper_uses_windows_powershell_51_compatible_hashing(self):
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("[Convert]::ToHexString", text)
        self.assertNotIn("SHA256]::HashData", text)
        self.assertIn("[Security.Cryptography.SHA256]::Create()", text)
        self.assertIn("[BitConverter]::ToString", text)


if __name__ == "__main__":
    unittest.main()
