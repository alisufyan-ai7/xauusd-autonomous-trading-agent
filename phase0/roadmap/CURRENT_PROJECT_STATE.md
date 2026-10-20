# CURRENT PROJECT STATE — XAU/USD Autonomous Trading Agent

**As-of date:** 2026-10-18  
**Authoritative code base:** private GitHub repository `alisufyan-ai7/xauusd-autonomous-trading-agent`  
**Reconciled merged `main` (2026-10-18):** `ccaa8338aecee8bd3afbc358644410dff6c512e5`

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

PR #6 merge commit (historical main at that point):

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

## 17. 2026-10-18 GitHub reconciliation and prospective calibration handoff — PR #8

- Reconciled actual `main` after PR #7 merge: `ccaa8338aecee8bd3afbc358644410dff6c512e5`. Compared against the prior `33b7ebb...` state: three commits ahead, only the two current-state files added; PRs #5, #6 and #7 merged. PR #7 head `e2e030c6e114bd3fb83c61b0908001df2834886c`; merge `ccaa8338aecee8bd3afbc358644410dff6c512e5`.
- **Draft PR #8**: [DEMO-ADMIT preregistration and review](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/8), branch `research/demo-admit-adverse-cost-prereg-20261018`, base `ccaa8338...`. Unmerged and **not authority** for execution, VPS action or source acquisition.
- Registered future `DEMO_LIFECYCLE_ONLY` read-only observation/Decimal derivation **method**, not cost numbers: `phase0/roadmap/DEMO_LIFECYCLE_COST_PREREGISTRATION_2026-10-18.json` and `phase0/roadmap/DEMO_LIFECYCLE_ADVERSE_COST_METHOD_2026-10-18.md`. All current/stressed calibration values and source SHA remain **NOT_ADMITTED**. No new Exness source capture was executed.
- Static gap review `phase0/roadmap/DEMO_ADMIT_RISK_GAP_REVIEW_2026-10-18.md` found the demo risk binding currently covers M1/V1 margin tests but does not compute USD entry-to-stop cash risk against full Policy A per-trade/period caps; also missing quote-freshness/calibrated-spread enforcement, missing-to-zero stops-level handling, source provenance admission verification, and accurate preflight control existence. These are **open pre-activation blockers**, not retrospective rejection of PRs #5/#6's 19 green tests.
- Dukascopy R3 `FAIL_CLOSED` and earlier PCR-3 `QUARANTINED` remain preserved. PCR-3 execution-disabled release, shared VPS worktree, XAUUSD scheduled task, other tasks and all broker state were **not touched** in this GitHub preparation step.
- **Next controlled action:** after owner exact-head review of PR #8, prepare and independently check a Windows PowerShell 5.1-compatible, statically allow-listed *read-only* XAUUSD collector in an isolated path, then request separate specific owner VPS-capture approval. No script/VPS run is authorized by PR #8; the numeric admission decision and successor implementation are later distinct gates.



## 18. Critical review of PR #8 duration — recommendation only (2026-10-18)

After a new exact GitHub reconciliation, draft PR #8's fixed `5 distinct market days + 3 rollover boundaries + 1 weekly reopening` was found to be a **candidate research-coverage choice**, not a frozen DEMO-ADMIT or Policy A entry criterion. A rigorous restricted-session DEMO-only alternative may reduce waiting by restricting trade entry to predeclared, liquid, owner-attended windows, not by assuming missing costs are zero or weakening Risk Governor limits.

The complete comparative review is `phase0/roadmap/DEMO_ADMIT_CALIBRATION_DURATION_CRITICAL_REVIEW_2026-10-18.md` in draft PR #8. It recommends evaluating a `v1.1_RESTRICTED_SESSION_PROPOSED` registration with a prospectively defined contiguous 4-hour eligible window, explicit sampling/gap/fee/swap/source evidence, strict unknown/boundary bans and unchanged risk-buffer/Decimal/hash/provenance rules. This is a design recommendation **not selected, accepted, registered as the active replacement or admitted**. The original v1.0 five-day preregistration is preserved unchanged and remains the only currently written preregistration; no capture has begun.

**Non-negotiable prerequisite:** correct the complete Policy A cash-risk binding for stop-loss USD planned loss, concurrent/daily/weekly/drawdown/streak, V1/M1, snapshot freshness and fail-closed unknown exposure **before any broker action**. A shorter quote sample cannot validate execution slippage or guarantee actual stop-loss fills. Position exposure may persist beyond an entry session, so supervised monitoring and explicitly authorized exit/emergency plans are required before any demo activation.

**Status:** PR #8 draft and unmerged; `main` remains `ccaa8338aecee8bd3afbc358644410dff6c512e5`; no VPS access/changes, MT5 execution enablement, permit or broker action was made by this review.

**Next owner decision needed (design only):** whether to select a prospectively frozen limited-session v1.1 method, or retain five-day/boundary coverage. Do **not request merge** until the method selection and revised exact-head review are completed. Each subsequent PR merge, VPS capture, staging and APC-DEMO action is independently gated.


## 19. OWNER DECISION — adopt restricted-session DEMO-ADMIT calibration v1.1 (2026-10-18)

**Authority: explicit owner design selection only.** Owner accepted the accelerated initial DEMO-ADMIT cost evidence method with one potentially qualifying four-hour contiguous liquid-session window. The four-hour threshold is an **engineering evidence gate** and carries no statistical-confidence claim. Any inadequate coverage or unsupported cost component fails closed and requires a new prospectively registered evidence window, with no favorable retuning.

Durable owner decision: `phase0/roadmap/DEMO_LIFECYCLE_CALIBRATION_OWNER_DECISION_2026-10-18.json`. **Selected prospective methodology:** `phase0/roadmap/DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_1_RESTRICTED_SESSION_2026-10-18.json`; interpretation `phase0/roadmap/DEMO_LIFECYCLE_COST_METHOD_V1_1_RESTRICTED_SESSION_2026-10-18.md`; exact window registration template `phase0/roadmap/DEMO_LIFECYCLE_V1_1_CAPTURE_WINDOW_TEMPLATE_2026-10-18.json`.

