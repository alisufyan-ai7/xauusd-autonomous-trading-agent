from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from xauusd_agent.features.v2_chronology_audit import (
    SessionCalendarEvidence,
    SessionInterval,
)
from xauusd_agent.features.v2_crossframe_forensics import (
    CrossframeForensics,
    MissingBucketSample,
    PairGapForensics,
)
from xauusd_agent.features.v2_sparse_session_reconciliation import (
    classify_sampled_sparse_slots,
)

START = datetime(2026, 9, 22, tzinfo=UTC)


def report(*, samples=1, missing=1, match=True, misaligned=False):
    sample = MissingBucketSample(
        parent_open_utc=START.isoformat(),
        parent_timeframe="H4", child_timeframe="H1",
        expected_child_count=4, observed_child_count=3,
        missing_child_open_utc=((START + timedelta(hours=1)).isoformat(),),
        malformed_child_open_utc=(
            ((START + timedelta(minutes=30)).isoformat(),)
            if misaligned else ()
        ),
        observed_aggregate_matches_parent=match,
    )
    return CrossframeForensics((
        PairGapForensics(
            pair="H4_H1", fully_covered_parent_buckets=108,
            partial_parent_buckets=samples, zero_child_parent_buckets=0,
            partial_aggregate_match_count=int(match),
            partial_aggregate_disagreement_count=int(not match),
            missing_child_slot_count=missing,
            misaligned_child_slot_count=int(misaligned),
            no_full_overlap=False, samples=(sample,),
        ),
    ))


def calendar(*, open_intervals=None, verified=True):
    return SessionCalendarEvidence(
        broker_session_source_sha256="a" * 64,
        revision="SYNTHETIC_NOT_EXNESS_ADMISSION",
        coverage_start_utc=START - timedelta(days=1),
        coverage_end_utc=START + timedelta(days=1),
        open_intervals=tuple(
            open_intervals if open_intervals is not None else (
                SessionInterval(
                    START + timedelta(hours=3),
                    START + timedelta(hours=4),
                ),
            )
        ),
        source_verified=verified,
        session_coverage_complete=True,
        weekly_sunday_utc_anchor_verified=True,
    )


def test_source_backed_closed_slot_remains_nonadmitting():
    result = classify_sampled_sparse_slots(
        forensics=report(), calendar=calendar()
    )
    assert result.status == "SAMPLED_CLOSED_GAPS_ONLY_NOT_CHRONOLOGY_ADMISSION"
    assert result.inspected_missing_child_slots == 1
    assert result.fully_closed_slots == 1
    assert result.open_or_partially_open_slots == 0
    assert result.crossframe_parity_admitted is False
    assert result.official_session_admitted is False
    assert result.execution_permitted is False


def test_partial_overlap_with_open_session_refuses_closed_classification():
    result = classify_sampled_sparse_slots(
        forensics=report(), calendar=calendar(open_intervals=(
            SessionInterval(
                START + timedelta(hours=1, minutes=30),
                START + timedelta(hours=2),
            ),
        )),
    )
    assert result.status == "SESSION_RECONCILIATION_UNVERIFIED"
    assert result.open_or_partially_open_slots == 1
    assert "MISSING_BAR_OVERLAPS_OPEN_SESSION" in result.reasons


def test_unverified_calendar_cannot_make_absent_hour_closed():
    result = classify_sampled_sparse_slots(
        forensics=report(), calendar=calendar(verified=False)
    )
    assert result.status == "SESSION_RECONCILIATION_UNVERIFIED"
    assert result.unknown_slots == 1
    assert "OFFICIAL_BROKER_SESSION_PROVENANCE_INCOMPLETE" in result.reasons
    assert not result.execution_permitted


def test_real_forensic_samples_are_truncated_and_never_admitted():
    # Owner H4/H1 snapshot: 26 partial buckets, but only 6 sampled;
    # D1/H4: 9 partial buckets, only 6 sampled. Either fails exhaustive proof.
    for partial_buckets, expected_missing in ((26, 38), (9, 45)):
        result = classify_sampled_sparse_slots(
            forensics=report(
                samples=partial_buckets, missing=expected_missing,
            ),
            calendar=calendar(),
        )
        assert result.status == "INCOMPLETE_DIAGNOSTIC_SAMPLE_FAIL_CLOSED"
        assert not result.complete_forensic_inventory
        assert any("TRUNCATED" in x for x in result.reasons)


def test_misaligned_or_disagreeing_partial_aggregates_cannot_pass():
    for forensic in (report(match=False), report(misaligned=True)):
        result = classify_sampled_sparse_slots(
            forensics=forensic, calendar=calendar()
        )
        assert result.status == "SESSION_RECONCILIATION_UNVERIFIED"
        assert any("AGGREGATE_OR_ALIGNMENT" in x for x in result.reasons)


def test_forged_trading_authorization_dto_rejected():
    original = classify_sampled_sparse_slots(
        forensics=report(), calendar=calendar()
    )
    with pytest.raises(ValueError, match="must not authorize"):
        replace(original, execution_permitted=True)
    with pytest.raises(ValueError, match="must not authorize"):
        replace(original, crossframe_parity_admitted=True)
