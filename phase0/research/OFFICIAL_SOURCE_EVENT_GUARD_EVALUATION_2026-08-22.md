# Free authoritative-source Event Guard evaluation

**Decision date:** 2026-08-22  
**Status:** conditionally recommended for Gate 0 conformance; not operationally admitted  
**Cost:** no paid calendar subscription  
**Trading authorization:** none; external Python trading remains disabled

## Recommendation

Use the official-source design as the Gate 0 primary candidate. Do not buy or
activate Trading Economics, Benzinga, or another paid calendar now. The design
meets the actual safety objective—pre-scheduled lockout around material XAUUSD
events—without consensus forecasts, surprise calculations, or headlines.

Admission remains conditional on live acquisition, revision, horizon, timezone,
holiday, outage, and schema-drift evidence. A paid aggregator becomes eligible
for a later approval decision only when a registered test demonstrates a
material capability gap that the official sources cannot safely close.

## Source conformance matrix

| Source | Intended coverage | Interface and time semantics | Rights/retention posture | Admission result |
|---|---|---|---|---|
| BLS | Employment Situation/NFP, CPI | First-party `https://www.bls.gov/schedule/news_release/bls.ics`; BLS says the tentative calendar updates weekly and is supplemented as needed | BLS states its published material is public domain; retain source attribution and local payload hashes | **Candidate pass**, subject to observed revision/freshness SLA |
| BEA | PCE / Personal Income and Outlays | First-party `https://apps.bea.gov/API/signup/release_dates.json` with the BEA ICS as corroboration; published timestamps are explicit UTC | BEA states site information is public domain unless noted; retain attribution and local payload hashes | **Candidate pass**, subject to duplicate/revision monitoring |
| Federal Reserve Board | FOMC statement, press conference, minutes, preclassified material communications | FOMC annual calendar plus monthly event pages; monthly pages supply exact event times; calendar/RSS changes require monitored snapshots | First-party public schedule; do not ingest third-party linked content; retain only schedule metadata and hashes | **Conditional**: HTML parser and late-added communication coverage require live tests |
| U.S. Census Bureau | Optional watch-only retail/housing/durables releases; can support later taxonomy promotion | Official economic-indicator list view; release times require explicit Eastern-time verification per release family and DST conversion | Public schedule/citation posture is usable; API terms do not automatically apply to the HTML calendar | **Conditional**: page is not a dedicated schedule API and frozen taxonomy currently excludes its releases |
| DOL ETA | Weekly initial/jobless claims (frozen Tier 2) | Official weekly claims publication is normally 08:30 Eastern; exception/holiday weeks must be captured from a first-party schedule or conservative fail-closed recurrence | First-party public release; local metadata/hash archive only | **Required gap closure** if jobless claims stays in taxonomy |
| FRED | Optional discrepancy check | API provides release dates, not a reliable authoritative release clock; it requires a FRED API key | Do not transmit broker/account data; store date-level comparison results only | **Cross-check only**; never unlocks or overrides agency time |

This is a technical/licensing conformance review, not legal advice. The local
archive should store the minimum schedule metadata, retrieval timestamp, source
URL, parser version, HTTP validators, and payload SHA-256. It should not
redistribute agency branding, bulk unrelated content, or third-party material.

## Local acquisition and normalization design

1. Retrieve BLS/BEA machine-readable schedules and monitored Fed/Census/DOL
   schedule pages on a polite cadence, using conditional HTTP requests where
   supported. Never infer safety from a failed fetch.
2. Store every raw snapshot locally in an append-only, hash-chained audit store;
   parse through a version-pinned adapter and quarantine schema drift.
3. Normalize an explicitly verified source zone with IANA
   `America/New_York`, or an explicit source UTC offset, into UTC. A time lacking
   a verified zone is invalid.
4. Classify only the frozen taxonomy. GDP, retail, PPI and other Census/BEA/BLS
   events remain watch-only unless a later decision promotes them.
5. Generate deterministic local IDs from agency, agency UID when present,
   taxonomy, period and scheduled time. Preserve revisions, postponements and
   cancellations; never overwrite history.
6. Reconcile the agency's current schedule with the last accepted snapshot.
   Conflicts, missing horizon, stale data, tentative/all-day records or a FRED
   date disagreement set `SOURCE_UNHEALTHY`.
7. Union all scheduled pre/post intervals. Independently evaluate the frozen
   spread/return/range/quote-gap/staleness circuit breaker. Either lock blocks a
   new entry; only sustained post-event normalization can resume evaluation.

## Registered conformance evidence

The standard-library-only package under `phase0/validation/event_guard` passes
30/30 tests: the original 14 Event Guard tests plus 16 acquisition/revision
conformance tests covering:

- EST/EDT conversion and missing-zone rejection;
- BLS-style iCalendar unfolding/filtering and BEA UTC JSON;
- FOMC statement/press-conference interval union and exact half-open boundaries;
- duplicate-ID/time conflicts, cancellation and tentative-event behavior;
- optional FRED date mismatch behavior;
- submission latency crossing into pre-lock;
- independent shock lock and post-event normalization;
- the requirement for a DOL source for weekly claims.
- frozen official HTTPS endpoints, roles and GET-only construction;
- HTTP/content/schema/freshness/body-hash rejection and 304 cache identity;
- append-only record-chain restart verification and tamper detection;
- bounded forward-coverage inventory and watch-only/cross-check isolation;
- typed additions, movements and cancellations, old-window retention after a
  move, and unexplained future-event disappearance rejection.
- source-specific schema fingerprints derived from captured body content rather
  than copied from expected registry metadata.

The accompanying read-only capture utility writes raw responses only to an
operator-selected private directory. Raw snapshots are evidence and are never
part of the sanitized repository. DOL remains hard-coded as blocked even if its
historical releases page returns HTTP 200; a page showing past weekly releases
does not prove future holiday exceptions.

## Material gaps and promotion rule

The free design is not yet operationally admitted because it lacks a measured
live acquisition record. Gate 0 must keep the Event Guard fail-closed until all
of these pass:

- at least one full published-calendar horizon plus observed additions,
  revisions, postponements and a holiday/exception case;
- deterministic parser fixtures made from actual BLS, BEA, Fed, Census and DOL
  snapshots, with schema-drift and HTTP-failure injection;
- explicit coverage inventory proving every frozen Tier 1 event and retained
  Tier 2 event has a fresh authoritative time;
- clock/DST boundary checks on the benchmark VPS;
- empirical shock/normalization calibration on untouched chronological data;
- hash-chain/restart recovery and alerting for missing/stale/conflicting sources.

A paid aggregator is a material upgrade only if it demonstrably reduces an
unacceptable gap such as late schedule changes, incomplete scheduled Fed
communication coverage, or absence of revision history, while also passing
automation, storage, derived-data, retention, subprocessor, pricing and
non-auto-renewal review. Consensus forecasts alone are not a material Gate 0
capability for this Event Guard.
