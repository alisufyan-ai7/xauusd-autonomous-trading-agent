from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from xauusd_agent.features.v2_crossframe_forensics import describe_crossframe_gaps
from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe

START = datetime(2026, 10, 20, tzinfo=UTC)
ONE = Decimal("3000")


def bar(tf: ContextTimeframe, date: datetime, *, volume: int = 1) -> ContextBar:
    return ContextBar(
        timeframe=tf, open_time=date, open=ONE,
        high=ONE + 1, low=ONE - 1, close=ONE, tick_volume=volume,
    )


def daily_with_missing_20h_h4():
    daily = bar(ContextTimeframe.D1, START, volume=5)
    h4 = tuple(
        bar(ContextTimeframe.H4, START + timedelta(hours=h))
        for h in (0, 4, 8, 12, 16, 24)
    )
    return {ContextTimeframe.D1: (daily,), ContextTimeframe.H4: h4}


def test_nominally_missing_h4_20h_is_diagnosed_not_excused():
    forensic = describe_crossframe_gaps(
        frames=daily_with_missing_20h_h4(),
        as_of=START + timedelta(days=2),
    )
    d1_h4 = forensic.results[0]
    assert d1_h4.pair == "D1_H4"
    assert d1_h4.partial_parent_buckets == 1
    assert d1_h4.missing_child_slot_count == 1
    assert d1_h4.misaligned_child_slot_count == 0
    assert d1_h4.partial_aggregate_match_count == 1
    assert d1_h4.partial_aggregate_disagreement_count == 0
    assert d1_h4.samples[0].missing_child_open_utc == (
        "2026-10-20T20:00:00+00:00",
    )
    assert forensic.session_classification_admitted is False
    assert forensic.strict_crossframe_pass is False
    assert forensic.execution_permitted is False


def test_sparse_bucket_price_mismatch_is_visible_but_never_prices_printed():
    frames = daily_with_missing_20h_h4()
    parent = frames[ContextTimeframe.D1][0]
    frames[ContextTimeframe.D1] = (
        replace(parent, high=Decimal("3002")),
    )
    forensic = describe_crossframe_gaps(
        frames=frames, as_of=START + timedelta(days=2),
    )
    report = forensic.results[0]
    assert report.partial_aggregate_disagreement_count == 1
    assert report.samples[0].observed_aggregate_matches_parent is False
    output = str(asdict(report))
    assert "3002" not in output and "2999" not in output


def test_true_child_bar_misalignment_is_not_silenced():
    frames = daily_with_missing_20h_h4()
    h4 = list(frames[ContextTimeframe.H4])
    h4[2] = replace(h4[2], open_time=START + timedelta(hours=9))
    frames[ContextTimeframe.H4] = tuple(h4)
    result = describe_crossframe_gaps(
        frames=frames, as_of=START + timedelta(days=2)
    ).results[0]
    assert result.misaligned_child_slot_count == 1
    assert result.missing_child_slot_count == 2
    assert result.samples[0].malformed_child_open_utc == (
        "2026-10-20T09:00:00+00:00",
    )


def test_insufficient_coverage_and_unknown_pairs_never_pass():
    forensics = describe_crossframe_gaps(
        frames={}, as_of=START + timedelta(days=1)
    )
    assert all(x.no_full_overlap for x in forensics.results)
    assert not forensics.execution_permitted
    with pytest.raises(ValueError, match="never admit"):
        replace(forensics, strict_crossframe_pass=True)


def test_completely_observed_h4_children_are_recorded_as_full():
    frames = daily_with_missing_20h_h4()
    rows = tuple(
        bar(ContextTimeframe.H4, START + timedelta(hours=h))
        for h in (0, 4, 8, 12, 16, 20, 24)
    )
    frames[ContextTimeframe.H4] = rows
    result = describe_crossframe_gaps(
        frames=frames, as_of=START + timedelta(days=2)
    ).results[0]
    assert result.fully_covered_parent_buckets == 1
    assert result.partial_parent_buckets == 0
