from __future__ import annotations

import importlib
import json
import sys
import tempfile
import types
import unittest
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path


Record = namedtuple("Record", "items")


def rec(**kwargs):
    Row = namedtuple("Row", kwargs.keys())
    return Row(**kwargs)


class FakeMT5(types.ModuleType):
    def __init__(self):
        super().__init__("MetaTrader5")
        self.__author__ = "Fake MetaQuotes"
        self.__version__ = "test"
        self.TIMEFRAME_M1 = 1
        self.TIMEFRAME_M5 = 5
        self.TIMEFRAME_M15 = 15
        self.TIMEFRAME_H1 = 60
        self.TIMEFRAME_H4 = 240
        self.TIMEFRAME_D1 = 1440
        self.COPY_TICKS_ALL = 3
        self.ORDER_TYPE_BUY = 0
        self.ORDER_TYPE_SELL = 1
        self.calls = []
        self.traps = []

    def _call(self, name):
        self.calls.append(name)

    def initialize(self): self._call("initialize"); return True
    def shutdown(self): self._call("shutdown"); return True
    def last_error(self): self._call("last_error"); return (1, "Success")
    def version(self): self._call("version"); return (500, 9999, "test")
    def terminal_info(self):
        self._call("terminal_info")
        return rec(connected=True, trade_allowed=True, tradeapi_disabled=True, build=9999, company="Exness", name="MT5", path=r"C:\Users\Alice\MT5", data_path=r"C:\Users\Alice\AppData\MT5")
    def account_info(self):
        self._call("account_info")
        return rec(login=12345678, trade_mode=0, trade_allowed=True, trade_expert=True, margin_mode=2, leverage=100, balance=10000.0, equity=10000.0, margin=0.0, margin_free=10000.0, margin_so_call=60.0, margin_so_so=0.0, server="Exness-Test", company="Exness", currency="USD", name="Test User")
    def symbols_get(self):
        self._call("symbols_get")
        return (self.symbol_info("XAUUSDm"),)
    def symbol_info(self, symbol):
        self._call("symbol_info")
        return rec(name=symbol, path="Metals", description="Gold", visible=True, select=True, digits=2, point=0.01, trade_mode=4, trade_exemode=2, filling_mode=3, order_mode=127, trade_calc_mode=0, trade_contract_size=100.0, trade_tick_size=0.01, trade_tick_value=1.0, trade_tick_value_profit=1.0, trade_tick_value_loss=1.0, volume_min=0.01, volume_max=100.0, volume_step=0.01, volume_limit=0.0, trade_stops_level=0, trade_freeze_level=0, spread=20, spread_float=True, currency_base="XAU", currency_profit="USD", currency_margin="XAU", time=1700000000, time_msc=1700000000000)
    def symbol_info_tick(self, symbol):
        self._call("symbol_info_tick")
        return rec(time=1700000000, bid=2000.0, ask=2000.2, last=0.0, volume=0, time_msc=1700000000123, flags=6, volume_real=0.0)
    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        self._call("copy_rates_from_pos")
        return [{"time": 1699999940, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.5, "tick_volume": 100, "spread": 20, "real_volume": 0}, {"time": 1700000000, "open": 2000.5, "high": 2001.0, "low": 2000.0, "close": 2000.2, "tick_volume": 80, "spread": 20, "real_volume": 0}]
    def copy_ticks_from(self, symbol, from_utc, count, flags):
        self._call("copy_ticks_from")
        return [{"time": 1700000000, "bid": 2000.0, "ask": 2000.2, "time_msc": 1700000000123, "flags": 6}]
    def orders_get(self): self._call("orders_get"); return ()
    def positions_get(self): self._call("positions_get"); return ()
    def history_orders_get(self, start, end): self._call("history_orders_get"); return ()
    def history_deals_get(self, start, end): self._call("history_deals_get"); return ()
    def order_calc_profit(self, direction, symbol, volume, open_price, close_price): self._call("order_calc_profit"); return (close_price - open_price) * volume * 100 * (1 if direction == 0 else -1)
    def order_calc_margin(self, direction, symbol, volume, open_price): self._call("order_calc_margin"); return volume * open_price

    def order_send(self, *args, **kwargs): self.traps.append("order_send"); raise AssertionError("risk-changing trap")
    def order_check(self, *args, **kwargs): self.traps.append("order_check"); raise AssertionError("risk-changing trap")
    def login(self, *args, **kwargs): self.traps.append("login"); raise AssertionError("credential/trading trap")
    def symbol_select(self, *args, **kwargs): self.traps.append("symbol_select"); raise AssertionError("state-changing trap")


class ReadOnlyBehaviorTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeMT5()
        sys.modules["MetaTrader5"] = self.fake
        for name in ("readonly_mt5", "collector"):
            sys.modules.pop(name, None)
        self.adapter_module = importlib.import_module("readonly_mt5")
        self.collector = importlib.import_module("collector")

    def tearDown(self):
        sys.modules.pop("MetaTrader5", None)
        sys.modules.pop("readonly_mt5", None)
        sys.modules.pop("collector", None)

    def test_collection_uses_only_observation_and_calculation_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "evidence"
            result = self.collector.collect_evidence(
                self.adapter_module.ReadOnlyMT5,
                output,
                None,
                100,
                100,
                1,
                {"status": "PASS", "test": True},
            )
            self.assertIn(result["summary"]["status"], {"PASS", "PARTIAL"})
            self.assertEqual([], self.fake.traps)
            self.assertTrue((output / "MANIFEST.json").is_file())
            account = json.loads((output / "ACCOUNT.json").read_text(encoding="utf-8"))
            self.assertTrue(str(account["login"]).startswith("hmac-sha256:"))
            self.assertEqual("<REDACTED>", account["name"])
            terminal = json.loads((output / "TERMINAL.json").read_text(encoding="utf-8"))
            self.assertIn("<REDACTED_USER>", terminal["before"]["path"])
            expected_calls = {
                "initialize", "terminal_info", "account_info", "symbols_get", "symbol_info",
                "symbol_info_tick", "copy_rates_from_pos", "copy_ticks_from", "orders_get",
                "positions_get", "history_orders_get", "history_deals_get", "order_calc_profit",
                "order_calc_margin", "version", "shutdown",
            }
            self.assertTrue(set(self.fake.calls).issubset(expected_calls))

    def test_guard_false_aborts_before_account_collection(self):
        original = self.fake.terminal_info
        self.fake.terminal_info = lambda: rec(connected=True, trade_allowed=True, tradeapi_disabled=False)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(self.collector.CollectionError):
                self.collector.collect_evidence(
                    self.adapter_module.ReadOnlyMT5,
                    Path(tmp) / "evidence",
                    None,
                    100,
                    100,
                    1,
                    {"status": "PASS", "test": True},
                )
        self.assertNotIn("account_info", self.fake.calls)
        self.fake.terminal_info = original

    def test_dependency_lock_is_complete_and_binary_only(self):
        verifier = importlib.import_module("verify_readonly")
        result = verifier.verify_dependency_lock(Path(__file__).resolve().parent)
        self.assertEqual("PASS", result["status"], result["findings"])
        self.assertTrue(result["binary_only"])
        self.assertEqual(
            ["MetaTrader5==5.0.6090", "numpy==2.5.0"],
            result["locked_distributions"],
        )


if __name__ == "__main__":
    unittest.main()