The original v1.0 `phase0/roadmap/DEMO_LIFECYCLE_COST_PREREGISTRATION_2026-10-18.json`, **Git blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77`**, is **IMMUTABLE, NOT SELECTED FOR INITIAL DEMO-ADMIT**. Its historical status, five-market-day/three-rollover/one-weekly-reopening protocol and all other failures remain preserved. Earlier §18 was an accurate *then-current* recommendation; this later owner decision supersedes §18's design-decision-pending state only, without changing its underlying historical record.

**Still unresolved:** no actual v1.1 source capture or verified numeric `current_adverse_cost`/`stressed_adverse_cost`, no calibration/source hash, no verified run-specific exact UTC window, and no calibration admission. The full Policy A pre-demo-order USD protective-stop loss formula (including commission, swap, slippage and gap), 0.25% dynamically scaled per-trade cap, USD 50 concurrent, USD 75 daily, USD 150 weekly, USD 500 drawdown, 3R pause, V1 0.01 lot, M1 stressed/current margin/free-margin and same-snapshot normalized accounting **must be implemented and independently tested before any demo action**. No cash-risk or execution boundary is waived.

Only evidence-supported liquid sessions may be used for *eventual* initial demo operations, excluding rollover, reopen, illiquid periods, high-impact events, shock/unknown states, unsupported guard conditions and holidays. A position may survive a permitted entry window; verified owner-attended position monitoring, planned-exit and human-only emergency protocol are mandatory before separate activation authority. Unknown exposure remains quarantined without automatic close.

**Approvals NOT granted:** merge PR #8, VPS access/source capture/staging/task actions, MT5 external Python trading enablement, active permit, APC-DEMO activation, demo orders, live/tiny-live trading. Sealed execution-disabled PCR-3 is unchanged to the best of previously verified GitHub state; no VPS verification took place in this turn.

**NEXT:** independently review v1.1 exact-head PR and continue offline-only preparation for read-only evidence collector, run-specific UTC window registration and full Policy A stop-loss USD-risk correction/tests. Obtain separate authorization before GitHub merge or any VPS evidence capture.

**Full Policy A correction test gate, frozen prospectively:** `phase0/roadmap/DEMO_ADMIT_FULL_POLICY_A_CORRECTION_TEST_REGISTRATION_2026-10-18.json` enumerates exact cash-risk formulas, fail-closed boundary cases and independent Windows/Linux offline tests. This registers engineering requirements; **the correction code is not yet implemented or validated**. In particular the old demo adapter remains blocked from demo orders. No calibration document alone can satisfy cash-risk admission.


## 20. 2026-10-18 successor engineering — PRs #9–#11 (read THIS latest section)

Later immutable stages supersede §19's then-current implementation-pending *status* without changing earlier records:

- **PR #9** `implementation/demo-policy-a-cashrisk-offline-20261018`, exact HEAD `6e5f32b771d511c670bbb348f0dd0fb427412fd5`, DRAFT UNMERGED: pure exact Decimal full Policy A USD worst-entry-to-protective-stop/fees and cash-risk mathematics implemented and synthetic Windows/Linux tested. The runtime `DemoMT5Adapter` intentionally **QUARANTINES before broker order_check/order_send** as no trustworthy end-to-end bridge has been admitted. Zero broker actions.
- **PR #10** `implementation/demo-evidence-bridge-v11-runner-offline-20261018`, exact HEAD `81ee6286fd2a3da528bed5c397ed816a103c1566`, DRAFT UNMERGED: offline source-pinned risk replay, four-hour injected read-only quote collector and undeployed Windows 5.1/MT5 read-only host, with synthetic validation. Caller hashes or apparent `INDEPENDENTLY_ADMITTED_FOR_REPLAY` labels do **not** authenticate broker/accounting providers.
- **PR #11** `research/demo-v11-tick-evidence-window-freeze-20261018`, reviewed exact HEAD `41f87a4db6e85a3cd16fc9fa3957478114af9272`, DRAFT UNMERGED: prospectively fixed `time_msc`/same-ms original source ordinals, flags and time crosscheck; all true adverse 1s/5s/30s tick matches in a **±250ms** window, fail-closed coverage; source registry for 11 independently verifiable broker/account/journal/fee/event classes; synthetic UTC-window checker; rejected candidate due official Exness centre-table overlap ambiguity and a known BLS release. See `phase0/roadmap/DEMO_V11_TICK_SOURCE_WINDOW_HANDOFF_2026-10-18.md`.
- Exact-head PR #11 GitHub [demo-admit run 39124407337](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39124407337) **PASS** Windows 115 tests / Ubuntu 114 tests + 1 Windows-only skip; [Validate records 39124407371](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39124407371) **PASS**. Earlier test fixture failures preserved.
- **No verified four-hour entirely eligible overlap registered; no live Exness-specific schedule, Event Guard, source SHA, cashflow or actual commission/swap/slippage/gap/FX evidence admitted.** The hypothetical 2026-10-20 13:00–17:00 UTC window is `NOT_SELECTED`, not permission to collect. Do not hide published Exness centre overlap difference: require instrument-specific verification, and if impossible request a prospective owner decision rather than silently widening scope. Owner consent to calibration *design* did not grant VPS/broker capture authority.
- **NEXT:** Independently reconcile session/holiday/DST/event Guard source evidence and exact eligible four-hour UTC overlap, or request owner scope clarification only if truly impossible; separately establish broker/journal/fee source provenance and exact hashes; then request separate read-only VPS approval for a precisely frozen run. Complete full broker-connected Policy A, lifecycle owner-attended exit safeguards and independent end-to-end tests before any demo permit.
- **Frozen:** Original v1.0 Git blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77` unchanged and NOT SELECTED initial, R3/Gate failures immutable, PCR3 QUARANTINED. PR #8/#9/#10/#11 all DRAFT UNMERGED; `main` still `ccaa8338aecee8bd3afbc358644410dff6c512e5`; no VPS, MT5, orders or trading enablement.


## 21. OWNER-GATED v1.1 session feasibility review — stacked draft PR #12 (2026-10-18)

The next offline-only work reviewed Exness's updated public instrument-hours page and the governing frozen `v1.1` strict London–New York overlap definition. The **published GENERIC trading-center** UTC table shows London 08:00–16:30; New York summer 13:30–20:00 and winter 14:30–21:00: exact center overlaps **180 minutes summer / 120 minutes winter**. A **contiguous four hours entirely inside the table's overlap is mechanically unavailable**, but that page is NOT a verified date-specific XAUUSD instrument/liquidity/maintenance schedule. No real qualifying four-hour interval, Event Guard run, broker audit or source SHA has been established. The earlier owner decision to collect *one qualified four-hour liquid-market window* stays valid; the narrower `v1.1` frozen engineering requirement `VERIFIED_LIQUID_LONDON_NEW_YORK_OVERLAP` must not be silently reinterpreted.

Draft PR #12 `research/demo-v11-session-eligibility-option-review-20261018` is stacked directly on **PR #11** and records `phase0/roadmap/DEMO_V11_SESSION_FEASIBILITY_OWNER_DECISION_REVIEW_2026-10-18.md`, `phase0/roadmap/DEMO_V11_SESSION_SCOPE_OWNER_OPTIONS_2026-10-18.json`, plus pure offline session-interval comparator/tests. Three **unselected** choices: **A recommended**—retain 240-minute verified eligible liquid **observation**, including narrower independently verified center overlap, with any later DEMO entries **overlap-only**, subject to separate owner prospective method registration; B—use only 180-minute/120-minute overlap evidence, with weaker coverage and separately approved successor registration; C—preserve literal four-hour full-overlap and remain blocked until independent contradicting source or prospective redesign. `selected_option=null`.

**New public calendar red flags**: Oct 20 08:30 US Eastern (12:30 UTC) U.S. Census new residential construction, Oct 20 10:00 ET (14:00 UTC) BLS state employment, and routine Thursday 08:30 ET DOL jobless claims (including externally listed Oct 22); no projected candidate can be labeled clean without independently admitted Event Guard classifications and full BLS/BEA/Fed/Census/DOL calendar source snapshots. The demo-account *Pro* product class is generally commission-free per public Exness guidance, but actual account type, fee waivers, swap and overnight administration fees remain **unverified and not numerically admitted**. No live account data received.

**Governance**: The original immutable v1.0 blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77` remains untouched/not selected for initial DEMO-ADMIT; PR #8/#9/#10/#11/#12 are DRAFT/UNMERGED; main remains `ccaa8338aecee8bd3afbc358644410dff6c512e5`. Full Policy A unchanged; existing PR #9 demo runtime hard QUARANTINE before any broker `order_check/order_send` remains active. No VPS/MT5/broker/source capture/trade or PR merge.

**NEXT OWNER DECISION (method only, not trade permission)**: review A/B/C in PR #12 and expressly select before any successor preregistration. Independently source and hash instrument-specific XAUUSD sessions, events/DST and fee/MT5 history only after appropriate separate read-only permission. If A is chosen, preserve 240-minute sampling and strict 180-minute summer / 120-minute winter overlap-only potential entry windows—never infer approval to capture or arm orders.


## 22. OWNER DECISION — OPTION A IN PRINCIPLE WITH SAFETY REFINEMENTS (2026-10-18; prior to successor artifacts)

**GitHub source-of-truth reconciled BEFORE THIS STATE UPDATE:** main `ccaa8338aecee8bd3afbc358644410dff6c512e5`; draft, open/unmerged PR #8 `8c3b83ba5edf83a8d4e5cc18096070fadf5c52e9`, #9 `6e5f32b771d511c670bbb348f0dd0fb427412fd5`, #10 `81ee6286fd2a3da528bed5c397ed816a103c1566`, #11 `5da628e9410c08467009cff1a8cdfe4440f0f414`, #12 `b03e1ba3ee2434744010ac8bdf37904ba19df730`. The selected historical v1.1 preregistration and immutable v1.0 blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77` are NOT amended. New prospective successor preparation happens ONLY on `research/demo-v12-option-a-safety-prereg-20261018`, stacked on PR #12, with no merge authorization.

