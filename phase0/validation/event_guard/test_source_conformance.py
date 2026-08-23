from datetime import datetime, timedelta, timezone
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from event_guard_oracle import Event, guard_state
from source_conformance import (
    POLICIES, ZERO_HASH, assess_snapshot, conservative_revision_events,
    coverage_inventory, make_record, observed_schema_fingerprint, revision_delta,
    verify_record_chain,
)
from capture_official_sources import DEFAULT_SOURCES, _request, _target_urls
from normalize_private_capture import normalize

UTC = timezone.utc


def at(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def event(source, source_id, taxonomy, when, tier="TIER_1", status="SCHEDULED"):
    return Event(source, source_id, taxonomy, at(when), "UTC", taxonomy, tier, status)


class SourceConformanceTests(unittest.TestCase):
    def setUp(self):
        self.now = at("2026-08-23T12:00:00Z")
        self.body = (b"BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:test-1\n"
                     b"SUMMARY:Consumer Price Index\nDTSTART:20260910T123000Z\n"
                     b"END:VEVENT\nEND:VCALENDAR\n")

    def record(self, **overrides):
        values = dict(
            source="BLS_ICS",
            url=POLICIES["BLS_ICS"].urls[0],
            retrieved_utc=self.now,
            http_status=200,
            content_type="text/calendar; charset=utf-8",
            body=self.body,
        )
        values.update(overrides)
        return make_record(**values)

    def test_frozen_registry_roles_and_official_https_hosts(self):
        self.assertEqual("WATCH_ONLY", POLICIES["CENSUS_WATCH"].role)
        self.assertEqual("DATE_CROSSCHECK_ONLY", POLICIES["FRED_CROSSCHECK"].role)
        self.assertTrue(all(url.startswith("https://") for policy in POLICIES.values()
                            for url in policy.urls + policy.url_prefixes))
        self.assertTrue(all(pattern.startswith("https://") for policy in POLICIES.values()
                            for pattern in policy.url_patterns))

    def test_capture_requests_are_get_only_and_fred_is_not_enabled(self):
        request = _request(POLICIES["BLS_ICS"].urls[0], None)
        self.assertEqual("GET", request.method)
        self.assertNotIn("FRED_CROSSCHECK", DEFAULT_SOURCES)

    def test_fed_targets_are_exact_month_pages_for_frozen_horizon(self):
        self.assertEqual((
            "https://www.federalreserve.gov/newsevents/2026-august.htm",
            "https://www.federalreserve.gov/newsevents/2026-september.htm",
            "https://www.federalreserve.gov/newsevents/2026-october.htm",
            "https://www.federalreserve.gov/newsevents/2026-november.htm",
        ), _target_urls("FED_CALENDAR", self.now))

    def test_windows_timezone_dependency_is_exactly_pinned_and_hashed(self):
        requirements = (Path(__file__).parent / "requirements-win-py312.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("--only-binary=:all:", requirements)
        self.assertIn("tzdata==2026.3", requirements)
        self.assertIn(
            "--hash=sha256:dc096730c87af6cab1b171c9d532be840741ff5d459015e7f6947bd7d7e54931",
            requirements,
        )

    def test_windows_runner_gates_capture_on_install_and_tests(self):
        runner = (Path(__file__).parent / "run_private_capture.ps1").read_text(
            encoding="utf-8"
        )
        install = runner.index("--require-hashes")
        tests = runner.index("-m unittest")
        capture = runner.index("capture_official_sources.py")
        normalize = runner.index("normalize_private_capture.py")
        self.assertLess(install, tests)
        self.assertLess(tests, capture)
        self.assertLess(capture, normalize)
        self.assertIn("tests and capture were not run", runner)
        self.assertIn("private capture was not run", runner)
        self.assertIn("outside the repository", runner)

    def test_valid_200_snapshot(self):
        record = self.record()
        self.assertEqual((True, ()), assess_snapshot(record, self.body, self.now))

    def test_wrong_host_content_type_and_schema_fail(self):
        body = b"<html>changed</html>"
        record = self.record(url="https://example.invalid/bls.ics",
                             content_type="text/html", body=body)
        healthy, reasons = assess_snapshot(record, body, self.now)
        self.assertFalse(healthy)
        self.assertEqual({"CONTENT_TYPE", "SCHEMA_DRIFT", "URL_NOT_ALLOWLISTED"}, set(reasons))

    def test_schema_fingerprints_are_derived_from_body_not_declared(self):
        bea = json.dumps({
            "Personal Income and Outlays": {"release_dates": ["2026-08-26T12:30:00Z"]},
            "file_last_updated": "2026-07-13T08:00:42.402013",
        }).encode()
        fed = (b"<html>Calendar FOMC Meetings Time: Release Date(s): "
               b"FOMC Meeting</html>")
        census = b"<html>Economic Indicators Release Time AM</html>"
        self.assertEqual(POLICIES["BEA_JSON"].schema_fingerprint,
                         observed_schema_fingerprint("BEA_JSON", bea))
        self.assertEqual(POLICIES["FED_CALENDAR"].schema_fingerprint,
                         observed_schema_fingerprint("FED_CALENDAR", fed))
        self.assertEqual(POLICIES["CENSUS_WATCH"].schema_fingerprint,
                         observed_schema_fingerprint("CENSUS_WATCH", census))
        self.assertEqual("UNRECOGNIZED", observed_schema_fingerprint("BEA_JSON", b"{}"))
        unexpected_scalar = json.dumps({
            "Personal Income and Outlays": {"release_dates": ["2026-08-26T12:30:00Z"]},
            "unexpected_metadata": "must not broaden admission",
        }).encode()
        self.assertEqual("UNRECOGNIZED",
                         observed_schema_fingerprint("BEA_JSON", unexpected_scalar))

    def test_date_only_fed_landing_page_is_not_lock_authoritative(self):
        body = b"<html>Federal Open Market Committee Upcoming Dates</html>"
        record = make_record(
            source="FED_CALENDAR",
            url="https://www.federalreserve.gov/monetarypolicy.htm",
            retrieved_utc=self.now,
            http_status=200,
            content_type="text/html",
            body=body,
        )
        healthy, reasons = assess_snapshot(record, body, self.now)
        self.assertFalse(healthy)
        self.assertIn("URL_NOT_ALLOWLISTED", reasons)
        self.assertIn("SCHEMA_DRIFT", reasons)

    def test_body_tamper_and_staleness_fail(self):
        record = self.record(retrieved_utc=self.now - timedelta(hours=27))
        healthy, reasons = assess_snapshot(record, self.body + b"tamper", self.now)
        self.assertFalse(healthy)
        self.assertIn("BODY_HASH_OR_SIZE", reasons)
        self.assertIn("STALE_OR_FUTURE", reasons)

    def test_304_requires_matching_cache_and_chain(self):
        first = self.record()
        second = make_record(
            source="BLS_ICS", url=POLICIES["BLS_ICS"].urls[0],
            retrieved_utc=self.now + timedelta(hours=1), http_status=304,
            content_type="", body=b"", cached_record=first,
            previous_record_sha256=first.record_sha256,
        )
        self.assertEqual((True, ()), assess_snapshot(second, b"", self.now + timedelta(hours=1), first))
        self.assertEqual((True, ()), verify_record_chain([first, second]))

    def test_304_without_cache_is_rejected(self):
        first = self.record()
        healthy, reasons = assess_snapshot(first, self.body, self.now, None)
        self.assertTrue(healthy)
        broken = make_record(
            source="BLS_ICS", url=POLICIES["BLS_ICS"].urls[0],
            retrieved_utc=self.now, http_status=304, content_type="",
            body=b"", cached_record=first,
        )
        self.assertIn("CACHE_REQUIRED", assess_snapshot(broken, b"", self.now, None)[1])

    def test_hash_chain_detects_restart_tamper(self):
        first = self.record()
        second = self.record(previous_record_sha256=first.record_sha256,
                             retrieved_utc=self.now + timedelta(hours=1))
        self.assertEqual((True, ()), verify_record_chain([first, second]))
        self.assertEqual((False, (0, 1)), verify_record_chain([second, first]))

    def test_complete_inventory_still_fails_on_unresolved_dol(self):
        events = [
            event("BLS_ICS", "jobs", "US_EMPLOYMENT", "2026-09-04T12:30:00Z"),
            event("BLS_ICS", "cpi", "US_CPI", "2026-09-10T12:30:00Z"),
            event("BEA_JSON", "pce", "US_PCE", "2026-08-26T12:30:00Z"),
            event("FED_CALENDAR", "stmt", "FOMC_STATEMENT", "2026-09-16T18:00:00Z"),
            event("FED_CALENDAR", "pc", "FOMC_PRESS_CONFERENCE", "2026-09-16T18:30:00Z"),
            event("FED_CALENDAR", "mins", "FOMC_MINUTES", "2026-10-07T18:00:00Z"),
            event("DOL_UI", "claims", "US_JOBLESS_CLAIMS", "2026-08-27T12:30:00Z", "TIER_2"),
        ]
        healthy, inventory = coverage_inventory(
            self.now, events, {"BLS_ICS", "BEA_JSON", "FED_CALENDAR", "DOL_UI"}
        )
        self.assertFalse(healthy)
        self.assertEqual("BLOCKED_NO_AUTHORITATIVE_FORWARD_SCHEDULE",
                         inventory["DOL_UI:US_JOBLESS_CLAIMS"])
        self.assertTrue(all(value == "COVERED" for key, value in inventory.items()
                            if not key.startswith("DOL_UI:")))

    def test_watch_only_and_fred_never_satisfy_lock_coverage(self):
        fake = event("CENSUS_WATCH", "cpi", "US_CPI", "2026-09-10T12:30:00Z")
        healthy, inventory = coverage_inventory(self.now, [fake], {"CENSUS_WATCH", "FRED_CROSSCHECK"})
        self.assertFalse(healthy)
        self.assertEqual("SOURCE_UNHEALTHY", inventory["BLS_ICS:US_CPI"])

    def test_missing_forward_horizon_fails(self):
        late = event("BLS_ICS", "cpi", "US_CPI", "2026-11-10T13:30:00Z")
        healthy, inventory = coverage_inventory(self.now, [late], {"BLS_ICS"})
        self.assertFalse(healthy)
        self.assertEqual("MISSING_FORWARD_EVENT", inventory["BLS_ICS:US_CPI"])

    def test_add_move_cancel_are_typed(self):
        old = event("BLS_ICS", "cpi", "US_CPI", "2026-08-25T12:30:00Z")
        moved = event("BLS_ICS", "cpi", "US_CPI", "2026-08-26T12:30:00Z", status="CANCELLED")
        added = event("BLS_ICS", "jobs", "US_EMPLOYMENT", "2026-09-04T12:30:00Z")
        healthy, revisions = revision_delta([old], [moved, added], self.now)
        self.assertTrue(healthy)
        self.assertEqual({"CANCELLED", "MOVED", "ADDED"}, {item.kind for item in revisions})

    def test_unexplained_future_disappearance_fails(self):
        old = event("BEA_JSON", "pce", "US_PCE", "2026-08-26T12:30:00Z")
        healthy, revisions = revision_delta([old], [], self.now)
        self.assertFalse(healthy)
        self.assertEqual("UNEXPLAINED_DISAPPEARANCE", revisions[0].kind)

    def test_moved_event_retains_old_lock_until_old_window_ends(self):
        old = event("BLS_ICS", "cpi", "US_CPI", "2026-08-25T12:30:00Z")
        moved = event("BLS_ICS", "cpi", "US_CPI", "2026-08-26T12:30:00Z")
        now = at("2026-08-25T12:15:00Z")
        effective = conservative_revision_events([old], [moved], now)
        self.assertEqual(2, len(effective))
        self.assertEqual("PRE_LOCK", guard_state(now, effective, source_healthy=True, shock_locked=False))

    def test_dol_candidate_cannot_be_marked_healthy_by_http_success(self):
        body = b"official historical release page"
        record = make_record(
            source="DOL_UI", url=POLICIES["DOL_UI"].urls[0], retrieved_utc=self.now,
            http_status=200, content_type="text/html", body=body,
        )
        healthy, reasons = assess_snapshot(record, body, self.now)
        self.assertFalse(healthy)
        self.assertIn("BLOCKED_NO_AUTHORITATIVE_FORWARD_SCHEDULE", reasons)

    def test_private_normalization_proves_candidate_horizons_but_dol_stays_closed(self):
        bls = b"""BEGIN:VCALENDAR
BEGIN:VEVENT
UID:jobs
SUMMARY:Employment Situation
DTSTART:20260904T123000Z
END:VEVENT
BEGIN:VEVENT
UID:cpi
SUMMARY:Consumer Price Index
DTSTART:20260910T123000Z
END:VEVENT
END:VCALENDAR
"""
        bea = json.dumps({
            "Personal Income and Outlays": {"release_dates": ["2026-08-26T12:30:00Z"]},
            "file_last_updated": "2026-07-13T08:00:42.402013",
        }).encode()
        fed_pages = {
            "august": b"<html><h1>Calendar August 2026</h1><h2>FOMC Meetings</h2><i>Time:</i><i>Release Date(s):</i><b>2:00 p.m.</b><span>FOMC Minutes</span><em>19</em></html>",
            "september": b"<html><h1>Calendar September 2026</h1><h2>FOMC Meetings</h2><i>Time:</i><i>Release Date(s):</i><b>2:30 p.m.</b><span>FOMC Press Conference</span><em>16</em><b>2:00 p.m.</b><span>FOMC Meeting</span><em>16</em></html>",
            "october": b"<html><h1>Calendar October 2026</h1><h2>FOMC Meetings</h2><i>Time:</i><i>Release Date(s):</i><b>2:00 p.m.</b><span>FOMC Minutes</span><em>7</em><b>2:30 p.m.</b><span>FOMC Press Conference</span><em>28</em><b>2:00 p.m.</b><span>FOMC Meeting</span><em>28</em></html>",
            "november": b"<html><h1>Calendar November 2026</h1><h2>FOMC Meetings</h2><i>Time:</i><i>Release Date(s):</i><b>2:00 p.m.</b><span>FOMC Minutes</span><em>18</em></html>",
        }
        census = b"<html>Economic Indicators Release Time AM</html>"
        targets = [
            ("BLS_ICS", POLICIES["BLS_ICS"].urls[0], bls, "text/calendar"),
            ("BEA_JSON", POLICIES["BEA_JSON"].urls[0], bea, "application/json"),
        ]
        targets.extend(
            ("FED_CALENDAR", url, fed_pages[url.rsplit("-", 1)[1].split(".", 1)[0]], "text/html")
            for url in _target_urls("FED_CALENDAR", self.now)
        )
        targets.append(("CENSUS_WATCH", POLICIES["CENSUS_WATCH"].urls[0], census, "text/html"))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            records = []
            previous = ZERO_HASH
            for source, url, body, content_type in targets:
                record = make_record(
                    source=source, url=url, retrieved_utc=self.now,
                    http_status=200, content_type=content_type, body=body,
                    previous_record_sha256=previous,
                )
                body_dir = output / source
                body_dir.mkdir(parents=True, exist_ok=True)
                (body_dir / f"{record.body_sha256}.raw").write_bytes(body)
                records.append(record)
                previous = record.record_sha256
            (output / "acquisition_records.jsonl").write_text(
                "".join(json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n"
                        for record in records),
                encoding="utf-8",
            )
            result = normalize(output, self.now)
        self.assertEqual("FAIL_CLOSED", result["status"])
        self.assertTrue(all(result["source_status"][source]["status"] == "HEALTHY"
                            for source in ("BLS_ICS", "BEA_JSON", "FED_CALENDAR")), result)
        self.assertEqual("BLOCKED_NO_AUTHORITATIVE_FORWARD_SCHEDULE",
                         result["coverage"]["DOL_UI:US_JOBLESS_CLAIMS"])
        self.assertTrue(all(value == "COVERED" for key, value in result["coverage"].items()
                            if not key.startswith("DOL_UI:")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
