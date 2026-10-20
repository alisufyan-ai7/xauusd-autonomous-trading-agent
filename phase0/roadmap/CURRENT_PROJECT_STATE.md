# CURRENT PROJECT STATE — XAU/USD Autonomous Trading Agent

**As-of date:** 2026-10-18  
**Authoritative code base:** private GitHub repository `alisufyan-ai7/xauusd-autonomous-trading-agent`  
**Current merged `main`:** `33b7ebb664d4c343dd6d8dc77544cfdb17bab6bf`

## 1. Source-of-truth rule

GitHub is the durable source of truth for this project. Chat history, account memory, screenshots, and local recollection are secondary aids only.

Before making a substantive project decision or changing project state, the operator/assistant must first reconcile the exact GitHub state. Any new decision, test result, failure, acceptance, rollback, authorization boundary, or operational state that would matter in a future chat must be written back to GitHub before relying on it as durable project knowledge.

Immutable failures must remain preserved and must never be reinterpreted away. If GitHub and a chat summary conflict, stop and reconcile the discrepancy before proceeding.

Secrets, credentials, account numbers, passwords, tokens, and personally identifying broker login values must not be committed. Account identity is represented only by admitted hashes/fingerprints.

## 2. Current program objective

The accelerated objective is to reach a production-grade XAU/USD autonomous trading agent on the VPS while keeping the distinction between:

1. **software / operational readiness**, and
2. **permission to risk money**.

Real-money activation remains separately gated. The current active focus is the bounded **DEMO-ADMIT** path for the Exness MT5 demo environment.

## 3. Frozen architecture and safety authority

Architecture remains:

Exness MT5 → Market Data Engine → Technical/Feature Engine → Setup Detector → OpenAI Analyst → deterministic Risk Governor → MT5 Execution Engine → Position Manager → Audit/Analytics.

OpenAI is advisory and cannot authorize risk. The deterministic local Risk Governor is authoritative and must fail closed.

Frozen safety controls include:
- XAUUSD only for the current program;
- V1 absolute volume cap: **0.01 lot**;
- deterministic Policy A / V1 / M1 risk checks;
- projected margin level at least **1000%** current and stressed;
- projected free margin at least **90% of equity** current and stressed;
- stressed incremental margin multiplier **2.0x**;
- protective stop required;
- no averaging down, martingale, grid recovery, or stop widening;
- unknown exposure → quarantine / block new risk; never automatic unknown-position closure;
- E1 emergency action is human-only;
- P1 resumption is human-gated;
- demo/live broker action requires separate explicit owner authorization.

## 4. Gate 0 historical state — preserve failures

Gate 0 is not retroactively rewritten by the accelerated path.

Important preserved historical state:
- G0-05 R4: immutable FAIL_CLOSED.
- G0-07: two immutable failed attempts (R34 and R35); no third attempt was to be silently substituted.
- Owner selected successor G0-05 trial R5 and G0-07-B prospective successor path.
- G0-06 prior captures passed, while an unattended attempt failed closed because the repository root was not the Git worktree root.
- G0-04 remains dependent on a natural qualifying transition.
- G0-08/G0-12/G0-14 remain blocked behind successor G0-05 work.

The accelerated path does not erase these records and does not itself authorize real money.

## 5. PCR production-candidate state

PCR-0 through PCR-3 are treated as PASS/READY for the accelerated software-readiness track.

### Current sealed PCR-3 runtime on VPS

Active execution-disabled release:

`pcr3-execution-disabled-e0383a50e2cc`

Source revision:

`e0383a50e2cce9639bee50b0e53f8d5c0db798a8`

Task:

`XAUUSD Execution-Disabled Shadow`

Last verified operational properties:
- task Running;
- MT5 connected after natural-disconnect recovery;
- execution capability `ABSENT`;
- `execution_enabled=false`;
- broker action count `0`;
- open positions `0`;
- pending orders `0`;
- analyst transport disabled;
- alert delivery disabled;
- PCR-3 sealed release remains unmodified in place.

The shared VPS Git worktree intentionally remains on `e0383a50e2cce9639bee50b0e53f8d5c0db798a8`; later GitHub revisions have been fetched/materialized into isolated build roots instead of overwriting the shared worktree, because existing Gate-0 scheduled tasks reference the same repository surface.

## 6. PCR-3 soak and recovery evidence

The key token-4 lineage ran from:

