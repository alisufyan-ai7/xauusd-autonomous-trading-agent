# News and Event Protection Specification

**Status:** Phase 0 deterministic protection baseline frozen; provider procurement and empirical calibration remain open  
**Version:** 1.0  
**Date:** 2026-08-11  
**Authorization boundary:** Research/design only. No paid provider purchase, external-data transmission, or trading is authorized.

## 1. Purpose and authority

The initial purpose is to prevent unsafe entries around material gold events and recognize post-event normalization—not predict binary releases. A deterministic local Event Guard owns lockout state. OpenAI may receive a minimized event-state summary and discuss context, but cannot suppress, shorten, or override a lock.

## 2. Protected taxonomy

Frozen initial scheduled taxonomy:

- US employment: NFP/Employment Situation and unemployment; CPI; PCE/Personal Income and Outlays;
- FOMC decisions/statements, press conferences, minutes, and preclassified material Federal Reserve communications;
- Tier 2 monitoring: US jobless claims and pre-announced material Federal Reserve communications. GDP, retail sales, PPI, Treasury/refunding, non-US central-bank events, and other releases are excluded from the protected calendar unless prospectively promoted by a versioned research decision; the independent shock breaker still applies.

Unscheduled shocks—material Fed surprises, geopolitical escalation, market closure, or abnormal price/liquidity behavior—are handled first by a source-independent volatility/spread/data-quality circuit breaker. Headlines alone must not trigger discretionary model execution.

## 3. Canonical event record

Every event has provider/source lineage; stable event ID; taxonomy/version; impact class; currency/region; title; scheduled time in UTC; source timezone/IANA zone; initial publication, receipt, last-update and cancellation timestamps; tentative/all-day flags; revision/postponement status; source payload hash; parser version; rights record; and health/conflict status. Time without a verified timezone is invalid.

Source priority and conflict resolution must be frozen. Official BLS, BEA, Federal Reserve, and DOL schedules are authoritative for their own releases, but operational use requires monitored machine-readable acquisition or a licensed provider. Any provider must have documented rights for automation, storage, VPS/cloud processing, derived states, audit retention, and—if used—OpenAI transmission. Unknown rights block that source.

## 4. Deterministic lock state

States: `HEALTHY`, `PRE_LOCK`, `EVENT_ACTIVE`, `POST_LOCK`, `NORMALIZATION_PENDING`, `SOURCE_UNHEALTHY`, and `SHOCK_LOCK`.

Any protected event interval is half-open `[event_time - pre_window, event_time + minimum_post_window)`. Overlapping intervals union; the most restrictive rule wins. Schedule changes recompute future windows but never retroactively erase the audit record. Cancellation is honored only from a sufficiently authoritative, fresh source; unresolved conflict remains locked.

Frozen conservative specification windows (subject only to a later append-only owner/research change before trading):

| Event class | Frozen pre-lock | Frozen minimum post-lock |
|---|---:|---:|
| Tier 1: NFP, CPI, PCE, FOMC decision/press conference | 30 min | 30 min, then normalization |
| Tier 2: scheduled material Fed communications and US jobless claims | 15 min | 15 min, then normalization |

FOMC statement and press conference are separate event records whose intervals union. Tentative/all-day events, missing authoritative time, or unresolved schedule conflicts remain locked from the start of the configured horizon until corrected or operator-cleared; they cannot be treated as proof of a safe interval.

During any lock: reject new entries and pending risk-increasing intents; management of existing exposure requires a separately frozen policy. Event Guard never causes model-predicted entry direction.

## 5. Resumption and shock circuit breaker

Time elapsed is necessary but insufficient. Resumption requires all of:

- fresh, continuous market data and healthy clock/provider;
- market open under account-specific sessions;
- spread at or below a precommitted absolute and baseline-relative threshold for a sustained interval;
- realized volatility/range and tick-gap measures below precommitted robust baseline multiples for a sustained interval;
- no unresolved price discontinuity, stale feed, source conflict, or broker-state ambiguity;
- a completely fresh feature snapshot and analysis after resumption.

The independent shock breaker enters `SHOCK_LOCK` on abnormal spread, return/range, quote gap, stale/discontinuous ticks, or provider/market anomaly. Thresholds use only past data available at the observation time and must be stress-tested. Release requires sustained normalization plus minimum hold time; repeated trips escalate to operator alert/quarantine. OpenAI cannot release it.

### 5.1 Frozen evaluation order and fail-closed result

