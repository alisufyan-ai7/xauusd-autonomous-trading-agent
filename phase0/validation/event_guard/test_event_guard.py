import json
from pathlib import Path
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent))
from event_guard_oracle import (
    Event, entry_allowed, fred_date_cross_check, guard_state, local_to_utc,
    parse_bea_json, parse_fed_monthly_html, parse_ics, parse_official_rows,
    reconcile_authoritative,
)

UTC = timezone.utc


def at(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class EventGuardTests(unittest.TestCase):
    def test_est_and_edt_normalize_differently(self):
        self.assertEqual(at("2026-01-09T13:30:00Z"), local_to_utc("2026-01-09", "08:30"))
        self.assertEqual(at("2026-07-09T12:30:00Z"), local_to_utc("2026-07-09", "08:30"))

    def test_missing_verified_timezone_is_invalid(self):
        with self.assertRaises(ValueError):
            local_to_utc("2026-07-09", "08:30", "EST")

    def test_bls_style_ics_unfolds_and_filters(self):
        text = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:bls-1
SUMMARY:Employment Situation for June 2026
DTSTART:20260702T123000Z
END:VEVENT
BEGIN:VEVENT
UID:bls-2
SUMMARY:Consumer Price In
 dex for June 2026
DTSTART:20260714T123000Z
END:VEVENT
BEGIN:VEVENT
UID:bls-ignore
SUMMARY:Regional price release
DTSTART:20260715T123000Z
END:VEVENT
END:VCALENDAR
"""
        events = parse_ics(text, "BLS_ICS")
        self.assertEqual(["US_EMPLOYMENT", "US_CPI"], [e.taxonomy for e in events])
        self.assertTrue(all(e.source_timezone == "UTC" for e in events))

    def test_ics_without_zone_is_rejected(self):
        text = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:x
SUMMARY:Employment Situation
DTSTART:20260702T083000
END:VEVENT
END:VCALENDAR
"""
        with self.assertRaises(ValueError):
            parse_ics(text, "BLS_ICS")

    def test_bls_windows_eastern_aliases_are_dst_safe(self):
        text = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:winter
SUMMARY:Employment Situation
DTSTART;TZID=Eastern Standard Time:20260109T083000
END:VEVENT
BEGIN:VEVENT
UID:summer
SUMMARY:Consumer Price Index
DTSTART;TZID=US Eastern Standard Time:20260709T083000
END:VEVENT
END:VCALENDAR
"""
        events = parse_ics(text, "BLS_ICS")
        self.assertEqual([at("2026-01-09T13:30:00Z"), at("2026-07-09T12:30:00Z")],
                         [item.scheduled_utc for item in events])
        self.assertTrue(all(item.source_timezone == "America/New_York" for item in events))

    def test_bls_timezone_alias_is_source_scoped(self):
        text = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:x
SUMMARY:Employment Situation
DTSTART;TZID=Eastern Standard Time:20260109T083000
END:VEVENT
END:VCALENDAR
"""
        with self.assertRaisesRegex(ValueError, "unsupported or unverified timezone"):
            parse_ics(text, "UNAPPROVED_SOURCE")

    def test_live_bls_us_eastern_alias_is_dst_safe_and_source_scoped(self):
        text = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:winter-live-shape
SUMMARY:Employment Situation
DTSTART;TZID=US-Eastern:20260109T083000
END:VEVENT
BEGIN:VEVENT
UID:summer-live-shape
SUMMARY:Consumer Price Index
DTSTART;TZID=US-Eastern:20260709T083000
END:VEVENT
END:VCALENDAR
"""
        events = parse_ics(text, "BLS_ICS")
        self.assertEqual([at("2026-01-09T13:30:00Z"), at("2026-07-09T12:30:00Z")],
                         [item.scheduled_utc for item in events])
        self.assertTrue(all(item.source_timezone == "America/New_York" for item in events))
        with self.assertRaisesRegex(ValueError, "unsupported or unverified timezone"):
            parse_ics(text, "UNAPPROVED_SOURCE")

    def test_unknown_bls_timezone_is_rejected(self):
        text = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:x
SUMMARY:Consumer Price Index
DTSTART;TZID=Unverified Eastern:20260709T083000
END:VEVENT
END:VCALENDAR
"""
        with self.assertRaisesRegex(ValueError, "unsupported or unverified timezone"):
            parse_ics(text, "BLS_ICS")

    def test_bea_json_is_utc_and_only_frozen_pce_is_admitted(self):
        raw = json.dumps({
            "Personal Income and Outlays": {"release_dates": ["2026-08-26T12:30:00+00:00"]},
            "Gross Domestic Product": {"release_dates": ["2026-08-26T12:30:00+00:00"]},
            "file_last_updated": "2026-07-13T08:00:42.402013",
        })
        events = parse_bea_json(raw)
        self.assertEqual(1, len(events))
        self.assertEqual("US_PCE", events[0].taxonomy)

    def test_fed_statement_and_press_conference_intervals_union(self):
        events = parse_official_rows([
            {"id": "stmt", "title": "FOMC statement", "date": "2026-09-16", "time": "14:00"},
            {"id": "pc", "title": "FOMC press conference", "date": "2026-09-16", "time": "14:30"},
        ], "FED_CALENDAR")
        self.assertEqual("PRE_LOCK", guard_state(at("2026-09-16T17:31:00Z"), events, source_healthy=True, shock_locked=False))
        self.assertEqual("POST_LOCK", guard_state(at("2026-09-16T18:45:00Z"), events, source_healthy=True, shock_locked=False))
        self.assertEqual("HEALTHY", guard_state(at("2026-09-16T19:00:00Z"), events, source_healthy=True, shock_locked=False))

    def test_fed_month_calendar_extracts_authoritative_times(self):
        html = """<html><title>Federal Reserve Board - Calendar: September 2026</title>
        <h4>FOMC Meetings</h4><h6>Time:</h6><h6>Release Date(s):</h6>
        <div>2:30 p.m.</div><a>FOMC Press Conference</a><div>16</div>
        <div>2:00 p.m.</div><div>FOMC Meeting</div>
        <div>Two-day meeting, September 15 - 16</div><div>Press Conference</div><div>16</div>
        </html>"""
        events = parse_fed_monthly_html(html)
        self.assertEqual(["FOMC_PRESS_CONFERENCE", "FOMC_STATEMENT"],
                         [item.taxonomy for item in events])
        self.assertEqual([at("2026-09-16T18:30:00Z"), at("2026-09-16T18:00:00Z")],
                         [item.scheduled_utc for item in events])

    def test_exact_half_open_boundaries(self):
        event = Event("BLS_ICS", "cpi", "CPI", at("2026-07-14T12:30:00Z"), "UTC", "US_CPI", "TIER_1")
        self.assertEqual("PRE_LOCK", guard_state(at("2026-07-14T12:00:00Z"), [event], source_healthy=True, shock_locked=False))
        self.assertEqual("EVENT_ACTIVE", guard_state(at("2026-07-14T12:30:00Z"), [event], source_healthy=True, shock_locked=False))
        self.assertEqual("HEALTHY", guard_state(at("2026-07-14T13:00:00Z"), [event], source_healthy=True, shock_locked=False))

    def test_source_failure_and_conflict_fail_closed(self):
        event = Event("BLS_ICS", "cpi", "CPI", at("2026-07-14T12:30:00Z"), "UTC", "US_CPI", "TIER_1")
        self.assertEqual("SOURCE_UNHEALTHY", guard_state(at("2026-07-14T10:00:00Z"), [event], source_healthy=False, shock_locked=False))
        moved = Event("BLS_ICS", "cpi", "CPI", at("2026-07-15T12:30:00Z"), "UTC", "US_CPI", "TIER_1")
        healthy, conflicts = reconcile_authoritative([event, moved])
        self.assertFalse(healthy)
        self.assertEqual(["BLS_ICS:cpi"], conflicts)

    def test_cancellation_is_honored_but_tentative_is_unhealthy(self):
        cancelled = Event("BLS_ICS", "cpi", "CPI", at("2026-07-14T12:30:00Z"), "UTC", "US_CPI", "TIER_1", "CANCELLED")
        tentative = Event("FED_CALENDAR", "speech", "Fed speech", at("2026-07-14T12:30:00Z"), "UTC", "FED_COMMUNICATION", "TIER_2", "TENTATIVE")
        self.assertEqual("HEALTHY", guard_state(at("2026-07-14T12:30:00Z"), [cancelled], source_healthy=True, shock_locked=False))
        self.assertEqual("SOURCE_UNHEALTHY", guard_state(at("2026-07-14T10:00:00Z"), [tentative], source_healthy=True, shock_locked=False))

    def test_shock_lock_is_independent_of_calendar(self):
        self.assertEqual("SHOCK_LOCK", guard_state(at("2026-07-14T10:00:00Z"), [], source_healthy=True, shock_locked=True))
        self.assertFalse(entry_allowed(at("2026-07-14T10:00:00Z"), [], source_healthy=True, shock_locked=True, normalized=True, submission_latency=timedelta(seconds=1)))

    def test_post_event_requires_normalization(self):
        event = Event("BLS_ICS", "cpi", "CPI", at("2026-07-14T12:30:00Z"), "UTC", "US_CPI", "TIER_1")
        self.assertEqual("NORMALIZATION_PENDING", guard_state(at("2026-07-14T13:01:00Z"), [event], source_healthy=True, shock_locked=False, normalized=False))

    def test_expected_submission_may_not_cross_prelock(self):
        event = Event("BLS_ICS", "cpi", "CPI", at("2026-07-14T12:30:00Z"), "UTC", "US_CPI", "TIER_1")
        now = at("2026-07-14T11:59:59Z")
        self.assertFalse(entry_allowed(now, [event], source_healthy=True, shock_locked=False, normalized=True, submission_latency=timedelta(seconds=2)))

    def test_fred_cross_check_is_date_only_and_cannot_supply_time(self):
        event = Event("BEA_JSON", "pce", "Personal Income and Outlays", at("2026-08-26T12:30:00Z"), "UTC", "US_PCE", "TIER_1")
        self.assertTrue(fred_date_cross_check(event, "2026-08-26"))
        self.assertFalse(fred_date_cross_check(event, "2026-08-27"))
        self.assertTrue(fred_date_cross_check(event, None))

    def test_jobless_claims_requires_dol_source(self):
        events = parse_official_rows([
            {"id": "dol-ui-2026-31", "title": "Unemployment Insurance Weekly Claims", "date": "2026-08-06", "time": "08:30"}
        ], "DOL_UI")
        self.assertEqual("US_JOBLESS_CLAIMS", events[0].taxonomy)
        self.assertEqual("TIER_2", events[0].tier)


if __name__ == "__main__":
    unittest.main(verbosity=2)