**Explicit owner authority:** `OPTION_A_APPROVED_IN_PRINCIPLE_WITH_SAFETY_REFINEMENTS_DESIGN_ONLY`. Prepare a **separately versioned successor preregistration** for a single contiguous **240-minute** date-specifically verified broker-eligible XAUUSD **observation** interval; future *entry* may be permitted ONLY inside the independently verified London–New York overlap. The generic 12:30–16:30 UTC illustration is NOT a window selection, authorization or guarantee.

**Mandatory successor safeguards, prospective before an owner review:**

1. Derive `current_adverse_cost` **only** from eligible, independently verified, non-event conditions **inside the admitted overlap**. Exclude non-overlap and event/shock intervals even if inside the four-hour observation; do not shrink the baseline after seeing outcomes. A valid isolated overlap baseline must independently meet its prospectively specified sample/coverage and source-proof gates or FAIL CLOSED.
2. Derive `stressed_adverse_cost` conservatively using broader credible adverse evidence: **entire observed four-hour window**, plus separately admitted relevant stress/event observations; preserve provenance/regime labels and no cross-contamination of baseline. Notional stress floors (`>=2*current`) never establish stop-fill tail bounds. Missing relevant stress sources -> `NOT_ADMITTED` unless a prospective independently supported conservative allowance is explicitly admitted.
3. Read-only quote movements, spread and jumps are **quote proxies**, NEVER measured execution slippage, fill/stop guarantees or automatically USD risk. Preregister a transparent **conservative pre-demo slippage allowance/floor**, separately account for gap and commission with non-overlap proof and actual broker-specific tick-value loss/conversion. Later actual execution slippage must be measured and separately reviewed during any **later, separately authorized** bounded demo lifecycle; not now.
4. For initial DEMO-ADMIT, **every known/owned position must be confirmed flat BEFORE the permitted entry/session interval ends**, with broker positions/pending orders **reconciled**, planned exit cutoff and attended supervision validated and preregistered. Never assume stop/TP closes on schedule; if exit fails/unknown, QUARANTINE + human-only emergency, **no automatic unknown-exposure close**. Rollover, weekly reopen and overnight holding forbidden unless separately admitted prospectively.
5. Before a real run window is chosen, require date-specific official Exness XAUUSD symbol session / holiday / daylight-saving schedule and independent Event Guard calendar/health classification, quote freshness, normal liquidity and approved provenance hashes. No currently chosen real UTC start/end; no evidence source or numeric calibration admitted.
6. Full immutable Policy A USD stop-loss/commission/swap/slippage/gap and day/week/inception account risk, M1/V1, E1 human-only emergency, P1 human-gated resumption, existing kill/quarantine and reconciliation remain mandatory without waiver.

**Approval limitations:** Owner explicitly **did NOT authorize** PR #12 or any successor merge, VPS access, real XAUUSD capture, MT5 configuration changes, external-Python trading enabling, orders, demo or live positions. **No authority yet to select an exact real capture window or deploy collector.** This is **not final approval of successor preregistration**; present the prospective version and independent tests for a new exact-head owner decision, and STOP at that genuine approval boundary.

**Immediate action on this branch:** first update both `CURRENT_PROJECT_STATE` files to durably record this owner decision; only then create new prospective preregistration, offline validation and synthetic adversarial tests. Maintain old state sections as historical snapshots (earlier `selected_option:null` meant *before* this in-principle owner decision).


## 23. v1.2 Option A separate successor prepared — DESIGN TESTS ONLY (2026-10-18)

Following §22's **prior** owner-decision reconciliation and update of BOTH authoritative state files, offline source-only work is recorded in stacked **draft PR #13**, branch `research/demo-v12-option-a-safety-prereg-20261018`, parent PR #12 exact SHA `b03e1ba3ee2434744010ac8bdf37904ba19df730`. The new **separate** prospective draft files are `DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_2_OPTION_A_SAFETY_2026-10-18.json`, `DEMO_LIFECYCLE_COST_METHOD_V1_2_OPTION_A_SAFETY_2026-10-18.md`, `DEMO_V12_OPTION_A_RUN_WINDOW_TEMPLATE_UNREGISTERED_2026-10-18.json` and a full owner-boundary handoff `DEMO_V12_OPTION_A_OWNER_APPROVAL_HANDOFF_2026-10-18.md` (all `phase0/roadmap`). Four-hour real UTC source/window and all numerical `current_adverse_cost`/`stressed_adverse_cost` **remain NULL**.

Offline-only code and adversarial Python test fixtures live in `demo_adapter/scripts/v12_option_a_cost_recipe.py`, `demo_adapter/scripts/v12_option_a_flat_lifecycle.py` and corresponding `test_v12_*` tests. These separately calculate current using **only proven non-event overlap** and stressed using **full four-hour + independent relevant event/stress evidence**; require a positive preregistered quote-movement-based *slippage proxy floor*, never call quote movement executed fill slippage, require owner-attended strict positive exit/reconcile deadline **before earlier overlap/broker end**, zero owned positions and pending orders, human-only E1 quarantine for unknown exposure and no overnight/rollover. Their math outputs are **synthetic, not admitted source/calibration or demo permission**; a matching caller pin alone never proves broker origin. The PR #9 runtime hard send/check veto is unchanged.

**IMPORTANT:** owner accepted Option A **IN PRINCIPLE**, not final approval to merge or deploy this v1.2 successor. Pending a separate exact-head owner design decision after independent Windows/Linux CI, STOP. Preserve original v1.0 immutable `3e6e0d19e70da5a02002615160e3f0c0a0367b77` (not selected initial), v1.1, PRs #8–#12 and old failures unmodified; all new PRs draft/unmerged; `main` `ccaa8338aecee8bd3afbc358644410dff6c512e5`. No VPS/MT5/config/trading toggle, date-specific capture, demo/live orders or owner permit.


## 24. OWNER-APPROVED FINAL v1.2 OPTION A DESIGN — DESIGN ONLY (2026-10-19 Asia/Karachi)

