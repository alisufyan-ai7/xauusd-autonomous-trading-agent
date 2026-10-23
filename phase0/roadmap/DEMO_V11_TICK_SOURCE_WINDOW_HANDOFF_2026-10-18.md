# Next priorities: v1.1-T1 tick protocol, independent source contract, UTC window feasibility

**Date:** 2026-10-18. **State:** offline prospective engineering only, no VPS/broker action, no new evidence capture, no numeric calibration, no DEMO-ADMIT PASS.  
**Stack:** `main ccaa8338aecee8bd3afbc358644410dff6c512e5` → PR #8 selected v1.1 → PR #9 pure full Policy A + demo adapter hard submission veto → PR #10 dormant Windows collector → THIS new branch/PR #11.

## Protocol preregistered before real data

`DEMO_V11_T1_TICK_TIMESTAMP_SEQUENCE_PROTOCOL_2026-10-18.json` freezes the exact tick-handling interpretation, addressing MT5's documented legitimate duplicate-millisecond source ticks. Do not dedupe or sort the source. Preserve original UTC `time_msc`, `time` seconds crosscheck, quote sides, flags and ordered 0-based source ordinal. If a 10-minute MT5 range includes a boundary tick also attributable to the adjacent range, **reject ambiguous source overlap** rather than trim adverse observations; this may make a capture fail and calls for a prospective method revision, not a retrospective relabel.

For each horizon h in **1s, 5s, 30s**, use all *subsequent* true tick pairs with time within **[t+h−250ms, t+h+250ms]**, inclusive. Maximize adverse ASK increase and BID decline over every eligible pair (including those crossing ten-minute bins). Ten-minute coverage requires at least one pair wholly inside each of the 24 ten-minute blocks *per horizon*. Same-millisecond source ticks remain distinct when source ordering is proven; adjacent quote jumps include them. Exact 4h, 240 minutes, 2880 nominal 5s poll slots/99% minimum, no unclassified >5s tick gap or boundary gap, and independent UTC clock checks remain mandatory. No observed price proxy bounds future order execution or stop-loss slippage.

**Files:** amended `demo_adapter/scripts/v11_quote_coverage.py` and `v11_capture_orchestrator.py`, extra synthetic source-sequence/irregular-ms tolerance tests; original v1.0 registration unchanged. Real MT5 tick sequencing and boundary semantics have not been empirically validated. Source hash SHA-256 and private raw manifest remain NULL.

## Independent source and accounting prerequisites

`DEMO_V11_INDEPENDENT_SOURCE_EVIDENCE_REGISTRY_2026-10-18.json` enumerates *eleven independently reviewable evidence groups*: account/terminal, symbol specification, tick stream, exposure, inception/day/week cashflow ledger, account-specific commission/swap, USD tick loss/FX conversion, adverse quote/slippage/gap stress assumptions, Exness XAUUSD-specific sessions/holiday/DST, BLS/BEA/Census/Federal Reserve + Event Guard, exact reviewed collector/manifest/owner authorization.

For each one, require verifiable original source identity and freshness, immutable PRIVATE raw bytes+SHA256, independent reread or cross-check and independent **exact Decimal** recomputation. A hash supplied by the same untrusted author proves only byte identity, not authentic broker/agency origin. Do not silently set zero commissions/swap/gap/currency conversion, manufacture inception/day/week boundary snapshots or trust a claimed `INDEPENDENTLY_ADMITTED_FOR_REPLAY` label. Broker historical deal/order retrieval would require separate explicit permission; current code makes NO additional MT5 history calls. Existing manual Exness source documentation is not evidence for actual account fees without account match.

Existing `mt5_demo.py` still **quarantines and refuses demo submission before order_check/order_send** until an actually independently authenticated, broker-reconciled full Policy A runtime binding exists.

## Four-hour UTC window: remain unregistered, not invented

`DEMO_V11_UTC_WINDOW_FEASIBILITY_REVIEW_2026-10-18.md` and `DEMO_V11_PROSPECTIVE_WINDOW_CANDIDATE_REJECTION_2026-10-18.json` document that the official Exness trading-center summer example has only a 3h overlap (13:30–16:30 UTC under its listed hours), while a considered **2026-10-20 13:00–17:00 UTC candidate** includes the October 20, 10:00 ET BLS state-employment release at 14:00 UTC. They are NOT date-specific source-hashed XAUUSD schedules, and the official Event Guard impact/blocking classification is still pending. This candidate is REJECTED FOR QUALIFICATION, never used for capture or backfilled evidence. No supported 4h overlapping window has been proven.

All exact run registration fields for a *qualified* future window remain NULL. A future owner decision may be needed if proof shows the 4h full-overlap condition cannot be met; do not change selected v1.1 session scope by implication. `v11_window_readiness.py` + synthetic tests enforce source pins, exact 4h, time prospectivity, all-session inclusion and event veto but **do not themselves authenticate provider documents**.

## Required next gates and owner boundaries

1. Independent review of exact-head CI and implementation source after prospective method registration. Windows/Linux lint, type, synthetic tests, package boundary, Windows PS5.1 parser should pass before advising a merge.
2. Source-hashed **XAUUSD-specific trading-hours, DST and Event Guard** independent evidence, exact eligible UTC window, broker historical boundary and cost provenance; register date and immutable hashes prospectively, *before* actual capture. If 4h strict entire-overlap impossible, stop and request new prospective owner selection instead of redefining it.
3. Separate explicit owner authorization before any VPS read-only diagnostic/capture, broker information call, task or worktree mutation. No real sample or empirical calibration exists here; project remains `NOT_ADMITTED`.
4. Later independent full runtime Policy A cash risk source binding tests and human-only emergency/position holding procedure. No removal of the demo submission veto without distinct reviewed approval.

**No merges PR #8/#9/#10/#11; no VPS/MT5 access; external Python trading stays disabled; no orders, no demo or live trade, no reclassification of Dukascopy R3 and other historical FAIL_CLOSED evidence.**

Public source references for offline investigation only, not immutable provider snapshot hashes:
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py
- https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours
- https://www.bls.gov/schedule/2026/10_sched_list.htm
