"""Synthetic-only v1.1-T1 time_msc, source order and fixed tolerance protocol."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from scripts.v11_quote_coverage import (
    MATCH_TOLERANCE_MS,
    QuoteCoverageError,
    QuoteSample,
    evaluate_quote_coverage,
)

START = datetime(2026, 10, 19, 13, tzinfo=UTC)
END = START + timedelta(hours=4)
BASE_MS = int(START.timestamp() * 1000)


@pytest.fixture(scope="module")
def full() -> tuple[list[QuoteSample], list[QuoteSample]]:
    polls = [
        QuoteSample(BASE_MS + 5000 * i, "2000.00", "2000.20")
        for i in range(2880)
    ]
    ticks = [
        QuoteSample(BASE_MS + i * 1000, "2000.00", "2000.20", i, 134)
        for i in range(14400)
    ]
    return polls, ticks


def check(
    polls: list[QuoteSample], ticks: list[QuoteSample]
) -> object:
    return evaluate_quote_coverage(
        START, END, polls, ticks, require_source_ordinal=True
    )


def test_registered_tolerance_fixed_to_quarter_second() -> None:
    assert MATCH_TOLERANCE_MS == 250


def test_same_millisecond_distinct_ticks_preserve_worst_jump(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    derived = list(ticks)
    # Two distinct source rows with the same UTC event time. Both retained.
    original = derived[100]
    derived.insert(
        101, QuoteSample(original.timestamp_ms, "1999.97", "2000.45", 101, 134)
    )
    for i in range(102, len(derived)):
        derived[i] = replace(derived[i], source_ordinal=i)
    result = check(polls, derived)
    assert result.tick_count == 14401
    assert result.maximum_spread_price == "0.48"
    assert result.max_adverse_tick_jump_price == "0.25"


def test_duplicate_ms_without_sequence_rejects_source(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    old = [replace(t, source_ordinal=None) for t in ticks]
    old.insert(101, old[100])
    with pytest.raises(QuoteCoverageError, match="sequence"):
        check(polls, old)


def test_adverse_match_at_plus_250_ms_included(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    derived = list(ticks)
    base = derived[100]
    # Replace the 101-second tick with a 101.250-second tick, preserving
    # monotonic order and registering the fixed tolerance before any data.
    derived[101] = replace(derived[101], timestamp_ms=base.timestamp_ms + 1250,
                           ask="2000.75")
    result = check(polls, derived)
    assert result.max_adverse_move_price_1s == "0.55"


def test_251_ms_offset_cannot_be_used_as_target_pair(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    derived = list(ticks)
    # At 101.251s the spike is outside the 100.000s start tick's 1s
    # horizon band, but it must still contribute to spread and jump maxima.
    derived[101] = replace(derived[101], timestamp_ms=BASE_MS + 101251,
                           ask="2000.75")
    result = check(polls, derived)
    assert result.maximum_spread_price == "0.75"
    assert result.max_adverse_tick_jump_price == "0.55"
    # It may still be in a valid +/-250-ms horizon from a different source
    # tick; the source is never discarded or retroactively trimmed.


def test_ordinal_reversal_rejected_without_timestamp_sort(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    corrupt = list(ticks)
    corrupt[100] = replace(corrupt[100], source_ordinal=99)
    with pytest.raises(QuoteCoverageError, match="sequence|ordinal"):
        check(polls, corrupt)


def test_out_of_order_ms_rejected_even_with_ordinals(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    corrupt = list(ticks)
    corrupt[100] = replace(corrupt[100], timestamp_ms=BASE_MS + 105000)
    with pytest.raises(QuoteCoverageError, match="not monotonic"):
        check(polls, corrupt)


def test_unclassified_source_gap_never_interpolated(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    # Build an internally consistent stream whose original source genuinely
    # observed no ticks for 10 seconds; reindex its synthetic source ordinals.
    missing = [t for t in ticks if not BASE_MS + 100000 <= t.timestamp_ms <
               BASE_MS + 110000]
    bad = [replace(t, source_ordinal=i) for i, t in enumerate(missing)]
    with pytest.raises(QuoteCoverageError, match="gap"):
        check(polls, bad)


def test_30s_horizon_crosses_10m_for_maxima_but_not_bin_coverage(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    modified = list(ticks)
    # At 599 s -> 629 s, pair straddles a 10-minute block; its adverse
    # value must still appear in the overall horizon maximum.
    modified[629] = replace(modified[629], ask="2001.80")
    result = check(polls, modified)
    assert result.max_adverse_move_price_30s == "1.60"


def test_end_window_cannot_expand_to_observe_better_quotes(
    full: tuple[list[QuoteSample], list[QuoteSample]],
) -> None:
    polls, ticks = full
    with pytest.raises(QuoteCoverageError, match="exact four-hour"):
        evaluate_quote_coverage(
            START, END + timedelta(milliseconds=1), polls, ticks,
            require_source_ordinal=True,
        )
