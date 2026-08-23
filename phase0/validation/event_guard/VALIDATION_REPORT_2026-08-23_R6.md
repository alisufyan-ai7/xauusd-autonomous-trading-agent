# Official-source Event Guard validation report R6

**Date:** 2026-08-23 UTC  
**Result:** PASS — 36/36 offline tests; exact-time Fed VPS capture pending  
**Trading authorization:** none

The second private VPS acquisition appended four records to the original three.
Independent recomputation verifies all seven record digests and every chain
link. The BLS, Fed and Census 304 records also retain the exact cached body hash,
byte count, schema fingerprint and source-specific cache-record link. BEA is now
captured at record hash
`8830a631ed903df71be3c1614e135495aae9bef0d48251cc0c64376b71a8d1ae`.
The seven-record chain ends at
`6849399718b3a66b390f96a377a9c1494615156815758555d328b35383692540`.

Review then found a separate pre-admission defect: the captured general Federal
Reserve monetary-policy page lists upcoming FOMC dates but does not publish the
authoritative release times needed to construct UTC lock intervals. Its R11
transport record is valid evidence of the fetched bytes, but it is not admitted
as lock-ready schedule evidence.

R6 replaces that endpoint with four exact allow-listed official month-calendar
URLs derived from the capture time. Those pages publish both `Time` and
`Release Date(s)`. A standard-library parser admits only FOMC statements,
press conferences and minutes, converts Eastern time through the pinned IANA
database, and rejects a missing time/date or an empty protected month section.
The old landing URL and shape are explicitly rejected.

An offline normalizer now reloads the private hash chain, verifies raw body
hashes and 304 cache identities, parses BLS/BEA/Fed schedules, reconciles IDs and
proves each frozen forward horizon. Its sanitized private report stays
`FAIL_CLOSED` while DOL jobless claims remains unresolved. The full synthetic
capture-to-horizon path is covered by a regression test.

No raw body, private manifest, identity, account data, screenshot or ZIP is
published. One controlled VPS rerun is required to prove the exact live Fed
month-page shapes. External Python trading remains disabled.
