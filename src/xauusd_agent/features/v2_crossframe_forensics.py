"""Privacy-preserving causal bucket forensics for Exness DEMO read-only bars.

This diagnostic does NOT relax the strict crossframe oracle, and never calls a
broker. Missing lower bars are NOT presumed to be scheduled closures. Samples
contain UTC timestamps/counts only, with no raw price/volume/account data.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from xauusd_agent.features.v2_market_context import ContextBar, ContextTimeframe
from xauusd_agent.market.models import _require_utc

_PAIRS = (
    (ContextTimeframe.D1, ContextTimeframe.H4),
    (ContextTimeframe.H4, ContextTimeframe.H1),
    (ContextTimeframe.H1, ContextTimeframe.M15),
    (ContextTimeframe.M15, ContextTimeframe.M5),
    (ContextTimeframe.M5, ContextTimeframe.M1),
)
_SAMPLE_LIMIT = 6


@dataclass(frozen=True, slots=True)
class MissingBucketSample:
    parent_open_utc: str
    parent_timeframe: str
    child_timeframe: str
    expected_child_count: int
    observed_child_count: int
    missing_child_open_utc: tuple[str, ...]
    malformed_child_open_utc: tuple[str, ...]
    observed_aggregate_matches_parent: bool | None


@dataclass(frozen=True, slots=True)
class PairGapForensics:
    pair: str
    fully_covered_parent_buckets: int
    partial_parent_buckets: int
    zero_child_parent_buckets: int
    partial_aggregate_match_count: int
    partial_aggregate_disagreement_count: int
    missing_child_slot_count: int
    misaligned_child_slot_count: int
    no_full_overlap: bool
    samples: tuple[MissingBucketSample, ...]


@dataclass(frozen=True, slots=True)
class CrossframeForensics:
    results: tuple[PairGapForensics, ...]
    session_classification_admitted: bool = False
    strict_crossframe_pass: bool = False
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if (
            self.session_classification_admitted
            or self.strict_crossframe_pass
            or self.execution_permitted
        ):
            raise ValueError("read-only sparse diagnostics never admit parity or trading")


def describe_crossframe_gaps(
    *,
    frames: Mapping[ContextTimeframe, Sequence[ContextBar]],
    as_of: datetime,
) -> CrossframeForensics:
    """Return only missing-bucket time/count metadata, never price or raw candles."""
    _require_utc(as_of, "as_of")
    results = []
    for parent_tf, child_tf in _PAIRS:
        parents = frames.get(parent_tf, ())
        children = frames.get(child_tf, ())
        pair = f"{parent_tf.value}_{child_tf.value}"
        if not parents or not children:
            results.append(PairGapForensics(
                pair, 0, 0, 0, 0, 0, 0, 0, True, (),
            ))
            continue
        child_opens = [bar.open_time for bar in children]
        start, end = children[0].open_time, children[-1].close_time
        expected_count = int(parent_tf.duration / child_tf.duration)
        if expected_count * child_tf.duration != parent_tf.duration:
            raise ValueError("crossframe ratio is nonintegral")
        full = partial = zero = match = disagree = missing = misaligned = 0
        samples: list[MissingBucketSample] = []
        for parent in parents:
            if (
                parent.open_time < start or parent.close_time > end
                or parent.close_time > as_of
            ):
                continue
            first = bisect_left(child_opens, parent.open_time)
            last = bisect_left(child_opens, parent.close_time)
            parts = children[first:last]
            actual = {bar.open_time: bar for bar in parts}
            slots = tuple(
                parent.open_time + offset * child_tf.duration
                for offset in range(expected_count)
            )
            absent = tuple(ts for ts in slots if ts not in actual)
            malformed = tuple(ts for ts in actual if ts not in slots)
            if not absent and not malformed and len(parts) == expected_count:
                full += 1
                continue
            partial += 1
            if not parts:
                zero += 1
            missing += len(absent)
            misaligned += len(malformed)
            equivalent = None
            if parts:
                equivalent = (
                    parent.open == parts[0].open
                    and parent.close == parts[-1].close
                    and parent.high == max(item.high for item in parts)
                    and parent.low == min(item.low for item in parts)
                    and parent.tick_volume == sum(item.tick_volume for item in parts)
                )
                if equivalent:
                    match += 1
                else:
                    disagree += 1
            if len(samples) < _SAMPLE_LIMIT:
                samples.append(MissingBucketSample(
                    parent_open_utc=parent.open_time.isoformat(),
                    parent_timeframe=parent_tf.value,
                    child_timeframe=child_tf.value,
                    expected_child_count=expected_count,
                    observed_child_count=len(parts),
                    missing_child_open_utc=tuple(
                        item.isoformat() for item in absent[:_SAMPLE_LIMIT]
                    ),
                    malformed_child_open_utc=tuple(
                        item.isoformat() for item in malformed[:_SAMPLE_LIMIT]
                    ),
                    observed_aggregate_matches_parent=equivalent,
                ))
        results.append(PairGapForensics(
            pair=pair, fully_covered_parent_buckets=full,
            partial_parent_buckets=partial,
            zero_child_parent_buckets=zero,
            partial_aggregate_match_count=match,
            partial_aggregate_disagreement_count=disagree,
            missing_child_slot_count=missing,
            misaligned_child_slot_count=misaligned,
            no_full_overlap=full + partial == 0,
            samples=tuple(samples),
        ))
    return CrossframeForensics(tuple(results))
