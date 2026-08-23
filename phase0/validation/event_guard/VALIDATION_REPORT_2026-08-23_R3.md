# Official-source Event Guard validation report R3

**Date:** 2026-08-23 UTC  
**Result:** PASS — 30/30 offline tests; operational admission fail-closed  
**Trading authorization:** none

R3 corrects a pre-operational conformance defect found before any owner capture:
the R2 capture path populated the expected schema fingerprint from registry
metadata rather than deriving the observed fingerprint from response bytes.

The collector now derives source-specific shape evidence from each body:

- BLS requires VCALENDAR, VEVENT, SUMMARY, DTSTART and UID markers;
- BEA requires a non-empty JSON title map whose values carry `release_dates`
  string arrays;
- Federal Reserve and Census require their frozen first-party calendar markers;
- DOL remains the unresolved forward-schedule token regardless of historical
  page content; and
- a 304 record inherits the previously body-derived cached fingerprint.

A new test proves accepted BEA/Fed/Census shapes and rejects an empty BEA object.
All prior HTTP, hash-chain, coverage, revision, timezone, lock and shock tests
remain green. The read-only capture has not yet been run on the benchmark VPS;
no availability, horizon, holiday or revision-latency claim follows.
