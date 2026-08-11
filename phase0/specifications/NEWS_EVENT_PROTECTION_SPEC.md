# News and Event Protection Specification

**Status:** Phase 0 candidate specification  
**Version:** 0.1  
**Date:** 2026-08-11  
**Authorization boundary:** Research/design only. No paid provider purchase, external-data transmission, or trading is authorized.

## 1. Purpose and authority

The initial purpose is to prevent unsafe entries around material gold events and recognize post-event normalization—not predict binary releases. A deterministic local Event Guard owns lockout state. OpenAI may receive a minimized event-state summary and discuss context, but cannot suppress, shorten, or override a lock.

## 2. Protected taxonomy

Initial scheduled high-impact candidates:

- US employment: NFP/Employment Situation and unemployment; CPI; PCE/Personal Income and Outlays;
- FOMC decisions/statements, press conferences, minutes, and preclassified material Federal Reserve communications;
- other events only after objective inclusion criteria, including GDP, retail sales, PPI, jobless claims, Treasury/refunding or central-bank events where evidence shows material XAUUSD impact.

Unscheduled shocks—material Fed surprises, geopolitical escalation, market closure, or abnormal price/liquidity behavior—are handled first by a source-independent volatility/spread/data-quality circuit breaker. Headlines alone must not trigger discretionary model execution.

## 3. Canonical event record

Every event has provider/source lineage; stable event ID; taxonomy/version; impact class; currency/region; title; scheduled time in UTC; source timezone/IANA zone; initial publication, receipt, last-update and cancellation timestamps; tentative/all-day flags; revision/postponement status; source payload hash; parser version; rights record; and health/conflict status. Time without a verified timezone is invalid.

Source priority and conflict resolution must be frozen. Official BLS, BEA, Federal Reserve, and DOL schedules are authoritative for their own releases, but operational use requires monitored machine-readable acquisition or a licensed provider. Any provider must have documented rights for automation, storage, VPS/cloud processing, derived states, audit retention, and—if used—OpenAI transmission. Unknown rights block that source.

## 4. Deterministic lock state

States: `HEALTHY`, `PRE_LOCK`, `EVENT_ACTIVE`, `POST_LOCK`, `NORMALIZATION_PENDING`, `SOURCE_UNHEALTHY`, and `SHOCK_LOCK`.

Any protected event interval is half-open `[event_time - pre_window, event_time + minimum_post_window)`. Overlapping intervals union; the most restrictive rule wins. Schedule changes recompute future windows but never retroactively erase the audit record. Cancellation is honored only from a sufficiently authoritative, fresh source; unresolved conflict remains locked.

Provisional windows requiring empirical freeze before implementation:

| Event class | Pre-lock candidate | Minimum post-lock candidate |
|---|---:|---:|
| Tier 1: NFP, CPI, PCE, FOMC decision/press conference | 30 min | 30 min, then normalization |
| Tier 2: selected Fed communications, claims/other proven events | 15 min | 15 min, then normalization |

These are research starting points, not approved production parameters. FOMC statement and press conference may be separate event times whose union extends protection.

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

## 6. Provider health and failure policy

Health covers source fetch success, age, clock offset, schema validity, duplicate/missing IDs, schedule completeness, update latency, disagreement, rate-limit state, and rights/entitlement validity. Before each decision the guard requires a calendar horizon covering the maximum pre-lock plus operational buffer. Missing/stale/conflicting calendars fail closed for new entries. Cached last-known events may extend an existing lock but cannot prove the absence of a new event.

Provider revisions, postponements, cancellations, and unscheduled updates remain append-only. Alerts must distinguish provider outage, parser failure, rights expiry, schedule conflict, shock lock, and ordinary protected window.

## 7. Analyst minimization contract

If rights permit external processing, OpenAI receives only minimized fields such as `protected_event_nearby`, normalized minutes to/from event, coarse taxonomy/impact, guard state, and locally derived regime/volatility state. Do not transmit proprietary raw calendar payloads, bulk headlines, broker ticks/history, account identifiers, tickets, credentials, or exact risk/account state unless separately necessary and authorized. The deterministic guard's verdict is authoritative.

## 8. Phase 0 test requirements

Golden/event-replay tests must cover DST changes; same-minute/overlapping events; FOMC statement plus press conference; revision, postponement and cancellation; source outage/staleness; conflicting times; duplicate IDs; timezone missing/ambiguous; clock jump; event added inside pre-lock; weekend/holiday; lock spanning session close; spread spike without event; volatility shock; delayed normalization; repeated shock trips; and an OpenAI proposal attempting to override the lock.

Required acceptance: zero new-entry approvals inside any expected lock; deterministic results for identical versioned inputs; no unlock on missing/conflicting/unhealthy data; no look-ahead in baselines; complete transition audit; property/mutation tests demonstrate boundary and comparison correctness.

## 9. Unresolved items and owner decisions

- Select the first operational calendar/provider or redundant design after rights, coverage, latency, reliability, and cost comparison. No paid service without owner approval.
- Freeze exact protected taxonomy, impact mapping, pre/post windows, shock thresholds, normalization durations, and schedule horizon using prospective research.
- Decide treatment of existing exposure/pending orders around events; no emergency action is implied here.
- Define material Fed communications and geopolitical alert provenance without admitting unreliable headline triggers.
- Set provider budget, retention, latency/health SLA, and permitted OpenAI fields.

