from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import unittest

from acquire_dukascopy import aggregate, decode, endpoint


class DukascopyAcquisitionTests(unittest.TestCase):
    def payload(self):
        return {
            "timestamp": 1577836800000, "multiplier": 0.001,
            "open": 1500.000, "high": 1501.000, "low": 1499.000, "close": 1500.500,
            "shift": 60000, "times": [0, 1],
            "opens": [0, 100], "highs": [0, 200], "lows": [0, 50],
            "closes": [0, 150], "volumes": [0.001, 0.002],
        }

    def test_delta_decoder_is_exact_and_chronological(self):
        rows = decode(self.payload())
        self.assertEqual([1577836800000, 1577836860000], [row.stamp_ms for row in rows])
        self.assertEqual(Decimal("1500.100"), rows[1].open)
        self.assertEqual(Decimal("1500.650"), rows[1].close)
        self.assertEqual([1000, 2000], [row.volume for row in rows])

    def test_closed_market_null_bases_decode_to_no_rows(self):
        value = self.payload()
        for key in ("times", "opens", "highs", "lows", "closes", "volumes"):
            value[key] = []
        for key in ("open", "high", "low", "close"):
            value[key] = None
        self.assertEqual([], decode(value))

    def test_bid_ask_aggregation_preserves_sides(self):
        bid = decode(self.payload())
        ask_payload = self.payload()
        for name in ("open", "high", "low", "close"):
            ask_payload[name] += .2
        ask = decode(ask_payload)
        rows = aggregate(bid, ask, 900, "2026-08-24T00:00:00Z")
        self.assertEqual(1, len(rows))
        self.assertEqual("1500.000", rows[0]["open_bid"])
        self.assertEqual("1500.200", rows[0]["open_ask"])
        self.assertEqual("3000", rows[0]["tick_volume"])

    def test_mismatched_side_drops_the_entire_derived_bucket(self):
        bid = decode(self.payload())
        ask = decode(self.payload())[:-1]
        self.assertEqual([], aggregate(bid, ask, 900, "2026-08-24T00:00:00Z"))

    def test_endpoint_is_official_read_only_path(self):
        self.assertEqual(
            "https://jetta.dukascopy.com/v1/candles/minute/XAU-USD/BID/2020/1/2",
            endpoint("BID", date(2020, 1, 2)),
        )

    def test_no_broker_model_message_or_trading_capability(self):
        tree = ast.parse(Path(__file__).with_name("acquire_dukascopy.py").read_text())
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                calls.add(node.func.attr if isinstance(node.func, ast.Attribute)
                          else node.func.id if isinstance(node.func, ast.Name) else "")
        self.assertTrue(imports.isdisjoint({"MetaTrader5", "openai", "smtplib", "telegram", "subprocess"}))
        self.assertTrue(calls.isdisjoint({"order_send", "order_check", "positions_get", "Popen", "run"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
