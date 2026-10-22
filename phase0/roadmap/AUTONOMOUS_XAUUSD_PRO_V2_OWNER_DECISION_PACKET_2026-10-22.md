# Autonomous XAUUSD Pro v2 — prospective owner decision packet

**Status:** OPTIONS FOR REVIEW; not owner-approved, not implementation, no DEMO/LIVE broker authorization. Date 2026-10-22 Asia/Karachi. Baseline: `main=51a7f7de395767a9ae1f9904f752bd74b3cdc010`, [2026-10-21 owner ADR](../decisions/ADR-2026-10-21-001-AUTONOMOUS-PRO-TRADING-VISION.md), [V2 draft architecture](AUTONOMOUS_XAUUSD_PRO_V2_ARCHITECTURE_AND_ACCEPTANCE_2026-10-22.md).

## Already adopted as product direction; no new selection needed

**Exness Pro only**, never Standard Cent; dedicated demo identity and no previously stored live-account credentials in this project MT5 profile; W1/D1/H4/H1/M15/M5/M1 market intelligence, autonomous direction + known-position monitoring, AI research/learning via controlled trial registry, no reliance on owner screenshots, 48-hour automated DEMO operating target, later independently admitted Pro LIVE. Provisional >USD300 future LIVE starting capital is a preference, **not** an approved deposit, margin calculation or risk budget. BROKER/TRADING/MT5 settings all remain unauthorized.

## A. First strategy and management

| Choice | Proposed sequence | What must be proved |
|---|---|---|
| A1 (recommended to investigate) | Start with original frozen **TPB** from Phase0 spec, independently replay and compare shadow candidates | Positive net OOS results and complete source/stop/fee admission; status cannot be assumed PASS |
| A2 | Evaluate TPB, BRT, FBR, RSR, MOC under unchanged preregistered families, select one objectively | Multiple-testing adjustment and sufficient per-family regime/trade coverage; not 'five for more trades' |
| A3 | Evaluate new H1 EMA + M15 breakout PR29 as a registered *new* family | Unknown CI cause resolved and independent chrono replay/holdout, not approved merely because six synthetic tests passed |

**Exit management, independent successor spec:** E0 original 100% fixed final target, no trailing/BE (already frozen for v1); E1 known-position early complete exit on objective structure failure; E2 E1 plus trailing/tightening and net break-even after proven favorable structure. E1/E2 require a new version, explicit predicates and adversarial known-order/stop-modification/retcode tests. No stop widening or model whim. **E0 retained unless a successor is accepted.**

## B. Account-aware risk alternatives — comparative modelling ONLY

Current frozen A: planned loss cap `floor_cent(0.25% * min(B,E,10000))`, 0.01 max lot, USD50 concurrent, USD75 daily, USD150 weekly, USD500 drawdown, Q streak>=3 pause, projected current/stressed margin>=1000% and free margin>=90%. Owner asked for flexibility but has not approved new percentages.

| Eligible Pro account equity | A: 0.25% | Research hypothetical B: 1% | Research hypothetical C: 2% |
|---:|---:|---:|---:|
| USD300 | USD0.75 | USD3.00 | USD6.00 |
| USD500 | USD1.25 | USD5.00 | USD10.00 |
| USD1,000 | USD2.50 | USD10.00 | USD20.00 |
| USD10,000 | USD25.00 | USD100.00 | USD200.00 |

These are **per-trade percentages for illustration only**, not permissible trade sizes or suggested daily loss caps. At 0.01 Pro XAUUSD lot (currently observed 1oz), `USD1/oz move = about USD1 before fees`; insufficient fixed broker min lot vs structural stop makes a trade inadmissible even with 1–2% risk. S2 used provisional adverse engineering reserves USD9.50 per 0.01 lot; these have NOT been accepted as LIVE cost estimates, but they illustrate why low-balance plans may be infeasible even under C. An even more aggressive policy or changing lot/account type is not implied. **Never use Standard Cent.**

Recommendation: retain A through initial DEMO implementation, develop evidence-backed B/C **offline** alternatives side by side, add modelled worst-case cumulative account drawdowns and broker-stops stress. If the owner later wants a different fraction, require a new dated owner ADR, exact dollar per-trade/day/week/drawdown values, stop/fee/0.01-lot feasibility, independently executed unit/property tests, immutable risk-release hashes and a non-automatic activation review.

## C. AI role and learning governance

Researcher proposal: source-permitted web/document inquiry, macro/event summaries and trade attributions; no raw broker credentials, no unvetted unrestricted external model inputs. Analyst proposal: version-pinned strict minimized structured outputs with `store=false`, no tools, no risk/position/lot authority, always fail-closed. Continuous learning proposal: offline challenger/version registry, not self-modified production prompt/weights. Any cloud/OpenAI production use beyond the previously approved benchmark requires explicit owner approval with max spend, permitted data and deployment-bound config.

## D. Broker and 48-hour DEMO activation

D0: code verified but execution disabled. D1: owner attended single S2 canary (only if the separately sealed implementation exact SHA and actual trade parameters are approved). D2: 48-hour autonomous Pro DEMO trial after a NEW exact sealed execution release passes risk, lifecycle, news/session, reconciliation, monitoring, native Windows adversarial tests and an explicit owner-bound activation window. Full DEMO result includes uptime, eligible hours, exact trade count, P/L after costs, incident history, broker deal reconciliation and stop/kill proof. **48h is not OOS profitability proof.**

Pro LIVE owner request remains a later independent review: LIVE account fingerprint and cost/margin stop risk must be independently qualified; no demo account can enable or switch to LIVE; original Gate0/replay/long-shadow requirements remain pending unless separately and prospectively revised. Never automatic LIVE after D2.

## E. Owner decisions to request after specification review

1. Approve or revise V2 **specification scope** (timeframes, signal-selector/AI roles, known-position management, data/provenance, watchdog) as a DESIGN decision—not code/deployment approval.
2. Select strategy/exit research priority A1/A2/A3 and E0/E1/E2 only after seeing the objective proposed tests. Suggested first candidate for study: A1 plus independently evaluated E1/E2 in shadow.
3. Decide whether an account-aware Risk Policy A successor should be *researched* and on what maximum tolerated USD loss/drawdown envelope. No automatic B/C activation.
4. For later broker runs: exact SHA, scope, account type/fingerprint, expiry/session and permission to use OpenAI, VPS staging/CI, SIMULATED/DEMO order and trading toggle separately.
5. When D2 evidence exists, review LIVE admission as a separate owner decision. No money movement now.

**Formal current choice state:** `V2_SPEC_DRAFT_UNREVIEWED`; `CHAMPION_NOT_SELECTED`; `DYNAMIC_EXIT_NOT_ADMITTED`; `POLICY_A_UNCHANGED`; `OPENAI_BROKER_ACTION_UNAUTHORIZED`; `DEMO_ACTIVATION_DISABLED`; `LIVE_ACTIVATION_DISABLED`.

## F. What comes after owner's v2 spec review

First implementation candidate should be **execution-disabled**: broker-neutral W1/D1/H4/H1/M15/M5/M1 context adapter, versioned single-strategy scorer and event/session/NO_TRADE audit, with offline and native Windows tests. In parallel fix PR29 exact-head GitHub Actions errors; do not merge its proof-of-concept just to show progress. The second tranche builds standalone, independently tested known-position/lifecycle and Policy A risk bridges; only a later owner-granted byte-exact demo release may place orders.

**This document records proposed options, not their adoption.** Keep this owner packet linked to the append-only ADR/Decision Log and next-state JSON.
