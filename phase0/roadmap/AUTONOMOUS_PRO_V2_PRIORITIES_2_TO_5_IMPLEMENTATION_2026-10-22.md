# Autonomous Exness Pro XAUUSD v2 — priorities 2–5 engineering progress

**Date 2026-10-22 (Pakistan local). Status: experimental source + synthetic tests AUTHORED, no accepted native Python3.12 PASS, no VPS deployment, no broker activity.**

**Provenance:** owner approved first v2 execution-disabled engineering stage; PR31 v2 SPEC accepted and merged into main `95875ccf1bddc43491ced1dd4358057b62b7800e`. This new implementation branch is stacked above **draft/unmerged PR32** exact starting head `527b631c3a37bf1574266edb8e7b5b6e225e65ad`, not above main. Do not merge this child or assume its parent accepted. Current Policy A/numerical limitations and original Gate0 history remain authoritative.

## Priority 1: exact Python3.12 CI — currently BLOCKED, not green

- PR32 GitHub Actions `production-candidate` run `39758170391` (Windows job `119755375230`, Ubuntu job `119755375652`) and `Validate records` run `39758170378` (job `119755375608`) each returned FAILURE within seconds, steps null; Ubuntu job logs 404 BlobNotFound. Pattern previously seen on PR29. **Root cause undetermined**: cannot claim software failure or quota/runner/billing failure without direct account evidence.
- Isolated assistant environment has only Python3.13 and no Python3.12; `uv python install 3.12` cannot reach GitHub due to DNS/network isolation. No native 3.12 validation available here. Authors may use local 3.13 source sanity, but that is NOT exact Windows Python3.12 certification. Avoid repeated blind Actions reruns or touching running VPS. Owner can review GitHub Actions job page/account allowance/settings for missing workflow steps and provide evidence. Native Python3.12 exact-head tests can be run later in a separate environment under a safely scoped owner instruction.

## Priority 2: extended MT5 read-only ingestion — code PREPARED

- New `src/xauusd_agent/broker/v2_mt5_context_readonly.py`: extends established read-only `MT5ReadOnlyAdapter`, maps genuine broker W1/D1/M5/M1 timeframe constants, reuses H4/H1/M15 unchanged, requests from closed position=1, checks completed candles, ordered bars, UTC time and exact admitted sanitized account fingerprint/company/server/USD/DEMO mode before and after observations. MT5 external Python trading protection must remain **DISABLED**, and no broker order functions exist.
- **Account-mode bug identified while source reviewing:** legacy `observe_account` stores `str(trade_mode or '')`, which would render demo integer `0` as empty string; new port correctly revalidates raw `trade_mode == 0` or literal `DEMO` rather than falsely treating it as LIVE. This has NOT been tested on actual Exness MT5.
- Five synthetic MT5 tests are authored; no account number, password or API credential included. No actual broker connection occurred and extended source is not wired into the installed shadow scheduler. Real broker weekly/day close/session UTC/DST/calendar boundaries remain unverified, and the frozen full-strategy history requirements are separate.

## Priority 3: automatic objective TPB research detection — code PREPARED

- `src/xauusd_agent/features/v2_tpb_research.py` calculates a conservative *subset* of TPB Zone A from 300 H4/500 H1/1000 M15 completed bars: regime from H4 EMA20/50, ADX and DI, H1 confirmed swings and ATR/impulse, Zone A H1 EMA20 confluence and two closed M15 rejection/confirmation candles. Emits `NO_TRADE` or `TECHNICAL_HYPOTHESIS`, never a trade/order ticket or risk PASS. Return explicitly marks `execution_permitted=False`.
- **Important incompleteness:** not yet exact frozen P0-SETUPS-001 strategy: Zone B, multi-location H1 structure, complete first-zone-touch accounting, full time-expiry/cancellation, official event/session/spread/cost/ATR-percentile admission, historical replay/holdout evidence, and exact broker TP/SL grids remain missing. DO NOT assume it has a profitable edge or promote this to a real `SetupCandidate` automatically. Synthetic negative tests only; no positive TPB performance evidence.

## Priority 4: frozen Event Guard + AI Analyst bridge — code PREPARED