`2026-10-14T00:11:42.916851Z`

until first fault:

`2026-10-16T09:22:06.452025Z`

Duration before first fault:

**57.173 hours**

Evidence:
- 13,563 input observations;
- 13,563 decisions;
- maximum input gap 16.581 seconds;
- no fault/shutdown until hour 57.173;
- all decisions were `QUARANTINED`;
- execution remained disabled;
- broker action count remained 0;
- exposure remained zero.

The later natural disconnect was correctly handled fail-closed. A controlled recovery preflight and restart succeeded, advancing the fencing token from 4 to 5 with fresh observations/decisions and zero new broker actions.

### DEMO-ADMIT duration decision

For the accelerated demo path, the owner/assistant working decision is:

**The first 48 hours of the 57.173-hour operational lineage satisfy the DEMO-ADMIT minimum shadow-duration criterion.**

This decision is limited to the accelerated DEMO-ADMIT duration requirement. It does **not** convert the historical `QUARANTINED` runtime into a formal Gate-4 market-month pass, and it does not erase the fact that Event Guard/session/shock admission remained incomplete in that PCR-3 lineage.

## 7. DEMO-ADMIT account identity / read-only preflight

The VPS read-only DEMO-ADMIT preflight passed against the intended Exness MT5 demo environment.

Admitted identity:
- broker: `Exness Technologies Ltd`;
- server: `Exness-MT5Trial15`;
- currency: `USD`;
- account fingerprint SHA-256:
  `9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91`;
- account trade mode: MT5 DEMO;
- symbol: `XAUUSD`;
- open positions: 0;
- pending orders: 0;
- external Python trading: disabled.

The preflight did not submit or modify any order and did not disturb PCR-3.

## 8. DEMO-ADMIT implementation lineage

### PR #5 — merged

PR #5 introduced the separate bounded demo package.

Approved head:

`32ef6dbb937ba09315350a7259feae5acfe20be7`

Approved base:

`e0383a50e2cce9639bee50b0e53f8d5c0db798a8`

Merge commit / resulting main:

`d87fab07af82aefb097841b4bd54832ddf3fa462`

Key controls:
- separate `xauusd-demo-adapter` package;
- MT5 DEMO trade-mode verification;
- exact broker/server/currency/account-fingerprint binding;
- live-account rejection;
- XAUUSD only;
- maximum 0.01 lot;
- zero existing positions/orders before new risk;
- maximum one post-submit position;
- protective stop required;
- explicit submission confirmation;
- bounded daily submission budget;
- durable request IDs;
- uncertain outcome latch requiring reconciliation;
- deterministic production Policy A Risk Governor binding;
- time-bounded owner-gated activation permit;
- package boundary keeps order capability outside the execution-disabled PCR package.

Exact-head CI was green on Windows and Ubuntu.

## 9. DEMO-ADMIT VPS staging R2 — PASS

The first two staging attempts failed closed for tooling/script reasons and are preserved as evidence:
- R0: Python build module unavailable;
- R1: Windows PowerShell 5.1-safe version-capture defect.

Neither failed attempt reached order-capable broker calls.

The corrected R2 staging completed successfully.

R2 release ID:

`demo-admit-d87fab07af82-r2`

Exact source revision staged:

`d87fab07af82aefb097841b4bd54832ddf3fa462`

Hashes:
- source archive SHA-256:
  `b3b5a6841e9d7b4518b88f08d837af1d5a0108a0b4f4934459a8d5b1d72f9865`
- production wheel SHA-256:
  `9b9211950c02010eeed9741a0469722714cde017fb22e0ce27f4e90a7dddf482`
- demo wheel SHA-256:
  `27fe0f0c0620c82b75e4b063942d0ce7ffbda5cece91f7852895a60a849dfbc8`
- release manifest SHA-256:
  `dc2a2f9ed6917968cbd2a35434e441eb184af6425630e7d838f4e59774d62a35`

R2 verified:
- native Windows validation PASS;
- Ruff PASS;
- mypy PASS;
- 12/12 demo tests PASS;
- package boundary PASS;
- production + demo wheels built separately;
- sealed artifact installed alongside PCR-3;
- live execution-off demo adapter preflight PASS;
- exact demo identity verified;
- MT5 DEMO mode verified;
- XAUUSD only;
- 0.01 lot cap;
- zero positions/orders;
- external Python trading remained disabled;
- no activation permit present;
- no broker action authorized;
- no demo order submitted;
- PCR-3 remained isolated and Running.

