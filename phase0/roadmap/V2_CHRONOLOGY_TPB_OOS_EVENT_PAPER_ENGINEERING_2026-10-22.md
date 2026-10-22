# V2 engineering tranche: chronology, TPB, OOS, official events and durable paper ledger

**Date:** 2026-10-22 (Asia/Karachi). **Status:** PROSPECTIVE EXECUTION-DISABLED ENGINEERING DRAFT. No broker orders, MT5 Python trading toggle, VPS deployment, demo trade, LIVE funding, or continuous background trading authorized.

## Baseline and immutable evidence

- Parent PR33 HEAD at child creation: `c452d90abf915761f0443be807e40cbe9784051d`. Source main `95875ccf1bddc43491ced1dd4358057b62b7800e`; PR32 and PR33 remain DRAFT/UNMERGED; this is a STACKED child, not a production merge.
- `phase0/evidence/V2_XAUUSD_DEMO_SEVEN_FRAME_READONLY_PASS_2026-10-22.json`: exact prior owner-attended snapshot, all seven requested bars, matching Exness XAUUSD DEMO fingerprint, Python-trading-disabled. Older attempts 1 & 2 preserved FAIL_CLOSED.
- **Important:** W1 source open timestamps are Sunday UTC; last trading tick before weekend need not be Sunday. Existing `ContextBar.close_time` equals `open_time+7d` for W1, a **nominal logical bar boundary** not a proved broker tradable cutoff. Never infer weekly market open/closed from this arithmetic alone.

## 1. Chronology and session coverage

New pure `src/xauusd_agent/features/v2_chronology_audit.py` checks completed bars, monotonicity, duplicated/overlapping opens, missing logical weeks, Sunday W1 anchor, declared session coverage and minute/hour/day missing bars **inside verified open-session intervals**; closed-session missing intervals can be classified separately. `SessionCalendarEvidence` requires source SHA, revision, coverage and external `source_verified`, `weekly_sunday_utc_anchor_verified` flags. No broker session metadata has been independently approved. Current real read-only sample is **acquisition PASS / full chronology UNADMITTED**. Tests synthetic only.

**Remaining:** authoritative MT5 Exness Pro UTC+0 session/holiday boundary capture, W1 week anchor and DST/rollover transitions, catalog actual open trading intervals, cross-frame live/replay parity fixtures. Treat `source_verified=False` until source date/time, page hash, broker rules and observation are independently assessed.

## 2. Objective TPB setup state

New `src/xauusd_agent/features/v2_tpb_zone_tracker.py` implements deterministic nonexecuting Zone A or Zone B first touch, confluence gate, wick/body rejection, top/bottom 35% close, confirmation within 2 M15 closes, 8-bar post-first-touch window, 4-bar paper entry expiration, 0.15 M15 ATR far-edge invalidation, explicit regime/origin/session/official-event/cost-source rejection and no Zone B while A exposure is present. Both zones always `execution_permitted=False`.

**NOT YET full frozen TPB:** independent qualifying H1 impulse/structural target and swing/consolidation confluences, new-impulse supersession, first-touch event persisted across restart, strict source-proven M15/H1/H4 alignment and two-tick/stop executable broker mechanics need integrated golden fixtures. Existing `v2_tpb_research.py` is a Zone A hypothesis and this new state machine is a separate building block; they have not been wired into a fully matching P0-SETUPS-001 candidate. No strategy admitted/profitable claim.

## 3. Cost-aware chronological OOS accounting

New `src/xauusd_agent/features/v2_replay_audit.py` requires immutable dataset and strategy hashes, source rights, frozen chrono split, empirical cost verification, and nonoverlapping time-ordered trade ledger. Computes deterministic gross-less-costs R, 2x transaction-cost stress, max R drawdown and normalized ledger digest. **Output cannot return 'PROFITABLE' or authorize trading**, even when synthetic trades yield positive expectancy.