**APPROVED FOR PROSPECTIVE DESIGN ONLY** at exact GitHub [PR #13](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/13) immutable HEAD `847829378956670e8936bf46c82e685de41145fd`, stacked on exact unmerged PR #12 HEAD `b03e1ba3ee2434744010ac8bdf37904ba19df730`. Owner approval was recorded durably as **PR #13 comment ID 6256228112** *before* child-branch implementation. Frozen separate v1.2 prereg file Git blob `c7dcf520fe2a3b12437cec6a1b5dd06c25494d5f`; frozen historical v1.0 and v1.1 blobs `3e6e0d19e70da5a02002615160e3f0c0a0367b77` and `5210056f0a07faad9225e24228392f43090c5561`. **None may be rewritten**. Prior Gate 0 FAIL_CLOSED/PCR3 QUARANTINED evidence stays immutable.

**Scope of approval:** v1.2 Option A method/preregistration alone: contiguous four-hour independently verified Exness XAUUSD liquid observation, eventual demo entries restricted to a separate verified non-event London–NY overlap; current costs from overlap only and stress costs from full four hours + relevant independently admissible event/stress evidence; preregister separately proven conservative quote-proxy slippage floor, not measured execution slippage; initial DEMO-ADMIT positions/pendings independently reconciled flat *strictly before* earlier entry overlap/broker session end with attended supervised exit, no rollover/overnight. Maintain full immutable Policy A and hard `QUARANTINE before order_check/order_send` submission veto.

**Not approved:** any PR merge (#8–#13 or successors), VPS access/mutation, MT5 connect/config, real data capture or actual source-acquisition transaction, external-Python trading enablement, demo/live order submission/modification/cancel/close, real money; no numeric USD quote slippage/gap, source SHA provenance, exact UTC capture interval or trader permit admitted. No source or demo operation may occur from passing synthetic tests.

**Execution strategy after owner decision:** preserve the approved exact PR13 HEAD without further commits. Child branch `implementation/demo-v12-offline-evidence-gates-20261019` is stacked ON PR13 and may contain *offline-only* independent manifest/provenance/admission-readiness code, tests and this state update, with a DRAFT new PR. This is next owner-independent work, not a v1.3 method change. STOP before the next genuine separate real-world broker/source-capture approval. The machine-readable state includes `v12_design_final_approval_2026_10_19`.


## 25. OWNER-APPROVED v1.2 controlled READ-ONLY EVIDENCE PHASE — PREPARATION ONLY (2026-10-19)

Owner authorized official independent source verification, future source-hashed four-hour date-specific window registration, PS5.1 isolated collector/independent verifier implementation and read-only evidence stage, **but explicitly required the complete exact UTC/source SHA/private destination/one-command packet BEFORE THE FIRST ACTUAL VPS/MT5 RUN**. PR #13 exact frozen approved Option A design `847829378956670e8936bf46c82e685de41145fd` and PR #14 offline preflight `9d768fcfd160b3ccfc92ecef44fe040da6b77db6`; new descendant **DRAFT PR #15** `implementation/demo-v12-readonly-vps-prep-20261019` is implementation preparation, not permission for actual execution, merger or trading.

**Public source review:** `phase0/roadmap/DEMO_V12_OFFICIAL_SOURCES_QUALIFICATION_STATUS_2026-10-19.json` records actual verified official Exness/BLS/BEA/Fed/Census links and event UTC details, while honestly identifying the lack of *date-specific dynamic Exness XAUUSD broker hours and original official raw byte SHA256*, actual Event Guard health and independent broker-specific fee/tick/USD, gap and stress sources. NO qualifying 240-minute date or overlap is frozen. `12:30–16:30 UTC` is only an illustration. No real XAUUSD market data was read.

**Prepared PS5.1 and raw-source pins (GitHub exact LF bytes):** `demo_adapter/scripts/v12-readonly-collector.ps1` SHA256 `03d8e7cdaa5cbf8de79f9b20327548a060f5e0feb809509a87ffd224c3f67222`; independent `v12-readonly-verifier.ps1` SHA256 `a808c47d4668038161400d8a8444d63d1edb67f9920225974a052993025772a7`; `v12_windows_mt5_readonly_host.py` SHA256 `fd2dac266bdb1083d0dcb062b95d279abd3cbf1d1938cb0c8109ecdddcfd2687`. All dependent SHA256 are separately registered in `DEMO_V12_READONLY_SOURCE_SHA256_PIN_MANIFEST_2026-10-19.json`; narrowly scoped `.gitattributes` fixes LF checkout, independent Python hash test verifies. The single PS5.1 collector is not to be called on VPS until **exact owner final first-run confirmation** and real source/session, private folder and process proof. Verifier itself has no MT5 operation. Python host is allowlisted read-only; `initialize()` may launch a terminal despite preexisting-process guard, so supervised method review is required.

**NO REAL RUN REGISTRATION:** `DEMO_V12_EXACT_FIRST_READONLY_RUN_UNFROZEN_TEMPLATE_2026-10-19.json` has `NULL` real UTC boundaries, original Exness/agency/Guard raw hashes, private destination and owner first-run approval; intentionally cannot execute. The code is merely prepared and offline-tested. `DEMO_V12_READONLY_FIRST_RUN_PREPARATION_HANDOFF_2026-10-19.md` details the official-source evidence and residual partial-failure evidence retention caveat, immutable risk and next action. Do not convert a synthetically validated read-only registration into real capture, a `current_adverse_cost` or `stressed_adverse_cost` admission, or trading permit. Need a separate exact owner first-run confirmation packet, consisting of frozen complete source/date/provenance, code-hash and private output and **one safe copy-paste PowerShell command**, presented to owner before execution.

**All restrictions unchanged:** PR #8–#15 DRAFT/UNMERGED; `main` unchanged `ccaa8338aecee8bd3afbc358644410dff6c512e5`; frozen v1.0 Git blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77`, v1.1 `5210056f0a07faad9225e24228392f43090c5561`, v1.2 `c7dcf520fe2a3b12437cec6a1b5dd06c25494d5f`. PCR3 and prior failures preserved. No VPS connection/mutation, MT5 broker interaction, scheduler changes, external-Python trading enablement, demo or live orders, order modifications, cancellations or close, risk-gate waiver, automatic unknown-exposure closure.

## 26. v1.2 owner-independent qualification + immutable failure attempts — DRAFT PR16 (2026-10-19)

**GitHub reconciled** production `main ccaa8338aecee8bd3afbc358644410dff6c512e5`; original approved v1.2 PR13 HEAD `847829378956670e8936bf46c82e685de41145fd`, offline PR14 `9d768fcfd160b3ccfc92ecef44fe040da6b77db6`, original read-only PR15 HEAD `cbb8f3bf0fc0e46fb187f62a3e849341756a4f80`. All PR8–PR15 remain DRAFT UNMERGED. New descendant `implementation/demo-v12-immutable-failure-evidence-20261019` is **DRAFT PR16**, not a change to the approved PR13 design, original PR15 branch or frozen preregistrations.

**Current evidence outcome (B):** A full date-specific, independently original-source-authenticated Exness XAUUSD 240-minute full-eligible observation + corresponding independently event-free, liquid London–NY overlap **cannot presently be certified for any near-term date** from available admissible source evidence. It is NOT proof such sessions do not exist. Official Exness date/instrument-specific widget output, original source body sha256, live Event Guard health and complete official release inventory are absent; the model-side direct HTTPS byte download is unavailable. All real observation and entry UTC fields remain NULL; no actual broker/cost source, quote, execution slippage, positive stressed/current cash reserve or source authenticity can be claimed. A *partial* 19 October–2 November calendar screen has only NEGATIVE/UNKNOWN verdicts, including Oct20 Census/BLS events, Oct21 BLS, Oct22/29 Thursday DOL, Oct27/28 Census/FOMC, Oct29 BEA/BLS and Oct30 ECI; Oct23/26 partial non-event appearance is not a qualifying permit. Official UK DST transition October 25 precedes US DST transition November 1 and requires fresh actual broker schedule confirmation. See `phase0/roadmap/DEMO_V12_NEAR_TERM_SOURCE_QUALIFICATION_2026-10-19.json` and `DEMO_V12_FAILCLOSED_ATTEMPT_AND_NEAR_TERM_QUALIFICATION_2026-10-19.md`.

**Exact frozen Event Guard implementation inspected:** `src/xauusd_agent/guards/event_guard.py` TIER_1 ±30m, TIER_2 ±15m; unknown tier, source/coverage disagreement, shock lock, tentative/suspended times, unverified normalization are NOT admitted. Do not invent a favorable tier or trim an event-contaminated 4h after observing it. Official published source summary is not original authenticated source bytes. No read-only VPS scan performed to clear these unknowns.

**PR16 ONLY — protected crash/partial evidence:** new `demo_adapter/scripts/v12_attempt_journal.py` and `v12_journaled_readonly_port.py` add private exclusive-create, deterministic per-registration fsynced JSONL hash-chain `ATTEMPT_STARTED` BEFORE MT5 initialize, each 5s XAUUSD poll, each true tick 10m chunk (flags/time/ordinal), broker connectivity and zero exposure reads, and `FAIL_CLOSED` versus `INCOMPLETE_FAIL_CLOSED` classifications if interrupted. Same registration cannot be retried/relabelled PASS, even after a crash. The private independent verifier checks journal chain and raw SHA and does not admit any current/stressed costs, fills or broker orders. **SHA chains alone are NOT external tamper-proof origin**: preserve the privately created file independently. Updated PS5.1 collector/verifier and isolated Python host have NEW SHA256 in `DEMO_V12_READONLY_SOURCE_SHA256_PIN_MANIFEST_2026-10-19.json`; **former PR15 SHA trio is superseded and MUST NOT be executed**. Updated `.gitattributes` pins LF and offline synthetic Windows/Linux tests cover duplicate attempts, tamper, truncation, early abort, and partial quote/tick retention.

**No first run:** `DEMO_V12_EXACT_FIRST_READONLY_RUN_UNFROZEN_TEMPLATE_2026-10-19.json` remains NOT EXECUTABLE; future journal module SHA fields, exact privately admitted raw sources, UTC windows, output directory, terminal path and final first-run owner confirmation NOT REGISTERED. **No Task Scheduler/PCR3/VPS/MT5/terminal/position changes, no broker quote capture, no unapproved API calls, no PR merge, no demo/live orders**. Frozen earlier v1.0 `3e6e0d19e70da5a02002615160e3f0c0a0367b77`, v1.1 `5210056f0a07faad9225e24228392f43090c5561`, and owner-approved v1.2 `c7dcf520fe2a3b12437cec6a1b5dd06c25494d5f` Git blobs unchanged. Full Policy A, runtime kill/quarantine, E1/P1 preserved. Next **single owner confirmation** when complete, NOT NOW: `APPROVE FIRST EXACT SOURCE-QUALIFIED XAUUSD 4H VPS READ-ONLY CAPTURE AT PINNED SHA/PATH`, with one complete PS5.1 command displayed beforehand.

**Windows CI safety correction (2026-10-19):** exact canonical per-event SHA256 journal initially failed native Windows tests because OS default text-mode `os.open()` could convert LF to CRLF. Fixed with explicit `os.O_BINARY` before writing fsynced journal; new exact journal SHA256 is `547131361b690e95c6718734b6de727e812346e92af8c1a20ced4f6dbc12ef06`. Prior red CI is preserved, not reclassified. Collector/verifier/host SHAs unchanged from the latest PR16 pinned manifest. Independently revalidate final exact head on both operating systems. Still no original source SHA, UTC window, first VPS run or any broker action.


## 27. 2026-10-20 RESUMPTION AFTER UI TIMEOUT — IMMUTABLE FAILURE LEDGER COMPLETED; NEAR-TERM WINDOW STILL NOT QUALIFIABLE

Owner requested to continue the GitHub owner-independent offline work following a ChatGPT message timeout without reopening prior PRs, rerunning broker capture or losing source-truth context. Reconciled production `main ccaa8338aecee8bd3afbc358644410dff6c512e5`, owner-approved immutable PR13 `847829378956670e8936bf46c82e685de41145fd`, immutable PR14 `9d768fcfd160b3ccfc92ecef44fe040da6b77db6`, unexecuted PR15 `cbb8f3bf0fc0e46fb187f62a3e849341756a4f80`. Existing successor draft **PR16** `implementation/demo-v12-immutable-failure-evidence-20261019` remains stacked on PR15; no merge.

**Offline source/dates conclusion (STOP B):** `phase0/roadmap/DEMO_V12_SOURCE_CANDIDATE_QUALIFICATION_2026-10-20.json` screens 2026-10-20 through 2026-10-29 against official published Exness/BLS/BEA/Fed/Census/DOL website content. Oct23 is merely an early *calendar screening candidate*, NOT a capture date. Exact four-hour UTC observation and entry overlap remain **NULL** because externally verifiable raw original Exness **date-specific XAUUSD instrument** full-open schedule, authoritative source-response SHA256 and *healthy/live/normalized Event Guard* are missing. Public search results are not original-source bytes; independent HTTPS direct downloading was unavailable through the offline container network. Failure to qualify dates from available evidence **does not prove market closed**. Exact date-specific open/full-eligibility and official-response provenance cannot be filled by conjecture.

**PR16 fail-closed source improvement:** exclusive-create registration-named private journal started/fynced **before any MT5 initialize**, per-read/per-poll and 10-minute true-tick chunk ordered raw XAUUSD evidence, hash chain, Windows binary LF, terminal FAIL_CLOSED, crash/interruption INCOMPLETE_FAIL_CLOSED, no repeat under same registration. Independent PS5.1 verifier now verifies hash-chained attempt success, exact private raw SHA and all original admission rules. A Windows admin could still delete/replace private journal; protected external checkpoint and owner-attested first-run lineage remain needed before the real run. Exact new SHA manifest at `phase0/roadmap/DEMO_V12_READONLY_SOURCE_SHA256_PIN_MANIFEST_2026-10-19.json` publishes revised collector `94d04fa7cd43dc7c92220808410f3135cf91256c80caec59bd3295ea01050c50`, verifier `fe9b19f074f26b3479204cddc8774f504613adcc915af154b6a28b6b60ebedd3`, host `5a3f4bab1f775739dcfb1c4c0a1d15ce2b3977c0309b520a4f63227425110c46`, attempt ledger `547131361b690e95c6718734b6de727e812346e92af8c1a20ced4f6dbc12ef06`, journaled port `085d6d51c4634e8ca60c59f9b78c381c6b8d3a7231eebc16ac73843d35cd1cd9` and all frozen v1.1 dependency pins. OLD PR15 hashes remain historical, now superseded ONLY on PR16 for any prospective first execution. Full durable handoff `DEMO_V12_QUALIFICATION_AND_IMMUTABLE_ATTEMPT_HANDOFF_2026-10-20.md`.

**No permission upgrade:** Actual first-run registration `DEMO_V12_EXACT_FIRST_READONLY_RUN_UNFROZEN_TEMPLATE_2026-10-19.json` remains deliberately NONEXECUTABLE with NULL UTC, Exness and Event Guard original SHA, private path and first-run owner confirmation ID. No VPS/MT5 connection, read or setting change; no job/task edits; no new unknown-exposure closures; PCR3 and older Gate failed evidence sealed; v1.0/v1.1/v1.2 prereg Git blobs unchanged; all PR #8–#16 draft/unmerged and main unchanged. Frozen Policy A, E1/P1 and broker-order hard QUARANTINE preserved. NEXT SINGLE owner approval **ONLY AFTER** complete actual provenance/window: first exact dated registered XAUUSD 4h VPS READ-ONLY capture, no trading. No command should be supplied until source packet complete.

## 28. PR17 OFFICIAL ORIGINAL HTTPS SOURCE RESCUE + FROZEN POLICY A INDEPENDENT AUDIT (2026-10-20)

Following exact GitHub reconciliation of main `ccaa8338aecee8bd3afbc358644410dff6c512e5` and all draft, unmerged PR8–PR16, owner-independent PUBLIC source qualification advanced on **new draft PR17** `research/demo-v12-official-origin-and-policy-audit-20261020`, directly stacked on immutable PR16 HEAD `1f60b8f0f15c6c73f4ea77297252dc6178a490cd`. PR13 frozen approved Option A design `847829378956670e8936bf46c82e685de41145fd`, PR14 `9d768fcfd160b3ccfc92ecef44fe040da6b77db6`, PR15 `cbb8f3bf0fc0e46fb187f62a3e849341756a4f80`, original v1.0/v1.1/v1.2 prereg blobs and PCR3 failures all unchanged.

**New original government HTTPS bytes, URL/retrieval UTC/SHA-256, NOT source completion:** `research/public_source/original_body_fetch.py` with strict official-host allowlist, HTTPS CA, no cross-host redirects, identity encoding, byte-exact SHA and ephemeral private GitHub Actions archiving (configured retention 90 days). The 2026-10-20 GitHub run `39412951853` retrieved 8/11 original HTTP entity bodies including BEA, BLS Oct/Nov, Census, Fed Oct/Nov, GOV.UK and newly located DOL ETA weekly claims schedule at `https://oui.doleta.gov/unemploy/archive.asp` original SHA `3adf9e071bc6cf1d87bfca6dd4abff253ca6c1237faada6d28b89e4aa84c4ed1`. Authoritative source/original URL, precise retrieval timestamp, response metadata, original entity byte SHA and status 200/403/404: `phase0/roadmap/DEMO_V12_ORIGINAL_HTTPS_SOURCE_RUN_39412951853_2026-10-20.json`. Original bodies in private time-limited Actions artifact `12259344231`, **NOT PERMANENT OR EXTERNALLY WORM**. Two Exness URLs denied HTTP 403; older DOL link denied 404 (actual ETA archive alternative succeeded). Source URL alone, cached web text or matching HTTPS response SHA does **not** prove generated date-specific XAUUSD schedule/live broker/Guard origin. Partial original-source progress supersedes old statement `NO_ORIGINAL_BYTES_AT_ALL` prospectively only; prior failure evidence retained as history.

**Extended screening through November 30:** `phase0/roadmap/DEMO_V12_GUARD_SCREEN_OCT23_NOV30_2026_2026-10-20.json` keeps publication UTC events and original-source references (BLS Oct30 ECI, Nov3 JOLTS, Nov6 jobs, Nov10 CPI, Nov13 PPI, Nov17 import/export/Fed G.17, Nov18 minutes, recurring DOL and Nov25 DOL Thanksgiving exception). UK DST ends Oct25; US DST ends Nov1; no extrapolated XAUUSD hours. Each event tier UNKNOWN (not automatically TIER_2), blackout unknown, source health/coverage and normalization not certified. Frozen Event Guard Tier1 ±30m and Tier2 ±15m, unverified/tentative/source-health unknown FAIL CLOSED. **All screened dates UNQUALIFIED**, all exact UTC four-hour observation/entry subwindows `null`. Observation target needs 4h, **entry overlap need only be contained, not itself 4h**. No exact window selected.

**Frozen Policy A regression without mutation:** Offline tests verify planned USD ask/bid-to-stop risk plus mandatory fees/swap/positive prudent proxy/gap, max trade risk 0.25% of min(balance/equity/10k) up to $25, concurrent $50, day $75, week $150, drawdown $500, 3R pause, lot cap 0.01, current/stressed M1 ≥1000% and free-margin ≥90%, cost/source/unknown-exposure QUARANTINE, broker quote freshness ≤2s and protective stop geometry, Tier 1/Tier 2 event/normalization locks. No proven new risk-engine arithmetic defect; **actual broker-authoritative runtime full-cash reconciliation is still MISSING and adapter hard quarantine executes before order_check/send**. Green synthetic math NEVER means DEMO-ADMIT or execution permission. Collector/independent verifier/host/journal/port unchanged from PR16 and original SHA256 PIN manifest remains current.

**Authority and STOP-B:** first-run JSON remains NOT EXECUTABLE with missing original date-specific Exness XAUUSD instrument-specific schedule, blackout/Guard health, account-bound fees/cost/proxy data, verified source-original and long-term retention, actual private VPS path + terminal64.exe state, exact UTC 4h/overlap, registration SHA256 and owner run confirmation. No VPS/MT5 access, tradeapi toggle, scheduler/PCR3 changes, orders, or merge of PR8–PR17. Both authoritative state files and `DEMO_V12_QUALIFICATION_AND_IMMUTABLE_ATTEMPT_HANDOFF_2026-10-20.md` updated on PR17; full source run packet and future guard evidence are in the linked JSON records. **NEXT OWNER ACTION: NO OWNER ACTION YET.** Do not supply speculative PowerShell or ask for first capture permission before a complete prospectively registered packet is genuinely possible.


## 29. PR18 CRITICAL STOP-B REVIEW — D0 DISCOVERY IS SEPARATE FROM FROZEN QUALIFYING FOUR-HOUR CAPTURE (2026-10-20)

Owner directed independent decomposition instead of accepting prior PR17 `STOP-B / NO OWNER ACTION YET` mechanically. Reconciled exact main `ccaa8338aecee8bd3afbc358644410dff6c512e5`, approved PR13 `847829378956670e8936bf46c82e685de41145fd`, PR14 `9d768fcfd160b3ccfc92ecef44fe040da6b77db6`, PR15 `cbb8f3bf0fc0e46fb187f62a3e849341756a4f80`, PR16 `1f60b8f0f15c6c73f4ea77297252dc6178a490cd`, PR17 `6ac06d365214f1a0146b3669a529d14a127ca5de`; all 8–17 draft/unmerged, production main unchanged, PCR3 historical failures sealed. New **DRAFT unmerged PR18** `implementation/demo-v12-d0-source-discovery-readonly-20261020` stacked exactly on unchanged PR17.

**Critical frozen-policy reading:** Frozen owner-approved v1.2 prereg (`DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_2_OPTION_A_SAFETY_2026-10-18.json`, frozen blob `c7dcf520fe2a3b12437cec6a1b5dd06c25494d5f`) prohibits ***qualifying 240m capture*** when broker session or Event Guard is unknown, and requires official/broker schedule, event/holiday/DST/Guard evidence before selecting that future four-hour observation. Frozen method `DEMO_LIFECYCLE_COST_METHOD_V1_2_OPTION_A_SAFETY_2026-10-18.md`, **Exact UTC source registration**, agrees. It does **not** exclusively require obtaining Exness *public help webpage HTML SHA256* as the only legitimate origin evidence nor disallow a separate, individually owner-approved single-shot diagnostic that is *not counted in v1.2 evidence*. Previous PR17 `NO OWNER ACTION YET` inadvertently applied 4h admission prerequisites to even learning terminal-specific facts; that is overly broad. The full original 4h requirements remain unwaived. One symbol `trade_mode` and tick does not prove 240m trade eligibility.

**Prospective PR18 D0 (not 4h):** owner-gated single Windows PowerShell 5.1 wrapper `demo_adapter/scripts/v12-d0-readonly-inventory.ps1` SHA256 `adc226a7d21ca7eb296f100ad0a6c79d9554c76ca15ca260c3c82959f0312274`; Python read-only snapshot `demo_adapter/scripts/v12_d0_readonly_inventory.py` SHA256 `ea1496f715a6601f47098ee15a9d09645dc804a63ab9248fa60a4d36d3f52260`; unchanged private fsynced PR16 attempt journal `v12_attempt_journal.py` SHA256 `547131361b690e95c6718734b6de727e812346e92af8c1a20ced4f6dbc12ef06`; registration exact SHA256 `ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534`. All source bytes LF native Windows pinned and independently verified by synthetic tests, registration `DEMO_V12_D0_DIAGNOSTIC_NOT_CAPTURE_FROZEN_REGISTRATION_2026-10-20.json`, manifest `DEMO_V12_D0_SOURCE_AND_REGISTRATION_SHA256_MANIFEST_2026-10-20.json`; complete matrix/handoff `DEMO_V12_D0_STOPB_DECOMPOSITION_AND_MINIMUM_VPS_APPROVAL_HANDOFF_2026-10-20.md`.

**D0 hard boundaries:** one *pre-existing* Windows terminal64 process, exact process path and PID before/after; existing MetaTrader5 Python path, auto-discovered terminal EXE path, only `initialize(existing)`, `terminal_info`, `account_info`, `positions_get`, `orders_get`, `symbol_info(XAUUSD)`, `symbol_info_tick(XAUUSD)`, `shutdown`. Account DEMO Exness server/company/currency and frozen identity SHA checked; `tradeapi_disabled=true` and zero exposures both sides. No login/symbol_select/history, no order_check/order_calc_margin/order_send, no order modification or closing, no settings or tasks, no shared worktree mutation. Owner-only ACL new private evidence folder derived from `%LOCALAPPDATA%\XAUUSD-v12-D0-PrivateEvidence\<frozen D0 registration SHA>\`, O_EXCL fsynced JSONL attempt and SHA-bound raw snapshot, no rerun under same registration (success OR FAIL). **MetaTrader5.initialize may still launch/activate another terminal** and release Python attach via `shutdown`; the operator must explicitly approve this risk, wrapper checks same terminal PID/path before/after but cannot guarantee zero process side effects.

**D0 is discovery NOT admission:** cannot establish real broker fee/swap execution, full date-specific XAUUSD quote/close/maintenance schedule, authenticated full Event Guard health/normalization, source official webpage hash, four-hour tick protocol, correct overlap, numerical stress/current adverse cost, permission to collect 4h, or DEMO-ADMIT/trading. The previous `DEMO_V12_EXACT_FIRST_READONLY_RUN_UNFROZEN_TEMPLATE_2026-10-19.json` remains entirely NONEXECUTABLE, no new UTC, real source or owner ID. Full Policy A/E1/P1 frozen and hard runtime QUARANTINE unchanged; all historical v1.0/v1.1/v1.2 Git blobs unchanged, no VPS/MT5 accessed and no demo/live action.

**NEXT SINGLE OWNER BOUNDARY:** after exact PR18 Windows/Linux native CI and SHA validation, request **one** owner approval for **ONE supervised D0 DEMO read-only source-inventory** and isolated source staging (no full 4h capture), with all exact pins and private path recipe. Do NOT execute it or provide a broker-capture command until owner explicitly approves. In contrast, a qualifying 4h capture still requires separate original source/date/Guard admission and separate exact future owner permission. This is **STOP-A for D0**, not waiver of **STOP-B for v1.2 4h**.



## 30. 2026-10-20 OWNER VPS D0-R1 BOOTSTRAP FAILURE — PRE-ATTACH, NEVER RETRY SAME REGISTRATION

The owner approved one isolated attended D0 on draft PR18 SHA `3ff100189349ada29331730af99459fecc4ea821`, registration original source SHA256 `ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534`. The user then pasted **actual VPS PowerShell output** `Pasted text(20261020-125238).txt` of the additional *unreviewed chat-provided bootstrap* (not the exact GitHub pinned PS51 wrapper). It created an isolated private source stage under `%LOCALAPPDATA%\XAUUSD-v12-D0-IsolatedStage\<R1 SHA>`, reported two preflight proof hashes `914ae74caef38bd3a3b6f08cc9d18e8eaae161457d3d2a6f572ffd529f8d887b` and `1dac09c21c5ed2f7112d09abe662a7531d794f0189e254bfb9d6af2488a7f9a3`; these were emitted after staging and verifying all four original source bytes.

Then **BOOTSTRAP PRE-ATTACH FAIL_CLOSED** `SessionStateUnauthorizedAccessException: Cannot overwrite variable Host because it is read-only or constant` at line 127 of the inline script: `$Host = Join-Path ...`. `$Host` is a case-insensitive reserved PowerShell automatic variable. This is a previously untested error introduced by assistant-authored orchestration, NOT Exness/MT5 fault. Since the statement failed before Python candidate discovery, `Get-Process terminal64`, the vetted PS wrapper or `MetaTrader5.initialize`, **no MT5 attach, broker read, trade action, raw D0 evidence, journal or capture is evidenced by this log**. The actual VPS directory/journal existence has not yet been verified independently; preserve all artifacts and classify it as **FAILED CLOSED / NO D0 RESULT**, not PASS or broker problem.

**NO R1 rerun.** Do not delete/rewrite the existing R1 isolated stage, proof files, stdout, frozen R1 registration, original approved file/hash or turn this into an undocumented retry. Incident evidence/limitations and exact lines recorded at `phase0/roadmap/DEMO_V12_D0_R1_BOOTSTRAP_PREATTACH_FAILURE_2026-10-20.md`.

**Prospective correct path:** separate **new draft PR19** `fix/demo-v12-d0-bootstrap-failclosed-recovery-20261020`, stacked on unchanged exact PR18 head. New R2 registration original source SHA256 `13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61`, new GitHub-reviewed R2 bootstrap SHA256 `91d493b5af205fcf964ee1d051d9bd0f505d17ea0fad9f1d0ca3e59678e31087`, original PS51 wrapper `adc226a7d21ca7eb296f100ad0a6c79d9554c76ca15ca260c3c82959f0312274`, Python host `ea1496f715a6601f47098ee15a9d09645dc804a63ab9248fa60a4d36d3f52260`, journal `547131361b690e95c6718734b6de727e812346e92af8c1a20ced4f6dbc12ef06`. All raw source pins versioned in `phase0/roadmap/DEMO_V12_D0_R2_SOURCE_SHA256_MANIFEST_2026-10-20.json`. The new staging bootstrap does **not** assign to PowerShell reserved variables, has a no-Git/no-MT5 native Windows smoke branch and requires separate owner approval, distinct one-attempt registration and new isolated private source/evidence directories. All PRs remain draft/unmerged, all PCR3/historical fail evidence and main immutable, full v1.2 240m prereg still NOT EXECUTABLE; external Python trading disabled.

**No second VPS operation authorized as of this update.** Wait for exact-head CI pass and then **fresh separate explicit owner PR19 R2 one-shot read-only D0 authorization** before ANY further broker or VPS staging/MT5 attempt. An owner may perform a purely read-only preflight-artifact inspection if needed; this does NOT consume a new D0 registration but must not overwrite, delete or reuse R1 evidence. A mistaken CI PASS does not confer new owner consent.


**PR19 R2 offline recovery CI checkpoint:** exact tested head `702f7fbb90f5c82ccacb8983d57215590ff19e6e`, [Windows/Linux demo-admit run 39427969089](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39427969089): **Windows Python3.12 291 PASS** including native PS5.1 parser, guarded no-MT5/no-Git shell-only invocation and negative fresh-approval runtime; **Ubuntu 286 PASS / 5 Windows-only SKIP**. [records validation 39427968998](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39427968998): SUCCESS. Earlier R2 red CI failed for a reversed assertion (not trading code) and is preserved. D0-R2 is **not owner authorized**, no R2 VPS attempt; no broker data/capture or trade; do not reuse R1.


## 31. 2026-10-20 OWNER VPS D0-R2 SECOND PRE-ATTACH FAILURE — LIMITED PYTHON PATH DISCOVERY

Owner explicitly approved one draft PR19 exact HEAD `ccee77501f74de7f59c457945a42609adf4bc6e5`, new R2 registration `13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61` and reviewed R2 bootstrap `91d493b5af205fcf964ee1d051d9bd0f505d17ea0fad9f1d0ca3e59678e31087`, retaining unchanged PS wrapper/host/journal pins. User-provided PowerShell output shows the reviewed PR19 bootstrap verified its exact Git SHA and source hashes, and initial terminal64 PID **6216** at launcher preflight. R2 new staged evidence proof SHA256 in order: `d959a80482deea23b14e4c7be5ab9f2d02116d5ff2a26e3eb467bbf79229ad19`, `994def2e106407cfa4853a8ef764603226274aa4855990dac87ad1fa59a52be2`, `d4a3304354649fd295805760a2668374ae8b10163bedb605beb49aad597a6d21`. It then exited **`NO_EXISTING_PYTHON312_WITH_MT5_PREATTACH_FAIL`** at reviewed bootstrap line 130 *before invoking the reviewed D0 wrapper, MT5.initialize, account/position/order/symbol reads, or recording any real D0 JSON/journal*. No orders or trading actions evidenced. The path printed as `R2_PRIVATE_EVIDENCE_PATH` is a recipe, not proof that the private folder exists. The initial terminal PID was not verified at run end after this failure. This is **PREATTACH FAIL_CLOSED, no admitted D0 outcome**; original first R1 reserved `$Host` failure remains separately immutable.

Crucial scope: The Python preflight searched only working-tree `.venv`, Desktop repo `.venv`, `%LOCALAPPDATA%\Programs\Python\Python312`, `C:\Python312`, and first PATH Python. The Python `-B -c` test looked for Python3.12 and `importlib.util.find_spec("MetaTrader5")` without importing MT5. Failure **does not prove Python/MetaTrader5 is absent** or that demo broker terminal is unhealthy. Native source-attested original R1+R2 staging/output/proof files remain on VPS and must be preserved without deletion/relabeling. **No R2 rerun**; exact owner approval consumed.

New **draft unmerged PR20** `research/demo-v12-d0-r2-runtime-location-preflight-20261020`, stacked directly on approved unchanged PR19, contains durable incident `DEMO_V12_D0_R2_PREATTACH_RUNTIME_DISCOVERY_FAILURE_2026-10-20.md` and a **pure file/path/registry read-only** Windows PowerShell 5.1 survey `demo_adapter/scripts/v12-d0-r2-python-environment-readonly-survey.ps1`. This independent helper does **not** run Python, import or initialize MetaTrader5, use Git, create files, attach broker, or change MT5 settings/PCR3/services/tasks. A negative PATH candidate cannot itself prove all install paths excluded; scan result is only preliminary and is to be owner-shared. **No prospective D0-R3 registration or approval is present**; do not attach MT5 again without fresh exact registration and approval after reviewing legitimate runtime evidence. Approved PR13 v1.2 four-hour stop condition unchanged; no four-hour capture, demo/live trades, order APIs, external Python trading enablement, or any PR merge.


**PR20 independent runtime locator CI PASS (screen only):** exact tested head `539d7c1de326d9d8dc2f2c4dd701714e6ac81622`; [demo-admit run 39431811443](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39431811443) Windows Python 3.12 **293 PASS**, including actually running the native Windows PowerShell 5.1 zero-attachment static survey; Ubuntu **287 PASS, 6 Windows-specific SKIP**. [Validate records 39431811368](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39431811368): SUCCESS. Actual VPS python executable/MT5 on-disk distribution remains UNKNOWN until owner supplies the static survey output. Not a D0-R3 grant; no run or new registration. Preserve all previous R1/R2 preattach results.


## 32. FINAL CROSS-CHAT HANDOFF CHECKPOINT — 2026-10-20

The authoritative **new durable and read-first** index is `phase0/roadmap/CROSS_CHAT_HANDOFF_PR20_2026-10-20.md`, added on current draft PR #20 (`research/demo-v12-d0-r2-runtime-location-preflight-20261020`) only. This consolidates the *complete* open draft PR #8–#20 stack (heads #8–#19 frozen as checked; current PR20 exact live HEAD must be obtained from GitHub and final post-update validated HEAD/CI are pinned in PR20 description/comment). Production main remains `ccaa8338aecee8bd3afbc358644410dff6c512e5`, PR13 frozen design-only approval `847829378956670e8936bf46c82e685de41145fd`; PCR-3 and all previous R4/G0/D0 failures preserved.

**Chronology supersession is explicit:** Historical preregistration and PR19 files describing R2 as "unapproved"/"not yet executed" were true at their initial creation, **not the current state**. Owner later specifically approved **one** R2 at PR19 exact `ccee77501f74de7f59c457945a42609adf4bc6e5`. The user-run R2 bootstrap checked PR HEAD, SHA pins and initial terminal PID 6216, then failed `NO_EXISTING_PYTHON312_WITH_MT5_PREATTACH_FAIL` before MT5 import/attachment (restricted Python candidate paths). R1 and R2 are separately **FAIL_CLOSED, approvals consumed, never rerun** and original stages/proofs retained; neither proves lack of installed Python or MT5 or any broker trading result. R1 remains the earlier reserved PowerShell `$Host` failure before MT5. Detailed paths/proof SHA values in new handoff and individual immutable incident files. Future R3 does not exist or have permission.

Latest PR20 PS5.1 candidate environment survey `demo_adapter/scripts/v12-d0-r2-python-environment-readonly-survey.ps1` byte SHA256 `e6095ec5b12a47ea86f6767008027c13e8d0e862ecec50b1a6725024f7c37605` has passed native Windows offline validation and is **not run on owner's VPS**. It reads only filesystem, registered Python installation locations, PATH and process paths without running Python/MetaTrader5, importing MT5, modifying registry/files/task services or touching broker. Earlier passing CI `demo-admit 39432327785` Windows 293 / Linux 287+6 skip and records `39432327854` at historical prehandoff PR20 HEAD; exact **final post-handoff** HEAD and its own CI must be verified and pinned in PR20 conversation/body, not inferred from these historical runs.

**NEXT OWNER BOUNDARY:** a separate explicit approval for *only* a supervised, read-only static VPS Python-location survey after exact GH HEAD and script SHA verification; not a D0 R3, broker read, trade, or any VPS mutation. Then review owner's entire output before proposing a new prospectively registered D0 R3 and demanding its *own* exact owner approval. No command provided or executed during cross-chat handoff. Frozen full v1.2 240-minute date-specific Exness/Event Guard qualification remains incomplete. No MT5 trading setting toggle, no demo/live trade, no merge, no PCR3 mutation, no SignalProof/VowSig/TradingTop or Windows/system tasks, no shared Gate-0 script edit, no wildcard or bulk Task Scheduler changes.

**This handoff is DOCUMENTATION ONLY.** Older historical sections of this file are not retroactively rewritten. New chat must resolve the current live PR HEAD and pass/fail CI by querying GitHub, treating `CROSS_CHAT_HANDOFF_PR20_2026-10-20.md` as navigation index, not independently executable permission.


## 33. 2026-10-20 PR20 OWNER-RUN STATIC VPS SURVEY — SOURCE-QUALIFIED OUTPUT, NOT PYTHON/MT5 RUNTIME PROOF

The owner explicitly approved **only** the exact PR20 static path/registry/process-location survey (PR20 `f255f59b401310a5acf2b3b0fc6169ac5635acc9`, SHA256 `e6095ec5b12a47ea86f6767008027c13e8d0e862ecec50b1a6725024f7c37605`). Owner-supplied PowerShell stdout reports complete exact hash verification and scan at `2026-10-20T14:22:43.0554548Z`; no Python/MT5 launched, no writes or broker calls. Existing system Python executable candidate **`C:\Program Files\Python312\python.exe`** (not venv), MetaTrader5 package directory present on disk, matching distribution `.dist-info` present. Exactly one existing MT5 process: **PID 6216**, `C:\Program Files\MetaTrader 5\terminal64.exe`. The previous R2 narrow runtime path set omitted this location; R2 still **FAIL_CLOSED**, not retroactively repaired. These are owner-reported **on-disk and OS observations only**, not proven executable Python 3.12 / import / version / broker data. Raw selected stdout and limitations: `phase0/roadmap/DEMO_V12_D0_R2_STATIC_VPS_SURVEY_OWNER_REPORTED_2026-10-20.md`.

Owner additionally approved only GitHub **documentation and prospective design** for new D0-R3. New **draft unmerged successor** stacked directly on unchanged PR20 (active new PR number, SHA and exact-head CI must be read from latest PR metadata). Prepared distinct **NONEXECUTABLE** R3 registration `phase0/roadmap/DEMO_V12_D0_R3_PROSPECTIVE_NONEXECUTABLE_REGISTRATION_2026-10-20.json`, design `phase0/roadmap/DEMO_V12_D0_R3_PHASED_RUNTIME_VERIFICATION_DESIGN_2026-10-20.md` and separately phase-gated PS5.1 verifier `demo_adapter/scripts/v12-d0-r3-phased-runtime-verifier.ps1` with no MT5 initialize/broker/order code and offline regression `demo_adapter/tests/test_v12_d0_r3_phased_runtime_verifier.py`. Gate A version-only check runs *literal* existing Python candidate only after fresh owner authorization; Gate B import-only after A pass and separate authorization; Gate C OS terminal identity after B pass and separate authorization; Gate D is future separately authorized MT5 read-only attach with side-effect caveat, not implemented/approved. All runs on owner's VPS **NOT AUTHORIZED** during this work. Shell-only Windows CI may parse/execute non-runtime test branch without Python/MT5.

R1 and R2 both remain distinctly **consumed FAIL_CLOSED before MT5 attach**, no rerun, no original stage or registration edits, no broker D0 result. Future D0-R3 must have its own exact code, registration, source SHA, owner approval, private attempted-once evidence. No 240m capture, source/Guard cost calibration, demo/live orders or automatic risk grant. PCR3/Gate0/other VPS tasks and main untouched, external Python trading disabled, full Policy A hard veto in force.

**NEXT ONLY OWNER BOUNDARY:** after exact-head native Windows/Linux CI, request one supervised `VERSION_ONLY` approval and full output; do not supply or execute a runtime VPS command before approval. Handoff to read first: `phase0/roadmap/CROSS_CHAT_HANDOFF_PR21_2026-10-20.md`, then PR metadata for final SHA, hashes and workflows. Earlier sections 30–32 are accurate historical snapshots; this newer paragraph supersedes the earlier statement that the survey was not yet performed.
