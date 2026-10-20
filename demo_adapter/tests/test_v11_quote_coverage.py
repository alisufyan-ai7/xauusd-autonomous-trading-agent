"""Independent offline-only 4h quote-window coverage tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from scripts.v11_quote_coverage import (
    QuoteCoverageError,
    QuoteSample,
    evaluate_quote_coverage,
)

START = datetime(2026, 10, 19, 13, tzinfo=UTC)
END = START + timedelta(hours=4)
START_MS = int(START.timestamp() * 1000)


def sample(second: int) -> QuoteSample:
    return QuoteSample(START_MS + second * 1000, "2000.00", "2000.20")


@pytest.fixture(scope="module")
def complete() -> tuple[list[QuoteSample], list[QuoteSample]]:
    polls = [sample(n) for n in range(0, 4 * 3600, 5)]
    ticks = [sample(n) for n in range(0, 4 * 3600)]
    return polls, ticks


def test_full_four_hour_fixture_quote_only_not_cost_admitted(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    result = evaluate_quote_coverage(START, END, polls, ticks)
    assert result.status == "QUOTE_ONLY_EVIDENCE_NOT_CALIBRATION_ADMITTED"
    assert result.distinct_poll_slots == 2880
    assert result.eligible_minute_bins == 240
    assert result.tick_count == 14400
    assert result.maximum_spread_price == "0.20"
    assert result.current_adverse_cost_usd is None
    assert result.stressed_adverse_cost_usd is None


def test_missing_one_minute_block_fails(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    no_minute = [x for x in polls
                 if not START_MS + 720000 <= x.timestamp_ms < START_MS + 780000]
    with pytest.raises(QuoteCoverageError, match="completeness|coverage"):
        evaluate_quote_coverage(START, END, no_minute, ticks)


def test_synthetic_sparse_ticks_do_not_prove_one_second_moves(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    sparse = ticks[::2]
    with pytest.raises(QuoteCoverageError, match="tick pairs"):
        evaluate_quote_coverage(START, END, polls, sparse)


def test_unknown_market_tick_gap_fails(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    bad = [x for x in ticks
           if not START_MS + 100000 <= x.timestamp_ms < START_MS + 115000]
    with pytest.raises(QuoteCoverageError, match="tick gap"):
        evaluate_quote_coverage(START, END, polls, bad)


def test_inverted_or_unknown_tick_rejects_entire_window(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    corrupted = list(ticks)
    corrupted[50] = replace(corrupted[50], bid="2001")
    with pytest.raises(QuoteCoverageError, match="inverted"):
        evaluate_quote_coverage(START, END, polls, corrupted)


def test_duplicate_timestamp_rejected(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    with pytest.raises(QuoteCoverageError, match="duplicate"):
        evaluate_quote_coverage(START, END, polls, ticks + [ticks[-1]])


def test_no_interpolation_or_retroactive_shrinking(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    with pytest.raises(QuoteCoverageError, match="exact four-hour"):
        evaluate_quote_coverage(START, END - timedelta(seconds=1), polls, ticks)


def test_one_cent_spike_is_not_trimmed(
    complete: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = complete
    spiked = list(ticks)
    spiked[100] = replace(spiked[100], ask="2000.21")
    result = evaluate_quote_coverage(START, END, polls, spiked)
    assert result.maximum_spread_price == "0.21"
    assert result.max_adverse_tick_jump_price == "0.01"
