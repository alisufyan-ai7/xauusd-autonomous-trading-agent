import ast
from pathlib import Path
import unittest

from feature_oracle import Bar
from family_golden_oracle import (
    SafetyState, evaluate_brt, evaluate_fbr, evaluate_moc, evaluate_rsr,
    evaluate_tpb,
)


def raw_h1_range(cycles=4):
    pattern = [110, 115, 119, 115, 110, 105, 101, 105]
    return [Bar(i * 3600, c, c + 1, c - 1, c, 10)
            for i, c in enumerate(pattern * cycles)]


class FiveFamilyGoldenLifecycleTests(unittest.TestCase):
    def test_oracle_has_no_broker_network_model_or_process_imports(self):
        source = Path(__file__).with_name("family_golden_oracle.py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported.isdisjoint(
            {"MetaTrader5", "socket", "requests", "urllib", "httpx", "openai", "subprocess"}
        ))

    def test_tpb_raw_zone_rejection_confirmation_to_candidate(self):
        result = evaluate_tpb(
            direction="LONG", regime="UP_TREND", impulse_start=100, impulse_end=120,
            location_level=111, level_tol=.1,
            rejection=Bar(0, 111, 112.2, 110, 111.8),
            following=[Bar(900, 111.8, 112.5, 111, 112.3)],
            tick_size=.1, stop_buffer=.2, tp1=120, final=125,
        )
        self.assertEqual(("PROPOSED", "TPB", 4), (result.state, result.family, result.expiry_bars))

    def test_brt_raw_breakout_retest_confirmation_to_candidate(self):
        result = evaluate_brt(
            direction="LONG", regime="UP_TREND", boundary=100, atr_h1=10,
            level_tol=.25, breakout=Bar(0, 98.5, 102.5, 98, 102),
            prior_bodies=[1] * 20, adx_now=20, adx_five_bars_ago=22,
            retest_h1=[Bar(3600, 101, 102, 99.8, 100.5)],
            rejection=Bar(4500, 100.5, 102, 99, 101.5),
            following=[Bar(5400, 101.5, 103, 101, 102.2)],
            tick_size=.1, stop_buffer=.5, tp1=112, final=115,
        )
        self.assertEqual(("PROPOSED", "BRT", 4), (result.state, result.family, result.expiry_bars))

    def test_fbr_raw_breach_reclaim_hold_confirmation_to_candidate(self):
        result = evaluate_fbr(
            direction="LONG", regime="RANGE", boundary=100, atr_h1=10, atr_m15=2,
            tick_size=.1, prior_twenty=[Bar(i, 100, 101, 99, 100.5) for i in range(20)],
            breach_to_reclaim=[Bar(20, 100, 100.2, 98, 99),
                               Bar(21, 99, 101, 98.5, 100.6)],
            following=[Bar(22, 100.5, 102, 100, 101.2)],
            stop_buffer=.5, tp1=110, final=115,
        )
        self.assertEqual(("PROPOSED", "FBR", 3), (result.state, result.family, result.expiry_bars))

    def test_rsr_raw_h1_range_and_m15_confirmation_to_candidate(self):
        result = evaluate_rsr(
            direction="LONG", h1_bars=raw_h1_range(), atr_h1=10, level_tol=.5,
            rejection=Bar(200000, 101, 102, 100, 101.8),
            following=[Bar(200900, 101.8, 102.5, 101, 102.2)],
            tick_size=.1, stop_buffer=.2,
        )
        self.assertEqual(("PROPOSED", "RSR", 4), (result.state, result.family, result.expiry_bars))

    def test_moc_raw_compression_trigger_and_no_chase_to_candidate(self):
        prior = [Bar(i, 112, 114, 110, 112) for i in range(20)]
        compression = [Bar(20 + i, 117.5, 118.5, 116.8 + .1 * i, 117.8) for i in range(3)]
        result = evaluate_moc(
            direction="LONG", regime="UP_TREND", impulse_start=100, impulse_end=120,
            atr_h1=10, atr_m15=2, prior_twenty=prior, compression=compression,
            trigger=Bar(23, 118, 120, 117.8, 119.8), rsi14=55,
            quote_price=119.9, stop_buffer=.2, tp1=125, final=130,
        )
        self.assertEqual(("PROPOSED", "MOC", 0), (result.state, result.family, result.expiry_bars))

    def test_common_gate_precedence_blocks_before_family_geometry(self):
        result = evaluate_tpb(
            direction="LONG", regime="DOWN_TREND", impulse_start=100, impulse_end=120,
            location_level=999, level_tol=0, rejection=Bar(0, 1, 1, 1, 1),
            following=[], tick_size=.1, stop_buffer=.2, tp1=120, final=125,
            safety=SafetyState(data_clear=False, event_clear=False),
        )
        self.assertEqual(("NO_TRADE", "DATA_INVALID"), (result.state, result.reason))

    def test_family_geometry_cannot_override_reward_risk(self):
        result = evaluate_tpb(
            direction="LONG", regime="UP_TREND", impulse_start=100, impulse_end=120,
            location_level=111, level_tol=.1,
            rejection=Bar(0, 111, 112.2, 110, 111.8),
            following=[Bar(900, 111.8, 112.5, 111, 112.3)],
            tick_size=.1, stop_buffer=.2, tp1=115, final=119,
        )
        self.assertEqual(("NO_TRADE", "INSUFFICIENT_RR"), (result.state, result.reason))

    def test_moc_quote_chase_is_terminal_no_trade(self):
        prior = [Bar(i, 112, 114, 110, 112) for i in range(20)]
        compression = [Bar(20 + i, 117.5, 118.5, 116.8 + .1 * i, 117.8) for i in range(3)]
        result = evaluate_moc(
            direction="LONG", regime="UP_TREND", impulse_start=100, impulse_end=120,
            atr_h1=10, atr_m15=2, prior_twenty=prior, compression=compression,
            trigger=Bar(23, 118, 120, 117.8, 119.8), rsi14=55,
            quote_price=120.101, stop_buffer=.2, tp1=125, final=130,
        )
        self.assertEqual(("NO_TRADE", "QUOTE_CHASE_BLOCKED"), (result.state, result.reason))


if __name__ == "__main__":
    unittest.main(verbosity=2)