- `src/xauusd_agent/features/v2_shadow_analyst_event.py` calls the existing frozen pure `evaluate_event_guard` on an *externally supplied official-source* `EventObservation`; rejects unavailable inventory, source disagreement, shock lock, event epoch mismatch. Only when clear + technical research hypothesis exists can it form the minimized `AnalystRequest` for the existing strict schema; model verdict may yield only `RESEARCH_SETUP` or `NO_TRADE`, with `execution_permitted=False` always.
- Default `AnalystClient()` transport intentionally disabled. No OpenAI API/paid call or official internet capture was made. Tests use synthetic offline analyst and synthetic event feed. Actual Event Guard source capture and production model activation are independent owner-approved integration/evidence tasks.

## Priority 5: DEMO position management — PAPER ONLY, NOT BROKER EXECUTION

- `src/xauusd_agent/ops/v2_demo_paper_lifecycle.py` simulates DISARMED, READY, ENTRY_PENDING, POSITION_KNOWN, EXIT_PENDING, FLAT_RECONCILED, QUARANTINED with immutable revision fencing; accepts synthetic position ID/0.01 lot; only allows stop tightening (BUY higher / SELL lower), exact-known synthetic position exit and ambiguity quarantine; cannot resume quarantine or send any order. 7 paper tests authored.
- This is **not the requested order-capable DEMO execution runtime**; missing broker-calculated full Policy A cash risk, durable cross-process DB journal, real MT5 order_check/send, actual protective stop and fill retcode, trade-state reconciliation, daily/weekly loss caps and observed shutdown/alerts. Those require a distinct sealed release, exhaustive adversarial/native Windows testing and a separate explicit owner DEMO activation decision. No 48-hour autonomous DEMO observation has started.

## Files in this child branch (beyond parent PR32)

