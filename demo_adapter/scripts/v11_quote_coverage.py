"""Strict OFFLINE coverage and quote-proxy calculator for v1.1.

Accepts synthetic or later separately captured PRIVATE raw read-only samples.
No MT5 import, credentials, network calls, broker capability, or admission.
A measured quote proxy is not realized execution slippage.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal


class QuoteCoverageError(ValueError):
    """No admitted source costs can be computed from inadequate coverage."""


@dataclass(frozen=True)
class QuoteSample:
    timestamp_ms: int
    bid: str
    ask: str


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
        raise QuoteCoverageError("raw price must be decimal string")
    try:
        price = Decimal(raw)
    except Exception as exc:
        raise QuoteCoverageError("bad raw decimal price") from exc
    if not price.is_finite() or price <= 0:
        raise QuoteCoverageError("unknown or nonpositive raw price")
    return price


def evaluate_quote_coverage(
    start_utc: datetime,
    end_utc: datetime,
    polls: list[QuoteSample],
    ticks: list[QuoteSample],
) -> QuoteCoverageResult:
    """Reject gaps instead of interpolating or ignoring unfavorable segments.

    All timestamps are UTC epoch milliseconds. The immutable accepted run
    manifest and read-only source SHA must be authenticated by a separate
    verifier; this function NEVER emits USD costs or an admission decision.
    """
    if (start_utc.tzinfo is None or start_utc.utcoffset() != timedelta(0)
            or end_utc - start_utc != timedelta(hours=4)):
        raise QuoteCoverageError("expected exact four-hour UTC registration")
    start_ms = int(start_utc.astimezone(UTC).timestamp() * 1000)
    end_ms = int(end_utc.astimezone(UTC).timestamp() * 1000)
    total_slots = 2880
    poll_slots: set[int] = set()
    minute_bins: set[int] = set()
    spread_max = Decimal(0)

    def parsed(sample: QuoteSample) -> tuple[Decimal, Decimal]:
        if type(sample.timestamp_ms) is not int:
            raise QuoteCoverageError("event timestamp not a true integer millis")
        if not start_ms <= sample.timestamp_ms < end_ms:
            raise QuoteCoverageError("quote outside prospectively registered window")
        bid, ask = _price(sample.bid), _price(sample.ask)
        if bid >= ask:
            raise QuoteCoverageError("inverted or nonpositive spread")
        return bid, ask

    for poll in polls:
        bid, ask = parsed(poll)
        slot = (poll.timestamp_ms - start_ms) // 5000
        minute = (poll.timestamp_ms - start_ms) // 60000
        poll_slots.add(slot)
        minute_bins.add(minute)
        spread_max = max(spread_max, ask - bid)

    if len(poll_slots) * 100 < total_slots * 99 or len(minute_bins) != 240:
        raise QuoteCoverageError("missing poll completeness or one-minute coverage")

    indexed: dict[int, tuple[Decimal, Decimal]] = {}
    times: list[int] = []
    for tick in ticks:
        bid, ask = parsed(tick)
        if tick.timestamp_ms in indexed:
            raise QuoteCoverageError("duplicate tick timestamp, sequencing unknown")
        indexed[tick.timestamp_ms] = bid, ask
        times.append(tick.timestamp_ms)
        spread_max = max(spread_max, ask - bid)
    if times != sorted(times):
        raise QuoteCoverageError("unsorted genuine tick timestamps")
    if not times:
        raise QuoteCoverageError("empty tick source")

    # No long unobserved tick intervals. This is an explicit conservative
    # engineering threshold for the initial liquid-window sample, not a claim
    # about future market microstructure.
    if times[0] - start_ms > 5000 or end_ms - times[-1] > 5000:
        raise QuoteCoverageError("uncovered starting or ending tick interval")
    if any(b - a > 5000 for a, b in zip(times, times[1:])):
        raise QuoteCoverageError("unclassified tick gap above five seconds")

    maxima = {1: Decimal(0), 5: Decimal(0), 30: Decimal(0)}
    qualified: dict[int, set[int]] = {1: set(), 5: set(), 30: set()}
    gap_max = Decimal(0)
    previous: tuple[Decimal, Decimal] | None = None
    for timestamp in times:
        bid, ask = indexed[timestamp]
        if previous is not None:
            old_bid, old_ask = previous
            gap_max = max(gap_max, ask - old_ask, old_bid - bid)
        previous = bid, ask
        bucket = (timestamp - start_ms) // (10 * 60 * 1000)
        for horizon in (1, 5, 30):
            successor = indexed.get(timestamp + horizon * 1000)
            if successor is None:
                continue
            # Only a pair entirely contained in the same 10-minute block
            # meets that block's horizon-specific coverage requirement.
            if (timestamp + horizon * 1000 - start_ms) // (10 * 60 * 1000) != bucket:
                continue
            later_bid, later_ask = successor
            maxima[horizon] = max(maxima[horizon], later_ask - ask, bid - later_bid)
            qualified[horizon].add(bucket)
    if any(len(qualified[h]) != 24 for h in (1, 5, 30)):
        raise QuoteCoverageError("insufficient true tick pairs in 10-minute blocks")

    return QuoteCoverageResult(
        status="QUOTE_ONLY_EVIDENCE_NOT_CALIBRATION_ADMITTED",
        distinct_poll_slots=len(poll_slots),
        eligible_minute_bins=len(minute_bins),
        tick_count=len(times),
        maximum_spread_price=str(spread_max),
        max_adverse_move_price_1s=str(maxima[1]),
        max_adverse_move_price_5s=str(maxima[5]),
        max_adverse_move_price_30s=str(maxima[30]),
        max_adverse_tick_jump_price=str(gap_max),
    )
