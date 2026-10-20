# CURRENT PROJECT STATE — XAU/USD Autonomous Trading Agent

## CURRENT S2 PRE-APC STATUS (2026-10-21) — DEDICATED DEMO TERMINAL UNVERIFIED

Original sealed S2 PR24 artifact was **owner-reported staged PASS on separate attended attempt #2**, with KILLED/UNUSED and zero broker actions; prior attempt #1 remains immutable FAIL_CLOSED_PRE_PYTHON_HASH. **No re-staging is needed or authorized**. Source-of-truth reconciliation on production `main ccaa8338aecee8bd3afbc358644410dff6c512e5` and PR23–PR26 unchanged/unmerged. Detailed non-executable final-preauthorization report: `phase0/roadmap/APC_DEMO_CANARY_FINAL_PREAUTH_GATE_2026-10-21.md`.

**ACTIVE BLOCKER IS NOW HUMAN DEMO-ONLY TERMINAL CREDENTIAL ATTESTATION**, not historical broader calibration. The previous current-blocker adverse-cost item remains historically applicable to **broader operating-condition or production admission**, but does not prevent the narrowly admitted `DEMO_CANARY_ONLY` deterministic envelope (entry slippage $0.50/oz, gap $2.00/oz, commission $5, swap $2) already source-tested and staged. It is NOT validated real-money calibration.

Existing MT5 terminal was previously observed logged into admitted Exness DEMO. **That observation does NOT prove there are no saved live account credentials**. Owner must inspect MT5 Navigator > Accounts (all server groups), confirm single demo-only remembered login and never-saved live credentials under this user/terminal profile, no alternate auto-switch actor; do not send passwords, login numbers or perform GUI modifications. If unknown/false, no broker APC; a new clean demo-only terminal would need separate VPS authorization.

**ALSO MISSING** exact owner-selected BUY or SELL, tick-aligned protective SL and BUY maximum entry ceiling/SELL minimum entry floor grounded in **fresh** XAUUSD Exness broker quote and a test rationale. Frozen risk veto includes full worst-entry-to-stop <=min($25,0.25% min(equity,balance,$10k)), stressed/current M1 margin >=1000% and >=90% free margin/equity, 0.01 lot, no exposure, fresh tick <=5 sec, spread <=$1/oz, independent symbol/account metadata. Activation ID and short UTC expiry must be literal in final APC and reused unchanged for entry/close; durable source does NOT freeze expiry between invocations, so this is a human procedural gate. Only manual external Python ENABLE -> one order -> known-ticket CLOSE -> DISABLE under separate APC; unknown result QUARANTINED/human reconcile, never retry or auto-close unknown exposure. No source, VPS, MT5, broker or trading modifications in this review.

**DECISION: `APC_DEMO_CANARY_AUTHORIZATION_NOT_READY`** pending owner attestation + exact side/SL/limit and session binding; current permission remains no MT5 attach/order/check/margin, trading toggle or real money.

---


## CURRENT VERIFIED S2 STAGE OUTCOME (2026-10-21)

