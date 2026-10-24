"""Source-gated classification of sampled sparse Exness XAUUSD UTC bar slots.

This does not repair missing bars, override crossframe FAIL_CLOSED, or claim
historical broker trading-session provenance. It refuses truncated samples
and any unknown/partial market-open intervals before drawing conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from xauusd_agent.features.v2_chronology_audit import SessionCalendarEvidence
from xauusd_agent.features.v2_crossframe_forensics import CrossframeForensics
from xauusd_agent.features.v2_market_context import ContextTimeframe

_PAIR_CHILD = {
    "D1_H4": ContextTimeframe.H4,
    "H4_H1": ContextTimeframe.H1,
    "H1_M15": ContextTimeframe.M15,
    "M15_M5": ContextTimeframe.M5,
    "M5_M1": ContextTimeframe.M1,
}


@dataclass(frozen=True, slots=True)
class SessionReconciliation:
    status: str
    reasons: tuple[str, ...]
    inspected_missing_child_slots: int
    fully_closed_slots: int
    open_or_partially_open_slots: int
    unknown_slots: int
    complete_forensic_inventory: bool
    official_session_admitted: bool = False
    crossframe_parity_admitted: bool = False
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if (
            self.official_session_admitted
            or self.crossframe_parity_admitted
            or self.execution_permitted
        ):
            raise ValueError("forensic inspection must not authorize source or trading")


def classify_sampled_sparse_slots(
    *,
    forensics: CrossframeForensics,
    calendar: SessionCalendarEvidence | None,
) -> SessionReconciliation:
    """A sampled diagnostic only; even closed slots don't imply global PASS."""
    reasons: set[str] = set()
    if (
        calendar is None
        or not calendar.source_verified
        or not calendar.session_coverage_complete
        or not calendar.weekly_sunday_utc_anchor_verified
    ):
        reasons.add("OFFICIAL_BROKER_SESSION_PROVENANCE_INCOMPLETE")
    inspected = closed = open_partial = unknown = 0
    complete = True
    for result in forensics.results:
        child_tf = _PAIR_CHILD.get(result.pair)
        if child_tf is None:
            reasons.add("UNREGISTERED_FRAME_PAIR")
            complete = False
            continue
        if len(result.samples) != result.partial_parent_buckets:
            reasons.add(f"{result.pair}_TRUNCATED_PARENT_SAMPLES")
            complete = False
        if sum(len(s.missing_child_open_utc) for s in result.samples) != (
            result.missing_child_slot_count
        ):
            reasons.add(f"{result.pair}_TRUNCATED_MISSING_SLOTS")
            complete = False
        for sample in result.samples:
            if (
                sample.observed_aggregate_matches_parent is not True
                or sample.malformed_child_open_utc
            ):
                reasons.add(f"{result.pair}_AGGREGATE_OR_ALIGNMENT_UNVERIFIED")
            for iso in sample.missing_child_open_utc:
                inspected += 1
                try:
                    start = datetime.fromisoformat(iso)
                    end = start + child_tf.duration
                except ValueError:
                    reasons.add("MALFORMED_UTC_SLOT")
                    unknown += 1
                    continue
                utc_offset = start.utcoffset()
                if (
                    calendar is None
                    or not calendar.source_verified
                    or not calendar.session_coverage_complete
                    or utc_offset is None
                    or utc_offset.total_seconds() != 0
                    or start < calendar.coverage_start_utc
                    or end > calendar.coverage_end_utc
                ):
                    unknown += 1
                    reasons.add("UTC_SLOT_NOT_COVERED_BY_VERIFIED_SOURCE")
                    continue
                if any(
                    max(start, interval.start_utc) < min(end, interval.end_utc)
                    for interval in calendar.open_intervals
                ):
                    open_partial += 1
                    reasons.add("MISSING_BAR_OVERLAPS_OPEN_SESSION")
                else:
                    closed += 1
    if not complete:
        status = "INCOMPLETE_DIAGNOSTIC_SAMPLE_FAIL_CLOSED"
    elif reasons:
        status = "SESSION_RECONCILIATION_UNVERIFIED"
    else:
        # Even complete verified closed-slot accounting remains a non-admitting
        # finding until separately reviewed, tested against live OHLC/volume,
        # and explicitly approved under the governed session policy.
        status = "SAMPLED_CLOSED_GAPS_ONLY_NOT_CHRONOLOGY_ADMISSION"
    return SessionReconciliation(
        status=status,
        reasons=tuple(sorted(reasons)),
        inspected_missing_child_slots=inspected,
        fully_closed_slots=closed,
        open_or_partially_open_slots=open_partial,
        unknown_slots=unknown,
        complete_forensic_inventory=complete,
    )
