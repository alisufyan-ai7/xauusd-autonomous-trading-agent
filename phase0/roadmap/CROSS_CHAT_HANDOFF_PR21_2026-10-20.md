# READ FIRST — XAU/USD Autonomous Trading Agent — prospective D0-R3 handoff (2026-10-20)

**REPOSITORY AUTHORITY: PRIVATE GITHUB ONLY.** This is a navigation snapshot, not VPS/MT5 approval. Read this file first **on active stacked draft PR after PR20**, verify live exact SHA from PR metadata, then consult `phase0/roadmap/CURRENT_PROJECT_STATE.md`, `phase0/roadmap/CURRENT_PROJECT_STATE_2026-10-18.json`, `phase0/roadmap/DEMO_V12_D0_R2_STATIC_VPS_SURVEY_OWNER_REPORTED_2026-10-20.md`, `phase0/roadmap/DEMO_V12_D0_R3_PROSPECTIVE_NONEXECUTABLE_REGISTRATION_2026-10-20.json`, `phase0/roadmap/DEMO_V12_D0_R3_PHASED_RUNTIME_VERIFICATION_DESIGN_2026-10-20.md`, and prior `phase0/roadmap/CROSS_CHAT_HANDOFF_PR20_2026-10-20.md` / immutable R1/R2 incident files. Final validated PR HEAD, workflow IDs and file hashes must be pinned in the new PR conversation after CI, because files cannot reference their own final commit SHA.

**Reconciled baseline:** `main ccaa8338aecee8bd3afbc358644410dff6c512e5`; unchanged approved DESIGN-only PR13 `847829378956670e8936bf46c82e685de41145fd`; direct parent PR20 head `f255f59b401310a5acf2b3b0fc6169ac5635acc9`, draft unmerged; PR19 `ccee77501f74de7f59c457945a42609adf4bc6e5`; frozen R1/R2 source evidence unchanged. Every existing #8–#20 draft PR remains unmerged at this preparation baseline. No actual VPS access, Python launch, MT5 or broker access by the assistant. No trading authorization.

## New owner-reported static survey now durable

Owner-approved PR20 read-only file/registry/PATH/process survey SHA `e6095ec5b12a47ea86f6767008027c13e8d0e862ecec50b1a6725024f7c37605` passed its own inline SHA guard and completed at owner-reported `2026-10-20T14:22:43.0554548Z`.

- **Python candidate** `C:\Program Files\Python312\python.exe`, system-level `VENV=False`; on-disk `MetaTrader5` directory and dist-info both `True`. Version and import NOT YET PROVEN.
- **Terminal** count exactly 1, PID `6216`, executable `C:\Program Files\MetaTrader 5\terminal64.exe`. Point-in-time OS evidence, not currently guaranteed.
- The survey launched **no Python or MT5 processes** and called no MT5/broker APIs; it wrote no files.
- R2 bootstrap's narrow Python locator missed `C:\Program Files\Python312\python.exe`; absence was never established.
- This output is **owner-supplied** not independently authenticated host evidence. Do not equate on-disk presence with executable import compatibility.

## Distinct immutable fails

**R1** registration SHA256 `ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534`, consumed, `FAIL_CLOSED` before attachment due to PowerShell `$Host` reserved-variable collision. **R2** registration SHA256 `13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61`, consumed, `FAIL_CLOSED` before attachment at `NO_EXISTING_PYTHON312_WITH_MT5_PREATTACH_FAIL`. Both must remain immutable: no rerun, deletion, reclassification, restaging, or overwrite of original VPS evidence. No D0 source admission from either.

## Current prospective design — not executable permission

- New R3 distinct registration `phase0/roadmap/DEMO_V12_D0_R3_PROSPECTIVE_NONEXECUTABLE_REGISTRATION_2026-10-20.json`; four owner gates A version-only, B exact MetaTrader5 interpreter import, C OS terminal singleton+PID+path, D future separately registered and approved MT5 attach. A, B and C each require separate owner approval and complete output review. D is a separate **higher-risk broker/MT5 approval** and has no launcher in this PR. No phase approved or executed.
- Native PS5.1 prospective no-attachment script `demo_adapter/scripts/v12-d0-r3-phased-runtime-verifier.ps1`, explicit pinned interpreter and terminal path; two modes launch Python only if separately approved and C reads only OS process. Safe `-ShellOnlyTest` for offline tests.
- Frozen v1.2 Option A requires prospective broker-eligible full 240m XAUUSD capture, independently verified eligible overlap entry subwindow, date-specific Exness schedule/Event Guard, numerical adverse/stressed cost calibration and full broker-bound Policy A; **none of this is authorized or admitted by D0 R3 design**. Existing adapter remains hard QUARANTINED and external-Python trading disabled. PCR3, Gate0, SignalProof/VowSig/TradingTop and all Task Scheduler state unchanged.
- **NEXT ONLY OWNER APPROVAL** after exact-head CI: one attended, pinned-script **A VERSION_ONLY** runtime verification launching the discovered Python candidate without importing MT5 or calling broker, with stdout returned for review. This is NOT approved under GitHub-only preparation. Then request B separately, then C, and only afterwards evaluate a future D0 attachment approval. No preemptive B/C/D authorization.

**Stop after reporting DONE / IN PROGRESS / BLOCKED / NEXT with exact PR head, file hashes, Windows/Linux/record CI. No PR merges, VPS commands, MT5 imports, attachments, broker reads, capture, orders or live trading under this task.**


## SUPERSESSION — OWNER PHASE A1 HAS NOW FAILED CLOSED

Owner's one approved Phase A1 (PR21 pinned source SHA) verified the SHA but Python printed `File "<string>", line 1` and PowerShell `NativeCommandError` before any version PASS marker. A1 approval **CONSUMED; never rerun**. New separately stacked draft PR22 has immutable A1 incident `phase0/roadmap/DEMO_V12_D0_R3_PHASE_A1_OWNER_VPS_FAILURE_2026-10-20.md`, prospective A2 quote-free version-only script, native PS5.1 CI test, and UNAPPROVED A2 registration. Read `phase0/roadmap/CROSS_CHAT_HANDOFF_PR22_2026-10-20.md` and final PR22 CI/HEAD comment. Older next-owner statement about Phase A1 is historical and no longer an authorization. R1/R2 remain separately immutable FAIL_CLOSED, no MT5 broker read/trade or VPS change.
