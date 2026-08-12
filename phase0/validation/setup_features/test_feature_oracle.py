import ast
import copy
import unittest
from decimal import Decimal
from pathlib import Path

from feature_oracle import (
    Bar, adx, atr, bar_geometry, breakout_bar, brt_retest, completed_bars,
    confirmation_sequence, confirmed_swings, correlation, ema, fbr_hold_and_confirm,
    fbr_reclaim, mirror_bars, moc_compression, moc_trigger, normalize_price,
    rejection_bar, reward_risk, rsi, rsr_location, tpb_zones, true_ranges,
    validate_series,
)


def series(closes, *, start=0, step=900, width=2.0):
    return [Bar(start + i * step, c - 0.25, c + width / 2, c - width / 2, c, 10)
            for i, c in enumerate(closes)]


class RawOHLCFeatureTests(unittest.TestCase):
    def test_oracle_has_no_broker_network_or_model_imports(self):
        tree = ast.parse((Path(__file__).parent / "feature_oracle.py").read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported.isdisjoint({"MetaTrader5", "socket", "requests", "urllib", "httpx", "openai"}))

    def test_forming_bar_is_excluded(self):
        bars = series(range(20))
        decision = bars[-1].time + 899
        eligible = completed_bars(bars, decision, 900)
        self.assertEqual(len(eligible), 19)
        self.assertNotIn(bars[-1], eligible)

    def test_integrity_fail_closed_and_known_session_break(self):
        bars = series(range(20))
        decision = bars[-1].time + 900
        self.assertEqual(validate_series(bars, decision_time=decision, period_seconds=900, minimum=20), (True, "CLEAR"))
        dup = list(bars); dup[9] = Bar(dup[8].time, 1, 2, 0, 1)
        self.assertEqual(validate_series(dup, decision_time=decision, period_seconds=900, minimum=20)[1], "TIMESTAMP_DUPLICATE_OR_NONMONOTONIC")
        bad = list(bars); bad[5] = Bar(bad[5].time, 4, 3, 2, 4)
        self.assertEqual(validate_series(bad, decision_time=decision, period_seconds=900, minimum=20)[1], "OHLC_INVALID")
        gap = bars[:10] + [Bar(b.time + 900, b.open, b.high, b.low, b.close) for b in bars[10:]]
        new_decision = gap[-1].time + 900
        self.assertEqual(validate_series(gap, decision_time=new_decision, period_seconds=900, minimum=20)[1], "UNEXPLAINED_GAP")
        boundary = (bars[9].time + 900, gap[10].time)
        self.assertEqual(validate_series(gap, decision_time=new_decision, period_seconds=900, minimum=20, known_breaks=[boundary]), (True, "CLEAR"))

    def test_missing_warmup_and_zero_range(self):
        bars = series(range(13))
        self.assertEqual(validate_series(bars, decision_time=20000, period_seconds=900, minimum=14)[1], "WARMUP_MISSING")
        self.assertIsNone(bar_geometry(Bar(0, 5, 5, 5, 5))["body_fraction"])

    def test_true_range_gap_and_wilder_atr(self):
        bars = [Bar(0, 10, 11, 9, 10), Bar(1, 13, 14, 12, 13), Bar(2, 12, 13, 11, 12)]
        self.assertEqual(true_ranges(bars), [2, 4, 2])
        values = atr(bars, 2)
        self.assertEqual(values[1], 3)
        self.assertEqual(values[2], 2.5)

    def test_ema_seed_and_update(self):
        values = ema([1, 2, 3, 4], 3)
        self.assertEqual(values[:2], [None, None])
        self.assertEqual(values[2], 2)
        self.assertEqual(values[3], 3)

    def test_rsi_edge_cases_and_direction(self):
        rising = series(range(20))
        flat = series([5] * 20)
        falling = series(range(20, 0, -1))
        self.assertEqual(rsi(rising)[-1], 100)
        self.assertEqual(rsi(flat)[-1], 50)
        self.assertEqual(rsi(falling)[-1], 0)

    def test_adx_and_di_mirror(self):
        rising = series([100 + i + (i % 3) * 0.1 for i in range(60)])
        falling = mirror_bars(rising, 150)
        a1, p1, m1 = adx(rising)
        a2, p2, m2 = adx(falling)
        self.assertAlmostEqual(a1[-1], a2[-1], places=10)
        self.assertAlmostEqual(p1[-1], m2[-1], places=10)
        self.assertAlmostEqual(m1[-1], p2[-1], places=10)
        self.assertGreater(p1[-1], m1[-1])

    def test_swing_confirmation_requires_two_later_bars(self):
        bars = [Bar(i, 5, h, l, 5) for i, (h, l) in enumerate([(7, 3), (8, 2), (10, 1), (8, 2), (7, 3)])]
        self.assertEqual(confirmed_swings(bars), ([2], [2]))
        self.assertEqual(confirmed_swings(bars[:4]), ([], []))

    def test_rejection_long_short_symmetry_and_boundary(self):
        long_bar = Bar(0, 5, 7, 2, 6.5)
        short_bar = mirror_bars([long_bar], 5)[0]
        self.assertTrue(rejection_bar(long_bar, "LONG"))
        self.assertTrue(rejection_bar(short_bar, "SHORT"))
        self.assertFalse(rejection_bar(Bar(0, 5, 5, 5, 5), "LONG"))

    def test_tpb_zones_and_two_bar_confirmation(self):
        long_zones = tpb_zones(100, 120, "LONG")
        short_zones = tpb_zones(100, 80, "SHORT")
        self.assertEqual(long_zones["A"], (110.0, 112.36))
        self.assertEqual(short_zones["A"], (87.64, 90.0))
        rejection = Bar(0, 110, 112, 106, 111)
        self.assertTrue(confirmation_sequence(rejection, [Bar(1, 111, 112, 110, 111.9), Bar(2, 112, 113, 111, 112.1)], "LONG", .1))
        self.assertFalse(confirmation_sequence(rejection, [Bar(1, 111, 112, 110, 112.09)], "LONG", .1))

    def test_breakout_exact_thresholds_and_one_side(self):
        bar = Bar(0, 100.0, 102.5, 99.5, 102.0)
        args = dict(direction="LONG", level=101.0, atr_h1=10.0, prior_bodies=[1.5] * 20, adx_now=17, adx_five_bars_ago=20)
        self.assertTrue(breakout_bar(bar, **args))
        self.assertFalse(breakout_bar(Bar(0, 100, 102.5, 99.5, 101.999), **args))
        mirrored = mirror_bars([bar], 100)[0]
        self.assertTrue(breakout_bar(mirrored, **dict(args, direction="SHORT", level=99.0)))

    def test_brt_retest_depth_and_twelve_bar_limit(self):
        valid = [Bar(i, 101, 102, 99.8, 100.5) for i in range(4)]
        self.assertTrue(brt_retest(valid, direction="LONG", boundary=100, level_tol=.25, atr_h1=10))
        deep = list(valid); deep[-1] = Bar(3, 100, 101, 97, 98.49)
        self.assertFalse(brt_retest(deep, direction="LONG", boundary=100, level_tol=.25, atr_h1=10))
        self.assertFalse(brt_retest(valid * 4, direction="LONG", boundary=100, level_tol=.25, atr_h1=10))

    def test_fbr_reclaim_wick_only_fails_and_mirror_passes(self):
        bars = [Bar(0, 100, 100.2, 98, 99), Bar(1, 99, 101, 98.5, 100.6)]
        self.assertTrue(fbr_reclaim(bars, direction="LONG", boundary=100, atr_h1=10, tick_size=.1, median_body_20=.5))
        wick_only = [Bar(0, 100, 100.2, 98, 99.9)]
        self.assertFalse(fbr_reclaim(wick_only, direction="LONG", boundary=100, atr_h1=10, tick_size=.1, median_body_20=.5))
        self.assertTrue(fbr_reclaim(mirror_bars(bars, 100), direction="SHORT", boundary=100, atr_h1=10, tick_size=.1, median_body_20=.5))

    def test_fbr_hold_and_confirmation_are_both_required(self):
        reclaim = Bar(0, 99, 101, 98, 100.6)
        following = [Bar(1, 100.5, 101.3, 100, 101.1)]
        self.assertTrue(fbr_hold_and_confirm(reclaim, following, direction="LONG", boundary=100, atr_m15=2, tick_size=.1))
        self.assertFalse(fbr_hold_and_confirm(reclaim, [Bar(1, 100, 101.3, 99, 99.89)], direction="LONG", boundary=100, atr_m15=2, tick_size=.1))

    def test_rsr_location_boundaries_and_middle_rejection(self):
        self.assertTrue(rsr_location(103, 100, 120, "LONG"))
        self.assertFalse(rsr_location(103.001, 100, 120, "LONG"))
        self.assertTrue(rsr_location(117, 100, 120, "SHORT"))
        self.assertFalse(rsr_location(110, 100, 120, "LONG"))

    def test_moc_trigger_bounds_and_fresh_compression(self):
        compression = [Bar(i, 100, 101, 99.5, 100.2) for i in range(3)]
        trigger = Bar(4, 100.5, 103, 100.5, 102.8)
        args = dict(direction="LONG", atr_m15=20, median_body_20=1.5, rsi14=55)
        self.assertTrue(moc_trigger(compression, trigger, **args))
        self.assertFalse(moc_trigger(compression, trigger, **dict(args, rsi14=54.999)))
        self.assertFalse(moc_trigger(compression[:2], trigger, **args))
        self.assertTrue(moc_trigger(mirror_bars(compression, 100), mirror_bars([trigger], 100)[0], **dict(args, direction="SHORT", rsi14=45)))

    def test_moc_compression_all_predicates_and_mirror(self):
        prior = [Bar(i, 112, 114, 110, 112) for i in range(20)]
        comp = [Bar(20 + i, 117.5, 118.5, 116.8 + .1 * i, 117.8) for i in range(3)]
        args = dict(direction="LONG", impulse_start=100, impulse_end=120, atr_h1=10, atr_m15=2)
        self.assertTrue(moc_compression(comp, prior, **args))
        too_deep = list(comp); too_deep[0] = Bar(20, 115, 116, 111, 115)
        self.assertFalse(moc_compression(too_deep, prior, **args))
        self.assertTrue(moc_compression(mirror_bars(comp, 100), mirror_bars(prior, 100), **dict(args, direction="SHORT", impulse_start=100, impulse_end=80)))

    def test_tick_normalization_never_reduces_stop_protection(self):
        self.assertEqual(normalize_price("99.994", "0.01", "BUY_STOP"), Decimal("99.99"))
        self.assertEqual(normalize_price("100.006", "0.01", "SELL_STOP"), Decimal("100.01"))
        self.assertEqual(normalize_price("110.009", "0.01", "BUY_TARGET"), Decimal("110.00"))
        self.assertEqual(normalize_price("89.991", "0.01", "SELL_TARGET"), Decimal("90.00"))

    def test_tick_normalization_can_cross_rr_threshold(self):
        raw = reward_risk(Decimal("100"), Decimal("95.001"), Decimal("110"), "LONG")
        stop = normalize_price("95.001", "0.01", "BUY_STOP")
        normalized = reward_risk(Decimal("100"), stop, Decimal("110"), "LONG")
        self.assertGreater(raw, Decimal("2"))
        self.assertEqual(normalized, Decimal("2"))

    def test_mirror_close_series_is_perfectly_inverted(self):
        bars = series([100, 101, 103, 102, 106])
        mirror = mirror_bars(bars, 100)
        self.assertAlmostEqual(correlation([b.close for b in bars], [b.close for b in mirror]), -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