**Most recent owner-reported attended VPS result: `S2_STAGE_ATTEMPT2_PASS_EXECUTION_OFF`.** Complete unchanged console output and SHA evidence at [PR26 stage-2 evidence](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/26#issuecomment-6299700345). Original second approval is **consumed** and cannot be reused. It is evidence from owner-pasted stdout, not an independently inspected host.

Exact reviewed PR26 helper SHA256 `fdb5624830b0741437b0a7e8697491db687c7e2d8af9b0ef494217d5556951e1`, in-memory Python SHA256 `3cf6ad71737766365874eef4d950fc93ae4169c60e1158ff1735e9dabf82a648`, original PR24 transport ZIP artifact ID 12289594320 SHA256 `596390ca92ec7cb94200a38f04a155ed5273f49bc84e9c9a16ebe48e5e05a160`, immutable sealed inner S2 ZIP SHA256 `6c37704c7d2d661ccb2b8fd4fbd5340ec35fb210f1cf9528452bc89bd08c1a4e`, immutable S2 source HEAD `89711065a3a2d38fe02282fff3ad1782aabda0d2`, stage helper HEAD `ab98292dde5c6bda9fc63a85eb36aaac36ed605d`.

**Staged only in NEW** `C:\Users\Administrator\AppData\Local\XAUUSD-APC-DEMO-CANARY-S2`, durable `KILLED`, `UNUSED` one-entry journal, MetaTrader5 **NOT IMPORTED**, **zero broker actions**. Previously existing MT5 PID6216 preserved by verified wrapper. Both required final `APC_STAGE_SUCCESS_EXECUTION_OFF_NO_TRADING` and `APC_STAGE_VERIFIED__KILLED__UNUSED__MT5_UNTOUCHED` markers present. The previous **S2 attempt #1 remains immutable `FAIL_CLOSED_PRE_PYTHON_HASH`**; original distinct PR23 stage PASS remains untouched.

**NEXT restriction:** neither VPS staging approval permits a broker action. No more VPS activity without a new meaningful authorization. Dedicated demo-only terminal with no live credentials, exact owner side/SL/price-limit, one attended external-Python manual enable->entry->known close->disable, fresh account/quote/exposure checks, full Policy A+M1 and final verified broker flat/KILLED/trading-disabled controls still need to be bound to a separate APC-DEMO-CANARY authorization. Unknown outcome QUARANTINED/human reconcile, never retry. Real-money entirely unauthorized.

---

**As-of date:** 2026-10-18  
**Authoritative code base:** private GitHub repository `alisufyan-ai7/xauusd-autonomous-trading-agent`  
**Current merged `main`:** `ccaa8338aecee8bd3afbc358644410dff6c512e5`

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


## 18. 2026-10-20 S2 successor code review after owner staging PASS (NO S2 STAGE OR BROKER AUTHORIZATION)

Owner-reported execution-OFF staging of frozen PR23 remains immutable PASS: previous stage `C:\Users\Administrator\AppData\Local\XAUUSD-APC-DEMO-CANARY` KILLED/UNUSED, no MT5 import/broker action. Frozen exact PR23 `e32f6dda35b2f29f2f5c0d762d0d26846bc5f384`, original inner ZIP SHA256 `61535b668da13605d62a00517bc76cc6b4b918eab1db769b001e64b1bfa241a5`. Production main unchanged at `ccaa8338aecee8bd3afbc358644410dff6c512e5`, PRs historical unmerged, R1/R2/A1 consumed distinct fail-closed, A2 unexecuted.

Full static audit discovered previously insufficient post-entry side/magic/fill/deal binding and no owner price ceiling/floor. New **separately sealed successor S2** on draft stacked GitHub branch `implementation/apc-demo-canary-s2-execution-closure-20261020` fixes and adds adversarial tests; no modifications to old staged artifact and no VPS activity under this task. Also adds isolated manifest/site tamper-checking S2 loader and owner-gated PS5.1 operator launcher, explicit manual MT5 external Python enable/disable and human emergency runbook. Exact prospective source and sequence: `phase0/roadmap/APC_DEMO_CANARY_S2_SAFETY_AND_ATTENDED_RUNBOOK_2026-10-20.md`. Read-first next chat: `phase0/roadmap/CROSS_CHAT_HANDOFF_APC_DEMO_CANARY_S2_2026-10-20.md`. Current in-repo status is OFFLINE PREPARATION; final SHA, CI, bundle artifact and hashes must be read from the S2 PR comment after CI.

**IMPORTANT:** S2 is **not** staged on VPS; the old stage cannot be silently upgraded/overwritten. New successor requires a future owner-authorized one-time **execution-off new S2 root** staging before any trade, plus exact owner authorization for **one** bounded demo canary. Owner specifies exact side, SL, BUY ceiling/SELL floor; no blind retry or automatic unknown-exposure closure. Dedicated demo-only terminal without live credentials and human confirmation that external Python is re-disabled are necessary operational controls. Real-money remains disabled. 


## 19. FINAL 2026-10-20 S2 OFFLINE REVIEW COMPLETE / NEW VPS STAGING NOT AUTHORIZED

For newest authoritative source of truth use `phase0/roadmap/CROSS_CHAT_HANDOFF_APC_DEMO_CANARY_S2_2026-10-20.md` on ops successor branch and the PR24 final SHA/CI comment. Frozen original PR23 `e32f6dda35b2f29f2f5c0d762d0d26846bc5f384` staged with KILLED/UNUSED PASS and remains immutable. S2 *separate* draft PR24 exact tested HEAD `89711065a3a2d38fe02282fff3ad1782aabda0d2`, 3/3 workflows green (Windows 53 PASS, Linux 49 PASS/4 Windows-only skips). Uploaded artifact ID `12289594320`; SHA256 of inner sealed S2 ZIP `6c37704c7d2d661ccb2b8fd4fbd5340ec35fb210f1cf9528452bc89bd08c1a4e`, manifest `70bf8637208772e91a64b7af2cc06997847dc557752b05d9225b735b30ff13be`. Hash of all seven component files independently checked.

**HISTORICAL SUPERSEDED S2 staging helper (wrong default artifact ID; do not use):** hash-pinned source in `ops/apc-demo-canary-s2-pinned-execution-off-stage-20261020` at helper code commit `105a9e348659aa7431b7eff07ea6b3d3f787bba9`, `phase0/ops/apc-demo-canary-s2-execution-off-stage.ps1`, SHA256 `03685894ed2249daed63b5ba7bcb60ec5e9db44892b26fa3b1e9d5baf0508166`. Embedded Python SHA256 `5e720a128551351ebfb09bd7b18adfc3776764b0da43371c9a1818698039e349`. S2 must go into NEW `%LOCALAPPDATA%\XAUUSD-APC-DEMO-CANARY-S2`, never old stage. Prior owner staging approval consumed; new S2 execution-off VPS staging **requires new explicit owner permission**. Another future separate APC-DEMO-CANARY broker grant can only be considered after new stage PASS plus dedicated demo-only terminal, exact owner side/stop/price bound, full Policy A USD risk/M1, human external-Python enable/disable and known-ticket supervised closure readiness. No VPS/broker actions during S2 work; real money disabled.


## 20. CURRENT TOP-LEVEL MAIN / S2 STAGING ARTIFACT DEFECT CORRECTION (2026-10-21)

**Verified production `main`:** `ccaa8338aecee8bd3afbc358644410dff6c512e5`, reflected correctly in the top-level **Current merged main** field (historical PR6 merge `33b7ebb664d4c343dd6d8dc77544cfdb17bab6bf` preserved in its prior-lineage record).

**CURRENT usable S2 helper source** is on `ops/apc-demo-canary-s2-pinned-execution-off-stage-20261020`, corrected helper commit **`ba10183e6735e820d8dcbed1e7ddc871b36a4830`**, SHA256 **`2c80339280d11fa635f8f739a2f12ecacca7c147de2ad4cfd937f98521a646a0`**, with default outer transport artifact **`github-actions-artifact-12289594320.zip`**. The previous helper source commit `105a9e348659aa7431b7eff07ea6b3d3f787bba9` / SHA256 `03685894ed2249daed63b5ba7bcb60ec5e9db44892b26fa3b1e9d5baf0508166` had the incorrect default artifact `12289113540`; historically preserved, **superseded and not executable as current S2 preparation**. The embedded Python helper SHA `5e720a128551351ebfb09bd7b18adfc3776764b0da43371c9a1818698039e349`, final S2 sealed ZIP SHA `6c37704c7d2d661ccb2b8fd4fbd5340ec35fb210f1cf9528452bc89bd08c1a4e` and manifest SHA `70bf8637208772e91a64b7af2cc06997847dc557752b05d9225b735b30ff13be` are **unchanged**.

**Safety & authority:** PR23/PR24 draft and unmerged. Original owner-reported execution-OFF stage KILLED/UNUSED PASS stays intact; no new S2 stage executed. Owner approval required separately for **ONE new S2 execution-OFF staging**; no MT5 interaction, trading enablement, broker action, PR merge, or demo/live order permission from this correction.


## 21. 2026-10-21 S2 FIRST ATTENDED STAGING ATTEMPT — FAIL_CLOSED PRE-PYTHON

The **first** owner-approved S2 execution-off VPS staging attempt was **consumed and FAIL_CLOSED**. Owner stdout verified outer helper source SHA256 `2c80339280d11fa635f8f739a2f12ecacca7c147de2ad4cfd937f98521a646a0`, then emitted actual in-memory SHA256 `3cf6ad71737766365874eef4d950fc93ae4169c60e1158ff1735e9dabf82a648`, followed by `APC_STAGE_HELPER_SHA256_MISMATCH__NOT_EXECUTED` at line290. Source proves **no Python staging call reached**, therefore no stage was created by this attempt; no MT5/broker/order call in the path. Original PR23 old stage remains distinct immutable KILLED/UNUSED PASS. Do not relabel S2 attempt as PASS or retry under original approval.

Offline root cause: PR25 pinned `5e720a128551351ebfb09bd7b18adfc3776764b0da43371c9a1818698039e349` from double trailing LF Python test; PowerShell runtime canonical here-string has one LF and hashes to `3cf6ad71737766365874eef4d950fc93ae4169c60e1158ff1735e9dabf82a648`. **Prospective PR26** branch `fix/apc-demo-canary-s2-ps-here-string-hash-20261021` corrects the expected hash and adds native Windows AST-derived SHA test. Candidate new outer helper SHA256 `fdb5624830b0741437b0a7e8697491db687c7e2d8af9b0ef494217d5556951e1`; native Windows PS5.1 AST-value hash check passed in offline-canary CI run 39482995784, Windows 55 PASS and Linux 50 PASS/5 Windows skips; final exact HEAD/CI pinned in PR26 completion comment. Original PR25 and hashes preserved, main and PR23/24 unchanged. NO VPS rerun, S2 stage still NOT installed/admitted, no trading permission. Next fresh approval only after CI and owner review, never silent retry; real money disabled.