R2 is therefore valid evidence for the PR #5 code lineage, but it does not contain the later PR #6 kill/quarantine controls and must not be treated as the final successor runtime.

## 10. PR #6 — durable kill/quarantine controls — merged

PR #6 exact approved head:

`0f75511d06ee7a803711c6ac28afb8553bf42a7a`

Exact approved base:

`d87fab07af82aefb097841b4bd54832ddf3fa462`

Merge commit / current main:

`33b7ebb664d4c343dd6d8dc77544cfdb17bab6bf`

PR #6 adds:
- durable demo control database;
- initial/default state `KILLED`;
- `ACTIVE` only after exact owner-gated activation permit plus explicit arm confirmation;
- owner kill returns state to `KILLED`;
- uncertain submission and critical pre-submit failures latch `QUARANTINED`;
- `QUARANTINED` cannot directly re-arm;
- explicit reset to `KILLED` is required before any fresh arm;
- invalid/expired activation permit kills the active control;
- demo calibration must include a source SHA-256;
- calibration scope must be exactly `DEMO_LIFECYCLE_ONLY`;
- the deterministic Policy A binding accepts only the exact calibration-object SHA-256 admitted in policy.

Exact-head validation:
- Validate records workflow: PASS;
- demo-admit workflow: PASS;
- Windows Python 3.12: Ruff PASS, strict mypy PASS, 19/19 tests PASS, package boundary PASS, separate demo wheel build PASS;
- Ubuntu Python 3.12: same PASS set.

## 11. Current DEMO-ADMIT blocker

**No numeric demo adverse-cost calibration is admitted yet.**

This is deliberate.

Existing historical empirical calibration evidence includes fail-closed / nonstationary findings and must not be silently promoted into a passed production calibration.

Therefore the next substantive step is to create a **conservative, source-backed, demo-lifecycle-only calibration** for the deterministic Policy A inputs:

- `current_adverse_cost`
- `stressed_adverse_cost`

The calibration must:
- be prospectively registered before use;
- identify its source with SHA-256;
- be scoped `DEMO_LIFECYCLE_ONLY`;
- use exact Decimal values;
- be validated against the intended Exness demo/XAUUSD environment;
- be hash-bound into the demo policy;
- not claim real-money validity;
- not overwrite or reinterpret prior failed/nonstationary calibration evidence.

A fresh read-only VPS capture may be used as evidence, but no missing cost component may be silently replaced with zero.

After calibration admission:
1. merge the calibration/control successor code/artifacts through the normal exact-SHA approval process;
2. build and stage a successor demo release from current main (or later exact approved main), execution still OFF;
3. verify the new durable control defaults `KILLED`;
4. verify the exact calibration hash is bound;
5. verify account identity/exposure again;
6. then make the final DEMO-ADMIT decision.

## 12. Current authorization boundary

As of this state record:

**Authorized / completed**
- repository implementation and offline testing described above;
- read-only VPS account/preflight checks;
- execution-off staging R2 for the PR #5 lineage;
- PCR-3 execution-disabled continuous shadow/recovery.

**Not authorized**
- enabling MT5 external-Python trading;
- arming demo control;
- creating an active APC-DEMO permit;
- `order_check` / `order_calc_margin` / `order_send` as part of an activated broker-action path unless separately approved;
- submitting, modifying, cancelling, or closing any demo order;
- any live-account broker action;
- real-money trading;
- modifying unrelated VPS scheduled tasks/services.

A future APC-DEMO approval must be explicit and identity-bound.

## 13. VPS isolation rule

The VPS hosts unrelated scheduled tasks/services. XAUUSD work must not affect them.

Hard rule:
- mutate only exact XAUUSD-approved paths/tasks;
- never bulk-edit Task Scheduler;
- never stop/start/edit SignalProof, VowSig, TradingTop, Windows, or other unrelated tasks;
- prefer isolated build/staging directories over changing the shared repository worktree;
- preserve Gate-0 task script surfaces unless a specific change is approved;
- use project-local Python/tooling where possible;
- run read-only isolation checks after meaningful VPS changes;
- stop and ask before any change that could overlap another project/service.

## 14. Owner approval model

Do not collapse approval boundaries.

Treat these as separate:
- GitHub branch/code preparation;
- PR merge;
- VPS source sync/build/staging;
- scheduled-task/service mutation;
- MT5 external-Python enablement;
- demo broker action;
- live broker action.