**Observed real historical performance: NO DATA / NO RESULTS.** One live Exness read-only count snapshot is NOT an admitted historical bid/ask, tick-cost, commission/swap/gap sample, registered TPB trade ledger, development/validation/untouched OOS split, or random-seed-protected trial. Frozen P0-REPLAY-001 still requires 10,000+ block bootstrap resamples, dependence justification, DSR/PBO or preregistered alternative, walk-forward fold coverage, fragility tests, selection bias correction, tail spread/slippage scenarios, deterministic replay and full Policy A compliance. Therefore truthful current verdict is `INSUFFICIENT_EVIDENCE`, regardless of toy test outcomes.

## 4. Official-source Event Guard + bounded AI

New `src/xauusd_agent/guards/v2_official_source_gate.py` requires versioned source-hashed, rights-cleared, clock/DST-verified, coverage-complete official BLS/BEA/FED/CENSUS/DOL agency inputs before passing any normalized event calendar to the existing frozen `evaluate_event_guard`. It rejects missing agencies, stale/late capture, unknown revisions, invalid official host, tentative/cancelled events via existing guard semantics, shocks and unknown normalization. `America/New_York` local times are converted with explicit invalid/ambiguous DST refusal. **No live network fetch/official parser is connected here**; source_verified cannot be inferred from a web search. Default `AnalystClient` remains transport-disabled and cannot override Event Guard, size or execute trades.

Authoritative sites researched for source inventory (NOT validated as machine-ingestion or timestamp-grade operational feed): https://www.bls.gov/schedule/ ; https://www.bea.gov/news/schedule ; https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm ; https://www.census.gov/economic-indicators/calendar-listview.html ; https://www.dol.gov/agencies/eta/ui-data . Any live feed requires source-terms and parser admission, stable IDs, event revisions, full required taxonomies, freshness monitoring, delivery audit and timezone validation, without guessing release times.

## 5. Durable DEMO transaction lifecycle — PAPER ONLY

New `src/xauusd_agent/ops/v2_durable_paper_ledger.py` creates a SQLite `WAL`+`synchronous=FULL` append-only **synthetic** intent/state journal, hash chain and optimistic revision fencing. It refuses duplicate intent IDs, mismatched sanitized account hash, journal tamper, unknown positions, stale broker snapshot, ambiguous submission and automatic quarantine rearm. It never holds broker credentials, positions/order APIs or places/closes/modifies orders. Local DB bytes stay OFF GitHub; repo contains only source/tests.

**STILL MISSING actual DEMO execution:** byte-exact Exness broker account/symbol preflight, `order_calc_profit/order_calc_margin/order_check` binding at time of entry, protective stop and 0.01-lot Policy A checks, order retcode mapping, durable intent + broker submission side effect consistency, broker history-based unknown ack reconciliation, known-ticket partial fill/close, real daily/weekly loss ledger and E1 human-only alerts/watchdog, restart/disconnect drills, P1 human gated resumption, explicit owner approved sealed release. Do not interpret synthetic paper state as authorization to toggle Python trading or place orders.

## Next work and safety

Run exact-head native Windows/Ubuntu Python3.12 lint/MyPy/unit/record checks before accepting even these source/test changes. Correct source or fixture errors in this child branch only, keeping original failed attempts. Do not merge unreviewed parent PR32/33 or this child; do not deploy to VPS. Remaining empirical tasks require an accepted source right and actual historical time-series data; consider a separately authorized **READ-ONLY** on-VPS source chronology provenance capture if evidence gaps persist.

**Frozen Policy A/owner policy unchanged:** Exness Pro only (never Standard Cent), 0.01 lot cap, 0.25% planned-risk ceiling, M1 1000% current/stressed and >=90% free/equity, daily/weekly/concurrent limits, no stop-widening/unknown-exposure close, no automatic REAL/LIVE gate. No uninterrupted 48h DEMO trading trial has started.