For every prospective entry, evaluate in this order: clock/data health; session; provider/calendar health; scheduled interval union; shock breaker; sustained normalization. Any `UNKNOWN`, stale, unavailable, contradictory, or boundary-equal unsafe value returns `LOCKED`. Windows use `start <= now < end`; no entry whose validation/expected submission latency could cross `start` may proceed.

The guard snapshots its calendar/version and evaluation timestamp into the intent. A schedule update, clock jump, provider degradation, or new event invalidates all not-yet-submitted intents. Resumption always requires fresh analysis; queued proposals do not survive a lock.

### 5.2 Calibration contract

Shock and normalization constants must be selected prospectively from chronological training data and then frozen before evaluation. The versioned configuration must define: tick-staleness maximum; absolute and robust-baseline spread limits; return/range and quote-gap horizons/multiples; minimum shock hold; normalization duration; repeated-trip window/count; minimum sample count; and behavior when a baseline is unavailable. Missing samples or unavailable baselines mean `LOCKED`, never a relaxed default. Calibration must report false-lock rate, missed-shock rate, lock duration, session/regime sensitivity, and tail cases on untouched chronological validation data.

## 6. Provider health and failure policy

Health covers source fetch success, age, clock offset, schema validity, duplicate/missing IDs, schedule completeness, update latency, disagreement, rate-limit state, and rights/entitlement validity. Before each decision the guard requires a calendar horizon covering the maximum pre-lock plus operational buffer. Missing/stale/conflicting calendars fail closed for new entries. Cached last-known events may extend an existing lock but cannot prove the absence of a new event.

Provider revisions, postponements, cancellations, and unscheduled updates remain append-only. Alerts must distinguish provider outage, parser failure, rights expiry, schedule conflict, shock lock, and ordinary protected window.

### 6.1 Frozen provider admission requirements

An operational source is inadmissible until a recorded review verifies: authoritative provenance/coverage for every frozen Tier 1 event; UTC/IANA timezone semantics and DST behavior; stable IDs plus revisions/cancellations/postponements; update latency history; documented uptime/status and rate limits; deterministic machine-readable access; automation/VPS/storage/derived-use/audit-retention rights; credential handling; historical replay availability or an approved archival method; and total cost. A provider marketing label such as “high impact” is not the taxonomy authority.

Production design requires either (a) one licensed operational provider continuously reconciled to official-source schedules with discrepancies locking entries, or (b) two licensed operational providers with a frozen source-priority/conflict rule. Scraping an undocumented public page is not acceptable. No paid source may be procured without owner approval. Until a provider passes admission and health tests, the Event Guard is `SOURCE_UNHEALTHY` and automated entry remains disabled.

## 7. Analyst minimization contract

If rights permit external processing, OpenAI receives only minimized fields such as `protected_event_nearby`, normalized minutes to/from event, coarse taxonomy/impact, guard state, and locally derived regime/volatility state. Do not transmit proprietary raw calendar payloads, bulk headlines, broker ticks/history, account identifiers, tickets, credentials, or exact risk/account state unless separately necessary and authorized. The deterministic guard's verdict is authoritative.

## 8. Phase 0 test requirements

Golden/event-replay tests must cover DST changes; same-minute/overlapping events; FOMC statement plus press conference; revision, postponement and cancellation; source outage/staleness; conflicting times; duplicate IDs; timezone missing/ambiguous; clock jump; event added inside pre-lock; weekend/holiday; lock spanning session close; spread spike without event; volatility shock; delayed normalization; repeated shock trips; and an OpenAI proposal attempting to override the lock.

Required acceptance: zero new-entry approvals inside any expected lock; deterministic results for identical versioned inputs; no unlock on missing/conflicting/unhealthy data; no look-ahead in baselines; complete transition audit; property/mutation tests demonstrate boundary and comparison correctness.

## 9. Remaining decisions/evidence

- Select the first operational calendar/provider or redundant design after rights, coverage, latency, reliability, and cost comparison. No paid service without owner approval.
- Calibrate and freeze shock thresholds, normalization duration, schedule horizon, and health SLA using prospective research; the evaluation semantics and missing-data behavior above are already frozen.
- Decide treatment of existing exposure/pending orders around events; no emergency action is implied here.
- Define material Fed communications and geopolitical alert provenance without admitting unreliable headline triggers.
- Set provider budget, retention, latency/health SLA, and permitted OpenAI fields.