An approval for one does not imply another.

## 15. New-chat operating procedure

Every new chat continuing this project must:

1. reconcile the private repository first;
2. verify current `main` SHA;
3. read this file and the authoritative records it references;
4. inspect later commits/PRs after the as-of SHA before acting;
5. prefer GitHub evidence over chat memory;
6. write every material new decision/result back to GitHub before ending the chat or before relying on it in another chat;
7. preserve exact SHAs, hashes, failure records, and authorization boundaries;
8. never infer demo/live permission from general statements such as "continue";
9. keep external Python trading disabled unless a separately explicit activation approval exists.

## 16. Files that should be read with this state record

At minimum:
- `MASTER_ROADMAP_TO_PRODUCTION.md`
- `phase0/DECISION_LOG.md`
- `phase0/roadmap/ACCELERATED_PRODUCTION_CANDIDATE_PLAN_2026-10-05.md`
- `phase0/roadmap/APC_BASELINE_ACCEPTANCE_2026-10-05.json`
- `phase0/roadmap/DEMO_ADMIT_IMPLEMENTATION_REGISTRATION_2026-10-18.json`
- `phase0/roadmap/DEMO_ADMIT_OPERATIONAL_CONTROLS_REGISTRATION_2026-10-18.json`
- `phase0/specifications/RISK_GOVERNOR_POLICY_A_SPEC.md`
- `phase0/calibration/XAUUSD_EMPIRICAL_CALIBRATION_2026-08-12.md`
- `phase0/validation/empirical_calibration/DUKASCOPY_CALIBRATION_REPORT_2026-08-24_R3.json`
- `demo_adapter/README.md`
- `demo_adapter/src/xauusd_demo/control.py`
- `demo_adapter/src/xauusd_demo/risk_binding.py`
- `demo_adapter/src/xauusd_demo/mt5_demo.py`

Also inspect PR #5 and PR #6 and all commits after this file's recorded main before making decisions.

---

**Next substantive action:** prospectively register and obtain source-backed evidence for the demo-lifecycle-only adverse-cost calibration, while keeping broker execution disabled.


## 17. 2026-10-20 APC-DEMO-CANARY CONSOLIDATION (UNMERGED BRANCH, NOT AN ADMISSION)

Owner redirected the project toward the shortest safe **ONE controlled Exness demo canary lifecycle**, not tiny A2/B/C/D approvals. A fresh independent branch from frozen main `ccaa8338aecee8bd3afbc358644410dff6c512e5` contains the execution-disabled consolidated demo-canary risk/lifecycle and read-only preflight source with offline tests. Historical draft PRs #8–#22 remain untouched and unmerged; R1 and R2 separate consumed FAIL_CLOSED, A1 consumed FAIL_CLOSED and A2 unexecuted/superseded. The old paragraph above about requiring 4h source-backed calibration before any demo action is a historical scope; revised **DEMO_CANARY_ONLY** hypothetical cost envelope and strict broker metadata verification is allowed for *one* demo lifecycle only, never for real money or restricted autonomous demo admission.

Read first `phase0/roadmap/APC_DEMO_CANARY_CONSOLIDATION_2026-10-20.md`, `phase0/roadmap/APC_DEMO_CANARY_PROSPECTIVE_REGISTRATION_2026-10-20.json` and `phase0/roadmap/CROSS_CHAT_HANDOFF_APC_DEMO_CANARY_2026-10-20.md` on the new consolidated branch and its exact final PR HEAD/CI artifact SHA. Reuse frozen main controls; original `mt5_demo.py` full cash-risk QUARANTINE remains intact and is **not removed**. New separate one-entry/one-close canary module is explicitly owner-gated and inert absent direct approved use. Full hypothetical loss-to-stop cash-risk, frozen M1 margin, exact Exness DEMO fingerprint and symbol required; unknown outcome permanently latches QUARANTINED, never automatic retry.

Next three meaningful owner boundaries: (1) one attended MT5 read-only preflight with potential initialize side effects; (2) execution-off VPS isolated staging (GitHub merge independent, not mandatory); (3) one explicit APC-DEMO-CANARY covering at most one entry and one controlled closure and disabling after. **No approval for any of those has been given**, no Python/MT5/broker action performed in this consolidation, no VPS or Scheduler/PCR3/Gate0 changes, real-money still disabled.
