import importlib
import json
import sys
import tempfile
import types
import unittest
from collections import namedtuple
from pathlib import Path


def rec(**values):
    return namedtuple("Record", values)(**values)


class FakeMT5(types.ModuleType):
    def __init__(self, blocked=True):
        super().__init__("MetaTrader5")
        self.blocked = blocked
        self.calls = []
        self.spread = 20
        self.condition_sample = 0
    def _c(self, name): self.calls.append(name)
    def initialize(self): self._c("initialize"); return True
    def shutdown(self): self._c("shutdown"); return True
    def last_error(self): return (1, "ok")
    def version(self): return (500, 9999, "test")
    def terminal_info(self): self._c("terminal_info"); return rec(connected=True, tradeapi_disabled=self.blocked, build=9999)
    def account_info(self): self._c("account_info"); return rec(login=1234, server="Secret", company="Exness", currency="USD", trade_mode=0, margin_mode=2)
    def symbol_info(self, symbol):
        self._c("symbol_info")
        self.spread += 1
        self.condition_sample += 1
        changing = self.condition_sample
        return rec(digits=2, point=.01, trade_mode=4 if changing % 2 else 0, trade_exemode=2, filling_mode=3, order_mode=127, order_gtc_mode=0, trade_calc_mode=0, trade_contract_size=100., trade_tick_size=.01, trade_tick_value=1. + changing / 1000, trade_tick_value_profit=1. + changing / 1000, trade_tick_value_loss=1. - changing / 1000, volume_min=.01, volume_max=100., volume_step=.01, volume_limit=0., trade_stops_level=changing, trade_freeze_level=changing, spread=self.spread, spread_float=True, swap_mode=1, swap_long=-1. - changing, swap_short=changing / 10, swap_rollover3days=3, currency_base="XAU", currency_profit="USD", currency_margin="XAU")
    def symbol_info_tick(self, symbol):
        import time
        self._c("symbol_info_tick"); return rec(time_msc=int(time.time()*1000), bid=2000., ask=2000.2)
    def __getattr__(self, name):
        raise AssertionError(f"unexpected MT5 access: {name}")


class Tests(unittest.TestCase):
    def load(self, blocked=True):
        fake = FakeMT5(blocked)
        sys.modules["MetaTrader5"] = fake
        for name in ("readonly_mt5", "diagnostic"):
            sys.modules.pop(name, None)
        adapter = importlib.import_module("readonly_mt5")
        diagnostic = importlib.import_module("diagnostic")
        return fake, adapter, diagnostic

    def test_short_run_hash_chain_and_redaction(self):
        fake, adapter, diagnostic = self.load()
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "run"
            result = diagnostic.run(adapter.ReadOnlyMT5, output, "XAUUSD", 1, .1)
            self.assertEqual("PASS", result["status"])
            fp = json.loads((output / "fingerprint.json").read_text())
            self.assertNotIn("symbol_properties", fp)
            self.assertTrue(fp["account"].startswith("hmac-sha256:"))
            self.assertNotIn("1234", json.dumps(fp))
            prior = "0" * 64
            for line in (output / "observations.jsonl").read_bytes().splitlines(keepends=True):
                row = json.loads(line)
                self.assertEqual(prior, row["prior_record_sha256"])
                prior = __import__("hashlib").sha256(line).hexdigest()
            rows = [json.loads(line) for line in (output / "observations.jsonl").read_text().splitlines()]
            self.assertTrue(any(row["symbol_conditions_changed"] for row in rows[1:]))
            self.assertNotEqual(rows[0]["symbol_conditions_sha256"], rows[-1]["symbol_conditions_sha256"])
            self.assertEqual(result["final_record_sha256"], prior)
        self.assertEqual({"initialize", "shutdown", "terminal_info", "account_info", "symbol_info", "symbol_info_tick"}, set(fake.calls))

    def test_guard_aborts_before_account_read(self):
        fake, adapter, diagnostic = self.load(False)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(diagnostic.SafeStop):
                diagnostic.run(adapter.ReadOnlyMT5, Path(td)/"run", "XAUUSD", 1, .1)
        self.assertNotIn("account_info", fake.calls)

    def test_powershell_sidecar_uses_explicit_path_and_value(self):
        script = Path(__file__).with_name("run_diagnostic.ps1").read_text(encoding="utf-8")
        self.assertIn("[System.IO.File]::WriteAllText", script)
        self.assertIn("$zip.FullName", script)
        self.assertIn("$zip.Name", script)
        self.assertNotIn("Set-Content", script)


if __name__ == "__main__":
    unittest.main()
