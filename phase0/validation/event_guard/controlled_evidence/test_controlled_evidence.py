from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
EVENT_GUARD = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EVENT_GUARD))

from controlled_evidence import (
    SafeFrame, decision_state, dol_holiday_events, evaluate_transition,
    recovery_is_complete,
)
from event_guard_oracle import Event

UTC = timezone.utc


def at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def event(source: str, source_id: str, taxonomy: str, when: str,
          tier: str = "TIER_1", status: str = "SCHEDULED") -> Event:
    return Event(source, source_id, taxonomy, at(when), "UTC", taxonomy, tier, status)


def frame(observed: str, source: str, events=(), healthy=True, digest="a" * 64):
    return SafeFrame(at(observed), source, digest, healthy, tuple(events))


class ControlledEvidenceTests(unittest.TestCase):
    def test_event_added_inside_prelock_locks_immediately(self):
        before = frame("2026-09-10T12:05:00Z", "BLS_ICS")
        added = event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T12:30:00Z")
        after = frame("2026-09-10T12:06:00Z", "BLS_ICS", [added], digest="b" * 64)
        result = evaluate_transition(before, after)
        self.assertEqual(("ADDED",), result.revision_kinds)
        self.assertEqual("PRE_LOCK", decision_state(after, at("2026-09-10T12:06:00Z")))

    def test_move_retains_both_old_and_new_windows(self):
        old = event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T12:30:00Z")
        new = event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T13:30:00Z")
        before = frame("2026-09-10T11:50:00Z", "BLS_ICS", [old])
        after = frame("2026-09-10T12:05:00Z", "BLS_ICS", [new], digest="b" * 64)
        result = evaluate_transition(before, after)
        self.assertIn("MOVED", result.revision_kinds)
        self.assertEqual(2, len(result.effective_events))
        effective = frame("2026-09-10T12:05:00Z", "BLS_ICS", result.effective_events,
                          digest="c" * 64)
        self.assertEqual("PRE_LOCK", decision_state(effective, at("2026-09-10T12:05:00Z")))
        self.assertEqual("PRE_LOCK", decision_state(effective, at("2026-09-10T13:05:00Z")))

    def test_unexplained_future_disappearance_locks(self):
        old = event("BEA_JSON", "pce", "US_PCE", "2026-09-25T12:30:00Z")
        result = evaluate_transition(
            frame("2026-09-01T10:00:00Z", "BEA_JSON", [old]),
            frame("2026-09-01T11:00:00Z", "BEA_JSON", [], digest="b" * 64),
        )
        self.assertEqual("LOCKED", result.status)
        self.assertIn("UNEXPLAINED_DISAPPEARANCE", result.revision_kinds)

    def test_outage_locks_even_with_cached_future_event(self):
        cached = event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T12:30:00Z")
        outage = frame("2026-09-09T11:00:00Z", "BLS_ICS", [cached], healthy=False)
        self.assertEqual("SOURCE_UNHEALTHY", decision_state(outage, at("2026-09-09T11:00:00Z")))

    def test_fetch_recovery_without_full_horizon_remains_locked(self):
        bls = frame("2026-08-23T12:00:00Z", "BLS_ICS", [
            event("BLS_ICS", "jobs", "US_EMPLOYMENT", "2026-09-04T12:30:00Z"),
            event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T12:30:00Z"),
        ])
        ok, reason = recovery_is_complete(at("2026-08-23T12:00:00Z"), (bls,), bls.events)
        self.assertFalse(ok)
        self.assertEqual("HORIZON_INCOMPLETE", reason)

    def test_recovery_requires_and_accepts_complete_authoritative_horizon(self):
        events = (
            event("BLS_ICS", "jobs", "US_EMPLOYMENT", "2026-09-04T12:30:00Z"),
            event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T12:30:00Z"),
            event("BEA_JSON", "pce", "US_PCE", "2026-08-26T12:30:00Z"),
            event("FED_CALENDAR", "statement", "FOMC_STATEMENT", "2026-09-16T18:00:00Z"),
            event("FED_CALENDAR", "press", "FOMC_PRESS_CONFERENCE", "2026-09-16T18:30:00Z"),
            event("FED_CALENDAR", "minutes", "FOMC_MINUTES", "2026-10-07T18:00:00Z"),
            event("DOL_UI", "claims", "US_JOBLESS_CLAIMS", "2026-08-27T12:30:00Z", "TIER_2"),
        )
        frames = tuple(
            frame("2026-08-23T12:00:00Z", source,
                  [item for item in events if item.source == source], digest=character * 64)
            for source, character in (
                ("BLS_ICS", "a"), ("BEA_JSON", "b"),
                ("FED_CALENDAR", "c"), ("DOL_UI", "d"),
            )
        )
        self.assertEqual(
            (True, "RECOVERY_CONFORMING"),
            recovery_is_complete(at("2026-08-23T12:00:00Z"), frames, events),
        )

    def test_unhealthy_cancellation_cannot_unlock(self):
        cancelled = event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T12:30:00Z",
                          status="CANCELLED")
        stale = frame("2026-09-10T12:05:00Z", "BLS_ICS", [cancelled], healthy=False)
        self.assertEqual("SOURCE_UNHEALTHY", decision_state(stale, at("2026-09-10T12:05:00Z")))

    def test_dol_holiday_exception_replaces_thursday_and_keeps_winter_utc(self):
        html = """<html><p>Publication Schedule: The UI Weekly Claims News Release is
        published each week on Thursday morning at 8:30am EST. Exceptions to this
        schedule occur when a Thursday falls on a Federal Holiday.</p>
        <table><tr><th>Release Date</th><th>Release Time</th></tr>
        <tr><td>Wednesday, November 25, 2026</td><td>8:30 AM EST</td></tr></table></html>"""
        events = dol_holiday_events(html, at("2026-11-20T00:00:00Z"), 20)
        times = {item.scheduled_utc for item in events}
        self.assertIn(at("2026-11-25T13:30:00Z"), times)
        self.assertIn(at("2026-12-03T13:30:00Z"), times)
        self.assertNotIn(at("2026-11-26T13:30:00Z"), times)

    def test_frame_rejects_private_or_malformed_hash_metadata(self):
        with self.assertRaises(ValueError):
            frame("2026-08-23T12:00:00Z", "BLS_ICS", digest="account-123")

    def test_transition_digest_is_deterministic(self):
        prior = frame("2026-08-23T12:00:00Z", "DOL_UI")
        current = frame("2026-08-23T13:00:00Z", "DOL_UI", digest="b" * 64)
        self.assertEqual(
            evaluate_transition(prior, current).digest_sha256,
            evaluate_transition(prior, current).digest_sha256,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
