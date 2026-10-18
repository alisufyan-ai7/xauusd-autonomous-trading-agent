"""Prospectively frozen v1.1 quote-only tick protocol. No MT5 import.

MT5 time_msc is UTC event time, and distinct records can share milliseconds.
Arrival/source sequence is preserved; no deduplication, sorting, interpolation
or retrospective selection. The observed worst quote move is not a fill bound.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

# Candidate engineering protocol v1.1-T1: frozen BEFORE broker capture.
HORIZONS_SECONDS = (1, 5, 30)
MATCH_TOLERANCE_MS = 250
MAX_INTERTICK_GAP_MS = 5000
TOTAL_EXPECTED_POLL_SLOTS = 2880
MIN_POLL_COMPLETENESS = Decimal("0.99")


class QuoteCoverageError(ValueError):
    """Missing/ambiguous evidence. Never return a cost admission."""


@dataclass(frozen=True)
class QuoteSample:
    timestamp_ms: int
    bid: str
    ask: str
    source_ordinal: int | None = None
    flags: int | None = None


@dataclass(frozen=True)
class QuoteCoverageResult:
    status: str
    distinct_poll_slots: int
    eligible_minute_bins: int
    tick_count: int
    maximum_spread_price: str
    max_adverse_move_price_1s: str
    max_adverse_move_price_5s: str
    max_adverse_move_price_30s: str
    max_adverse_tick_jump_price: str
    current_adverse_cost_usd: None = None
    stressed_adverse_cost_usd: None = None


def _price(raw: str) -> Decimal:
    if type(raw) is not str:
        raise QuoteCoverageError("raw prices must be exact decimal strings")
    try:
        value = Decimal(raw)
    except Exception as exc:
        raise QuoteCoverageError("invalid raw quote") from exc
    if not value.is_finite() or value <= 0:
        raise QuoteCoverageError("missing or nonpositive quote")
    return value


def evaluate_quote_coverage(
    start_utc: datetime,
    end_utc: datetime,
    polls: list[QuoteSample],
    ticks: list[QuoteSample],
    *,
    require_source_ordinal: bool = False,
) -> QuoteCoverageResult:
    """Quote-only maxima with deterministic ±250 ms matching, no fallback.

    For each source tick at t and horizon h, consider *all* subsequent true
    ticks with time_msc in [t+h-250ms, t+h+250ms], inclusive. Maximize adverse
    ASK rise and BID decline separately over this full candidate set. A pair
    qualifies a ten-minute bin only if both endpoints fall within the bin;
    cross-bin pairs still contribute to global maxima. Equal-millisecond
    source ticks are distinct if source ordinals prove preserved read order.
    No midpoint, no as-of estimate, no crossing a >5-second unknown gap.
    """
    if (
        start_utc.tzinfo is None or end_utc.tzinfo is None
        or start_utc.utcoffset() != timedelta(0)
        or end_utc.utcoffset() != timedelta(0)
        or end_utc - start_utc != timedelta(hours=4)
    ):
        raise QuoteCoverageError("expected exact four-hour UTC registration")
    start_ms = int(start_utc.astimezone(UTC).timestamp() * 1000)
    end_ms = int(end_utc.astimezone(UTC).timestamp() * 1000)
    slots: set[int] = set()
    minutes: set[int] = set()
    max_spread = Decimal(0)

    def quote(record: QuoteSample) -> tuple[Decimal, Decimal]:
        if type(record.timestamp_ms) is not int:
            raise QuoteCoverageError("noninteger UTC millisecond timestamp")
        if not start_ms <= record.timestamp_ms < end_ms:
            raise QuoteCoverageError("tick outside prospectively registered window")
        bid, ask = _price(record.bid), _price(record.ask)
        if bid >= ask:
            raise QuoteCoverageError("inverted or invalid bid/ask")
        if record.flags is not None and (
            type(record.flags) is not int or record.flags < 0
        ):
            raise QuoteCoverageError("invalid raw tick flags")
        return bid, ask

    for poll in polls:
        bid, ask = quote(poll)
        if poll.source_ordinal is not None:
            raise QuoteCoverageError("observer polls cannot impersonate source tick order")
        elapsed = poll.timestamp_ms - start_ms
        slots.add(elapsed // 5000)
        minutes.add(elapsed // 60000)
        max_spread = max(max_spread, ask - bid)

    if (
        Decimal(len(slots)) / Decimal(TOTAL_EXPECTED_POLL_SLOTS)
        < MIN_POLL_COMPLETENESS or len(minutes) != 240
    ):
        raise QuoteCoverageError("missing poll completeness or one-minute coverage")

    if not ticks:
        raise QuoteCoverageError("empty source tick stream")
    times: list[int] = []
    bids: list[Decimal] = []
    asks: list[Decimal] = []
    last_ordinal = -1
    last_ms = -1
    for tick in ticks:
        bid, ask = quote(tick)
        if tick.timestamp_ms < last_ms:
            raise QuoteCoverageError("source order not monotonic by time_msc")
        if last_ms == tick.timestamp_ms and last_ordinal < 0:
            raise QuoteCoverageError("duplicate-millisecond prior source sequence unknown")
        if (
            require_source_ordinal or last_ms == tick.timestamp_ms
        ) and (type(tick.source_ordinal) is not int
               or tick.source_ordinal <= last_ordinal):
            raise QuoteCoverageError("duplicate-millisecond source sequence unknown")
        if tick.source_ordinal is not None:
            if type(tick.source_ordinal) is not int or tick.source_ordinal <= last_ordinal:
                raise QuoteCoverageError("source ordinal not strictly increasing")
            last_ordinal = tick.source_ordinal
        times.append(tick.timestamp_ms)
        bids.append(bid)
        asks.append(ask)
        last_ms = tick.timestamp_ms
        max_spread = max(max_spread, ask - bid)

    if times[0] - start_ms > MAX_INTERTICK_GAP_MS:
        raise QuoteCoverageError("unclassified opening tick gap")
    if end_ms - times[-1] > MAX_INTERTICK_GAP_MS:
        raise QuoteCoverageError("unclassified closing tick gap")
    if any(b - a > MAX_INTERTICK_GAP_MS
           for a, b in zip(times, times[1:], strict=False)):
        raise QuoteCoverageError("unclassified tick gap above five seconds")

    moves = {1: Decimal(0), 5: Decimal(0), 30: Decimal(0)}
    covered: dict[int, set[int]] = {1: set(), 5: set(), 30: set()}
    max_gap = Decimal(0)

    for i, start_time in enumerate(times):
        if i:
            # Adjacent original rows, including same-ms ticks; no favorable
            # elimination of duplicates or cross-boundary quote jumps.
            max_gap = max(
                max_gap, asks[i] - asks[i - 1], bids[i - 1] - bids[i]
            )
        bucket = (start_time - start_ms) // (10 * 60 * 1000)
        for horizon in HORIZONS_SECONDS:
            target = start_time + horizon * 1000
            lo = bisect_left(times, target - MATCH_TOLERANCE_MS, i + 1)
            hi = bisect_right(times, target + MATCH_TOLERANCE_MS, lo)
            for j in range(lo, hi):
                moves[horizon] = max(
                    moves[horizon],
                    asks[j] - asks[i],
                    bids[i] - bids[j],
                )
                if (times[j] - start_ms) // (10 * 60 * 1000) == bucket:
                    covered[horizon].add(bucket)

    if any(len(covered[h]) != 24 for h in HORIZONS_SECONDS):
        raise QuoteCoverageError("insufficient true timestamped tick pairs in 10-minute blocks")

    return QuoteCoverageResult(
        status="QUOTE_ONLY_EVIDENCE_NOT_CALIBRATION_ADMITTED",
        distinct_poll_slots=len(slots),
        eligible_minute_bins=len(minutes),
        tick_count=len(times),
        maximum_spread_price=str(max_spread),
        max_adverse_move_price_1s=str(moves[1]),
        max_adverse_move_price_5s=str(moves[5]),
        max_adverse_move_price_30s=str(moves[30]),
        max_adverse_tick_jump_price=str(max_gap),
    )