- broker `v2_mt5_context_readonly.py`
- features `v2_tpb_research.py`, `v2_shadow_analyst_event.py`
- operations `v2_demo_paper_lifecycle.py`
- 5 read-only adapter + 9 AI/Event/TPB reject + 7 lifecycle = **21 authored tests** in three new files (in addition to PR32's 13 unverified tests), all presently NOT VERIFIED PASS.
- this decision/evidence document, plus read-first human/machine state updates.

## Additional cash-risk engineering (post-first draft, 2026-10-22)

- Added `src/xauusd_agent/risk/v2_cash_preflight.py`: PURE nonexecuting check requiring explicit source-verification booleans and finite Decimal broker stop-loss, commission, swap, slippage and gap reserves; enforces current frozen 0.25% eligible-capital planned loss, only 0.01 lots, USD50 concurrent, USD75 daily, USD150 weekly, USD500 drawdown, streak >=3 pause and calls the existing deterministic current+2x stressed M1 margin/free-equity governor. Even a passing result carries `execution_permitted=False`; no `order_calc_profit` or `order_calc_margin` is invoked here and supplied 'broker-derived' values have **not** been obtained from Exness.
- Added five synthetic tests `tests/unit/risk/test_v2_cash_preflight.py`, including $300 Pro account min-lot infeasibility, unknown costs, period limits and M1 guard; **tests are authored but Python3.12 evidence remains NOT VERIFIED**. Total child tests authored is now **26 (5+9+7+5)**, all 0 verified native pass. Parent PR32 separately has 13 authored tests.
- New PR33 GitHub Actions exact prior head `e38dd91a62673dbda7ce5f6d657759963d14b5da` runs `39761671235` production-candidate and `39761671259` Validate records both immediately reported `FAILURE`. No Python3.12 test PASS; do not claim PR33 quality gate solved. Billing/runner entitlement are possible hypotheses per GitHub official troubleshooting docs, not a verified root cause for this private account.
- The cash-risk preflight and paper lifecycle are not wired to a real order-capable MT5 adapter or persistent broker ledger. This is a preexecution simulation aid, **not** a full admissible DEMO trading system. The frozen Policy A is not modified.
## Isolated Python3.12 Windows fallback — prepared, NOT EXECUTED

Added [`phase0/ops/v2_pr33_isolated_py312_source_tests_20261022.ps1`](../ops/v2_pr33_isolated_py312_source_tests_20261022.ps1). It pins exact pre-script source commit `4bfb431daf078c84d4189a4c033a2d607ae53004` and verifies that commit is an ancestor of current fetched branch; archives it into a brand-new TEMP directory without checkout/reset/pull of the existing Windows live worktree. It selects a pre-existing Python3.12 interpreter and pytest, compiles the archived source, runs the parent+child **39 authored synthetic tests**, then checks the execution-disabled capability guard. It neither installs dependencies nor connects to MT5, writes trading settings, modifies scheduled tasks, enables trading or sends a broker order. This script has **NOT** been executed on a native Windows host and cannot be credited as a PASS. Owner can choose to run it in a separately attended verification step; exact terminal output must be reviewed before merge. The new script is a testing aid, not production software.
## Immediate next engineering gate

1. Confirm root cause of pre-test GitHub Actions failures through repo Actions UI/account settings or an independent native Python3.12 environment. Collect exact logs; do not mark any current source PASS.
2. Independently test full historical XAUUSD W1/D1/M5/M1 acquisition on a **read-only** Exness Pro DEMO session, with verified exact fingerprint and disabled external-Python trading, including session gap/DST; new owner permission needed for any VPS operation.
3. Complete frozen TPB technical/oracle predicates, source healthy Event Guard inputs, canonical setup identities and registered chrono OOS/realistic cost evaluation without execution.
4. Implement a separate broker-bound, tested full Policy A/cash-risk + durable lifecycle with source checks, no unknown-exposure auto close, rollback, watchdog and human E1/P1. Seek a **new explicit** DEMO enable/order APC only once the executable release is verified.

**Never interpret owner's general 'proceed with engineering priorities' as account funding, broker order/API-toggle, paid OpenAI transport, relaxing fixed 0.25%/0.01 caps or live-money consent.** No Standard Cent; original PCR3, S2 stage and all historical Gate0 failures preserved.

## Latest 2026-10-22 CI recovery, source safety review and next read-only broker proof

Owner reported billing issue resolved. Native GitHub Actions CI **PASSED**:
- Parent PR32 exact HEAD `527b631c3a37bf1574266edb8e7b5b6e225e65ad`: `39758546890` (Windows 274 passed 90.82%, Ubuntu 273 passed/1 skipped 90.78%); Validate records `39758546916` PASS.
- Child PR33 exact source/test snapshot `b3dc25e0533f47468fc33959dba99decc3c4bfe4`: `39770548463` (Windows and Ubuntu Python3.12 PASS, Ruff, MyPy, full test suite, execution-disabled scan and build); Validate records `39770548527` PASS. Earlier `08375a43...` CI `39769961073` Windows 301 passed 88.23%, Ubuntu 300 passed/1 skipped 88.20%. Later code fixes preserved by source SHA.
- Old infrastructure failures still historical; post-runner true source defects discovered and fixed: import order and paper BE stop; renamed preflight cash risk field to `broker_stop_loss_cash_usd`. No Policy A change.

Added **two unrun, sanitized read-only Pro DEMO proof scripts** in `phase0/ops`: `v2_pr33_readonly_mt5_seven_frames_probe_20261022.py` and `v2_pr33_attended_readonly_mt5_probe_20261022.ps1`. The wrapper archives pinned source `b3dc25...` to TEMP; broker MT5 already opened DEMO, external-Python trade protection remains ON. Verifies W1/D1/H4/H1/M15/M5/M1 completed candles, exact fingerprint/server/company raw DEMO=0; output excludes raw account login. **NOT RUN on VPS**. Fingerprint algorithm mismatch is possible; fail closed, do not bypass. Actual broker observation proof remains pending.

**Status unchanged:** No real DEMO executor, order checks/submits/closures, real official event ingestion, production OpenAI calls, profitable strategy evidence, VPS changes or LIVE account approval; no 48h trial started. Both PR32 and PR33 remain DRAFT/UNMERGED, PR33 stacked on PR32.

## Final native CI after Windows parser hardening

Exact corrected source and test commit **`1848c7c7fd850bb24203d65f830453e2e3b0c975`**: production-candidate Actions `39772152774` **PASS**, Windows Python3.12 **305 passed, 88.23%**, Ubuntu **303 passed, 2 skipped, 88.20%**. Ruff/Mypy/execution-disabled capability and both builds **PASS**; Validate records `39772152748` **PASS**. Added Windows PowerShell parser test for the owner-attended read-only probe; corrected static path and Ruff S603/S607. No broker operation occurred. Prior failing runs remain historical, corrected code is passing.

**Broker proof is still missing:** the sanitized Python/PS source in `phase0/ops` is reviewed and syntactically tested but has never been run with Exness MT5. It explicitly fails on old/mismatched fingerprint, stale quote, incomplete historical window, or missing disabled-trading guard. Next owner-attended read-only step is required before a production data-admission claim.

## Owner-attended first VPS read-only attempt — failure before MT5, corrected

**Owner's first attended replay** ran the wrapper from review HEAD `9aaf178aba5133e6d5c89edb4325be0dc0a9f691`. Git fetch and ZIP archive succeeded. The `-c` Python f-string `print(f"{...}")` lost its nested quotes through Windows PowerShell 5.1 and caused `SyntaxError: invalid syntax`; wrapper failed closed at Python version determination. **No MetaTrader5 initialize/account/bars/tick read occurred, no trade action or terminal setting change.** This is a command-quoting defect, **not** evidence that Python 3.12 is missing. The exact failure was preserved in [PR33 comment 6340077026](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/33#issuecomment-6340077026).

**Correction:** exact code/test commit `3f435855eee82ab91eb44cb8ed75bb9ae71b4f72` uses quote-free `-c 'import sys;print(sys.version_info.major*100+sys.version_info.minor)'` with `312` as the only admitted version. New regression test executes the *actual* `$pyver` command under native Windows PowerShell 5.1 with Python 3.12. This covers the failure that the previous syntax-only parser test could not catch.

**CI:** [production-candidate run 39773857672](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39773857672) PASSED on Windows Python3.12 (**306 passed, 88.23%**); Ubuntu Python3.12 (**303 passed, 3 Windows-only skipped, 88.20%**). Ruff, MyPy (61 files), execution-disabled scanner, build PASS; Validate records `39773857831` PASS. Old failures and intermediate correction history preserved.

**Still pending:** corrected wrapper has NOT run on VPS, so no real 7-frame Exness Pro DEMO data is accepted yet. The separate archived Python diagnostic stays pinned to `a8945c68397ce06f527f9317c0f7560ad7f73d6b`, exact identity binding and disabled trading remain mandatory; no `order_send` or exposure modification. Owner should re-run the *new* wrapper by exact verified commit, not the old temporary script. No demo/live broker order activation follows from a read-only PASS.

## Owner-attended second read-only trial — non-specific RuntimeError and safe diagnostics

**Immutable owner-attended second trial:** exact corrected wrapper `3f435855eee82ab91eb44cb8ed75bb9ae71b4f72` passed PowerShell Python version, Git source verification and archive (`V2_SOURCE_SHA=a8945c68397ce06f527f9317c0f7560ad7f73d6b`), then Python emitted `{ "error_type":"RuntimeError", "order_api_calls":0, "status":"FAIL_CLOSED_NO_ORDER" }`. It halted without verified frame counts. This class-only output cannot establish the failing conditional or whether MT5 initialized. No broker order is indicated; account identity and complete read-only history are **NOT admitted**. Prior attempt #1 (Python f-string quotes stripped) remains a separate immutable failed trial.

**Source correction:** add strictly enumerated public `reason_code` without logging exception messages/MT5 last_error/raw login; known `RuntimeError` branches map to quote missing/stale/future and empty/forming per-timeframe; exact `MT5ReadOnlyError` guard branches map to DEMO identity mismatch, trade-API-protection missing, terminal disconnect, incomplete/bad-ordered bars; any other error maps to `UNCLASSIFIED_READONLY_FAILURE`. Also enforce admitted DEMO identity before any quote sample and timestamp snapshot after that guard. No weakening of Pro DEMO or external-Python-disabled controls.

**Exact tested source + wrapper:** `f2b26c882620b8a3ba6118a8bfad073851f336bf` is the immutable probe/code+unit-test snapshot; wrapper build commit `e1ab534c1fd99c82f86b258173fb687fa1c64533` pins it. [Production CI 39776184003](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39776184003) PASS Windows Python3.12 **320 passed (88.23%)**, Ubuntu Python3.12 **317 passed/3 skipped (88.20%)**, Ruff/MyPy/execution-disabled scan/build PASS; [Validate records 39776184125](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39776184125) PASS. No owner third read-only VPS trial has occurred and no broker dataset has been observed/accepted.

**Next owner action:** rerun the new immutable wrapper commit, not old temp copy, with Exness Pro DEMO profile connected, external-Python trading disabled, and provide only sanitized reason-code JSON. If stale tick, market session/terminal timing should be investigated; never widen thresholds simply to pass. If identity mismatch, do not disclose or bypass account identity. No demo/live order, scheduler/production change, live-account funding or 48h DEMO activation authorized.
