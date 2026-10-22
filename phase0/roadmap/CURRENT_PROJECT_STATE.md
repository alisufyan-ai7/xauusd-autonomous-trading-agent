# CURRENT PROJECT STATE — XAU/USD Autonomous Trading Agent

## FINAL CURRENT PR34 NATIVE CI + REAL READ-ONLY PARITY PROBE PREPARED (2026-10-22)

**Updated exact code/test SHA `a7114eff0649fb843095300042a0114933cd7033`** in **DRAFT stacked PR34** was tested in [GitHub Actions production-candidate run 39783484834](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39783484834): **Windows Python3.12 362 PASSED /88.56%**, **Ubuntu Python3.12 358 PASSED /4 Windows-only skipped /88.54%**, Ruff PASS, MyPy 67 source files PASS, capability scan `PASS_EXECUTION_DISABLED_CAPABILITY_SCAN`, package builds PASS. [Validate records 39783484790](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39783484790) PASS. This supersedes earlier 358/355 synthetic test counts below for revised source, without erasing old runs.

**New sanitized read-only Exness XAUUSD DEMO crossframe probe has NOT RUN on VPS**. Source `phase0/ops/v2_pr34_attended_crossframe_readonly_20261022.py`, Windows PowerShell wrapper `phase0/ops/v2_pr34_attended_crossframe_readonly_20261022.ps1` (frozen source pin `48128c83130aa767b047d382f113d4510cb3ac4d`) are committed and covered by CI syntax/no-broker-action/manual-confirmation tests. It requires exact owner-attested Exness Pro DEMO fingerprint/server/company, `trade_mode=DEMO`, external-Python trading DISABLED, reads the seven real completed bar series and reports only sanitized D1/H4/H1/M15/M5/M1 OHLC/volume parity, W1 Sunday logical anchor and gap counts. It expressly returns `official_broker_session_source_admitted:false` and `full_chronology_admitted:false` pending verified session/holiday calendar. **No actual broker OHLC crossframe parity claim has yet been earned; owner does not need to repeat the prior count-only capture.**

**Outstanding major gaps after this engineering release:** full frozen TPB objective impulse/first-touch integration and source-backed economics, new untouched V2 OOS instead of consumed/failed R3, official agency BLS/BEA/FED/Census/DOL machine feed quality and rights, real broker cost/margin/order-check binding with durable position/deal reconciliation, E1/P1 watchdog/alert drills, independently permitted demo trading 48h, and separate future Pro LIVE admission. Paper SQLite ledger never grants broker execution. PR32/33/34 remain UNMERGED/DRAFT; production main unchanged; no installed VPS changes or trading actions.


## CURRENT V2 FIVE-PRIORITY ENGINEERING — PR34 SYNTHETIC CI PASS (2026-10-22)

**User authorized continued engineering work for chronology, full TPB candidate predicates, realistic historical OOS, official-source Event Guard + bounded AI, and durable DEMO execution/position safety.** This instruction is engineering permission only, **not** broker demo/live action, MT5 Python trading enablement, VPS deployment, owner risk-policy change or paid live OpenAI transport. New **DRAFT stacked PR34** [`implementation/pro-v2-chronology-replay-event-ledger-20261022`](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/34) branched from exact parent PR33 `c452d90abf915761f0443be807e40cbe9784051d`; PR33/PR32 both remain DRAFT/UNMERGED; production main `95875ccf1bddc43491ced1dd4358057b62b7800e` untouched.

**Exact code CI PASS snapshot** `b769468d30bea4f9a9324556b2f15006cceed80e` [GitHub Actions 39782217155](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39782217155): **Windows Python3.12 358 passed /88.56%**, **Ubuntu Python3.12 355 passed, 3 skipped /88.54%**; Ruff PASS, MyPy 67 source files PASS, `PASS_EXECUTION_DISABLED_CAPABILITY_SCAN`, package build PASS. Before this, real failures from import ordering, MyPy optional SQLite transition, synthetic cost rejection assertion and Windows missing `tzdata` were corrected and remain preserved in historical CI runs. Windows-only `tzdata>=2025.2,<2028` dependency added to draft.

**1. Chronology:** New `v2_chronology_audit.py` requires independently verified broker session source SHA, revision, coverage and W1 Sunday UTC anchor; rejects open-session missing bars, invalid/future bars and missing weekly buckets, and refuses unknown/empty session calendars. New `v2_crossframe_oracle.py` compares OHLC + volume across D1/H4/H1/M15/M5/M1 fully overlapping completed bars; **does not assume W1 Sunday bucket represents a tradable market session**. Synthetic tests PASS; actual Exness session source/holiday/DST and complete real crossframe prices not admitted. Prior seven-frame owner read-only COUNT snapshot remains PASS only.

**2. TPB:** `v2_tpb_zone_tracker.py` tracks A/B first-touch, rejection/next-two-bar confirmation, max-eight-bar window, paper four-bar expiry, far-zone ATR invalidation, official event/session/cost veto and A-exposure/B prohibition. Existing causal Zone-A TPB research remains separate; **not integrated into all frozen P0-SETUPS-001 impulse/first touch/stop/target candidates, thus NOT a complete accepted strategy**.

**3. Replay:** `v2_replay_audit.py` adds protected registration/rights/holdout and Decimal gross/net cost/2x cost, max drawdown and ledger hashes; will only say `DESCRIPTIVE_ONLY` or `INSUFFICIENT_EVIDENCE`. Earlier Gate3 private Dukascopy R28/R3 historical hashes and 10,619 H4, 39,269 H1, 157,019 M15 bars exist as evidence, but R3 prior holdout is **consumed and failed**, so do not reclassify as untouched V2 OOS; no new raw registered V2 trade ledger or DSR/PBO/bootstrap/fold proof. **NO evidenced profitable trading strategy yet**.

**4. Events/AI:** `v2_official_source_gate.py` requires BLS/BEA/FED/CENSUS/DOL verified hashed rights-cleared coverage/UTC revisions, with America/New_York DST ambiguity veto, before calling frozen deterministic Event Guard. **No real official feed installed or proven healthy**, default Analyst transport still disabled, no model can override gate/risk/execution. Official agency links are source candidates only.

**5. DEMO lifecycle:** `v2_durable_paper_ledger.py` stores only synthetic broker-neutral SQLite WAL/FULL hash-chained state/revision-fenced intents, bans duplicate IDs, detects hash corruption/wrong fingerprint, quarantines unknown/stale exposure and ambiguous outcomes; **not an actual broker order adapter nor remote tamperproof journal**. Real MT5 order_calc_profit/margin/order_check/send, broker positions/deals/restart, known ticket management, alerts/watchdog and 48-hour DEMO remain NOT BUILT/NOT AUTHORIZED.

Full technical limits and next admission dependencies in [`phase0/roadmap/V2_CHRONOLOGY_TPB_OOS_EVENT_PAPER_ENGINEERING_2026-10-22.md`](V2_CHRONOLOGY_TPB_OOS_EVENT_PAPER_ENGINEERING_2026-10-22.md) and machine gate matrix [`V2_5_PRIORITY_ENGINEERING_EVIDENCE_GATE_MATRIX_2026-10-22.json`](V2_5_PRIORITY_ENGINEERING_EVIDENCE_GATE_MATRIX_2026-10-22.json). Frozen Policy A 0.25%, 0.01-lot, M1/period caps, owner Exness Pro-only/no Standard Cent and all prior Gate0 FAIL records unchanged. **No VPS changes or broker orders performed.**


## OWNER-ATTENDED V2 SEVEN-FRAME READ-ONLY SNAPSHOT PASS — 2026-10-22

**ACCEPTED owner-supplied sanitized VPS evidence (capture at `2026-10-22T12:18:18.893538+00:00`)**: the third attended diagnostic using exact CI-proven PowerShell wrapper commit `e1ab534c1fd99c82f86b258173fb687fa1c64533` and pinned Python source `f2b26c882620b8a3ba6118a8bfad073851f336bf` returned `READ_ONLY_EXTENDED_MARKET_CAPTURE_COMPLETE_NOT_TRADING_ADMISSION` followed by **`V2_EXTENDED_DEMO_READONLY_CAPTURE_PASS_NO_ORDER`**. Exness `XAUUSD`, company `Exness Technologies Ltd`, server `Exness-MT5Trial15`, admitted sanitized account fingerprint `9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91`, `trade_mode: DEMO`, Python trading disabled `true`, `execution_enabled:false`, `order_api_calls:0`, quote age **1.281s**. Account subtype **Pro** is based on owner dedication/admission attestation; the capture does not prove subtype separately. Never store raw account IDs/credentials.

**All seven requested completed-bar counts returned:** W1 **104/104**, D1 **180/180**, H4 **300/300**, H1 **500/500**, M15 **1000/1000**, M5 **300/300**, M1 **300/300**. The archived machine-readable proof with exact oldest/latest UTC per timeframe, wrapper/source SHAs and capability limitations is [`phase0/evidence/V2_XAUUSD_DEMO_SEVEN_FRAME_READONLY_PASS_2026-10-22.json`](../evidence/V2_XAUUSD_DEMO_SEVEN_FRAME_READONLY_PASS_2026-10-22.json). This admits **single-snapshot 7-frame read-only acquisition**, not full time-series causal correctness or trading readiness.

**Boundaries/next gates:** captured broker W1 bar-derived `latest_closed_utc=2026-10-18T00:00:00+00:00` and oldest W1 open `2024-10-20T00:00:00+00:00` (Sunday). Before strategy usage, reconcile broker-specific W1 weekly opens/last-close conventions and real Exness session/holiday gaps (the program derives `close_time` from `open_time+7d`); validate cross-timeframe UTC consistency, opening hours, DST, and missing-bar handling. Require independently healthy official Event Guard, full frozen objective TPB predicates/chronological cost-aware OOS, durable source-checked Policy A/position/execution governor, authenticated alerts/watchdog, and exact separately owner-approved DEMO activation. No native quote snapshot proves profitability or 48h running monitor.

**Historical statuses immutably preserved:** attended attempts 1 and 2 failed closed (PowerShell quoting then unclassified Python RuntimeError); attempt 3 is a new successful snapshot, not a relabelling. PR32 and PR33 remain DRAFT/UNMERGED, PCR3 installed/MT5 trading API disabled, no broker order/toggle, no VPS deployment, no 48-hour DEMO started and NO LIVE approval. Frozen Policy A (0.25%, 0.01 lot, M1, period limits) and all earlier Gate0 failures unchanged.


## THIRD-PROBE DIAGNOSTIC READY — SANITIZED REASON CODES (2026-10-22)

**READ-ONLY OWNER ATTEMPT #2 remains immutable FAIL_CLOSED:** owner executed corrected wrapper SHA `3f435855eee82ab91eb44cb8ed75bb9ae71b4f72`, archived source `a8945c68397ce06f527f9317c0f7560ad7f73d6b`, and received `RuntimeError`, `FAIL_CLOSED_NO_ORDER`, `order_api_calls:0` **without** a reason_code. No verified DEMO fingerprint, tick history or seven-frame bar evidence; whether MT5 initialized is unknown. [PR33 evidence](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/33#issuecomment-6340238980). Historical earlier pre-MT5 PowerShell quoting failure remains separate and unchanged.

**Corrected observation-only diagnostic:** source + tested synthetic reason classifier snapshot `f2b26c882620b8a3ba6118a8bfad073851f336bf`, referenced via immutable `PinnedCode` in the [PowerShell wrapper](../ops/v2_pr33_attended_readonly_mt5_probe_20261022.ps1) from exact wrapper implementation commit `e1ab534c1fd99c82f86b258173fb687fa1c64533`. The probe now checks precise admitted Exness Pro DEMO fingerprint/server/company/USD/raw DEMO account mode and disabled external-Python trading **before** sampling quote; derives `as_of` after guard. Then reports allow-listed reason codes for quote stale/future/unavailable, blank/forming bars, invalid account/terminal state, with generic `UNCLASSIFIED_*` otherwise. Full raw MT5 errors/credentials/tickets never echoed. **Existing quote freshness (5 sec), account and volume/risk locks not loosened.**

**Native exact GitHub checks at wrapper commit `e1ab534c1fd99c82f86b258173fb687fa1c64533`:** [production-candidate run 39776184003](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39776184003) PASS on **Windows Python3.12: 320 passed / 88.23% coverage** and **Ubuntu Python3.12: 317 passed, 3 skipped / 88.20% coverage**. Ruff PASS, MyPy PASS (61 files), `PASS_EXECUTION_DISABLED_CAPABILITY_SCAN`, source/wheel builds PASS; [Validate records run 39776184125](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39776184125) PASS. CI validates only synthetic source and safety; **third owner-run broker capture has not yet been performed**.

**NEXT:** run new exact wrapper commit `e1ab534...` from GitHub on owner VPS, keep dedicated Exness Pro DEMO and external-Python API trading DISABLED; supply **sanitized** diagnostic JSON. If code is `QUOTE_TIMESTAMP_STALE`, investigate market/session/tick freshness, never change tolerance just to pass. If `DEMO_IDENTITY_MISMATCH`, stop and reconcile profile/fingerprint privately, no credential/ID exposure. If broker history incomplete or forming, do not infer data admission. Do not deploy, merge draft PR32/PR33, place demo/live order, toggle MT5 trading or start 48-hour DEMO on the strength of this read-only diagnostic.


## LATEST ATTENDED DEMO READ-ONLY REPLAY #2 — RUNTIME REJECTION (2026-10-22)

**User output, observed:** corrected owner-attended PowerShell wrapper SHA `3f435855eee82ab91eb44cb8ed75bb9ae71b4f72` successfully passed Git fetch, quote-free Python3.12 version check and immutable source archive (`V2_SOURCE_SHA=a8945c68397ce06f527f9317c0f7560ad7f73d6b`). It reached Python diagnostic but emitted `{"error_type":"RuntimeError","order_api_calls":0,"status":"FAIL_CLOSED_NO_ORDER"}` and halted as `V2_EXTENDED_DEMO_READONLY_CAPTURE_FAIL_CLOSED`. **NO pass/no seven-frame counts; no verified real MT5 identity, ticks, history or dataset.** The existing program suppresses exception message: concrete cause is UNRESOLVED, plausibly within one of quote unavailable, stale/future quote, empty frame or forming frame branches, but none independently established. No evidence supports saying MT5 never initialized on this attempt. [Immutable owner evidence in PR33](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/33#issuecomment-6340238980).

**Remediation in isolated draft branch (NOT VPS run yet):** Python read-only probe uses exact safe whitelist `_public_failure_reason()` mapping `RuntimeError` to sanitized fixed reason codes (e.g. `QUOTE_UNAVAILABLE`, `QUOTE_TIMESTAMP_STALE/FUTURE`, `<TF>_EMPTY_BROKER_HISTORY`, `<TF>_FORMING_BAR`, else `UNCLASSIFIED_RUNTIME_ERROR`). Other exception classes map to `UNCLASSIFIED_READONLY_FAILURE`; full exception text/raw account/MT5 errors never printed. Probe checks exact admitted Pro DEMO identity & Python-trading-disabled guard **BEFORE requesting quote**, then freshly snapshots UTC; no loosening of 5-second tick policy, history requirements or exact DEMO identity. Wrapper is pinned to source+test `783cce55a09706cc59017202336da77d69ed8ec4` and the currently reviewed correction lives in PR33. The resulting GitHub Actions test verdict must be consulted before new owner VPS run; **no real broker observation from this fix yet**.

**Safety:** owner statement and source output provide zero order API calls; unchanged VPS scheduling/installed PCR3 and prior S2 state; no demo/live trading authorization, no account profile switching, no MT5 trading toggle. Keep historical prior PowerShell quoting failure and this new RuntimeError failure separate and immutable. Next action: exact-source native CI of diagnostic reason whitelist + owner-attended rerun with sanitized output; then evaluate specific blocker without bypassing control.


## LATEST OWNER ATTENDED READ-ONLY REPLAY — VERSION ARG QUOTING FIXED (2026-10-22)

**Owner-executed VPS read-only trial failed closed BEFORE MT5:** owner ran exact previous PR33 HEAD `9aaf178aba5133e6d5c89edb4325be0dc0a9f691` script. Git fetch and isolated ZIP archive succeeded, but PowerShell 5.1 mangled embedded Python `-c` f-string `print(f"{...}")` into `print(f{...})`, yielding Python `SyntaxError` and throwing `Exact Python 3.12 required`. **This does not mean Python3.12 is unavailable; no MT5 initialization or broker read occurred.** No order, account switch, settings change, scheduled-task change or other broker operation occurred. Preserve the failed read-only attempt as immutable evidence: [PR33 issuecomment-6340077026](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/33#issuecomment-6340077026).

**Corrigendum, exact source+test commit `3f435855eee82ab91eb44cb8ed75bb9ae71b4f72`:** the diagnostic wrapper now checks Python 3.12 via quote-free `-c 'import sys;print(sys.version_info.major*100+sys.version_info.minor)'` with observed string `312`. Added **native Windows execution regression test** to run that extracted *exact* `$pyver` line in PowerShell 5.1, beyond the earlier syntax-only test. [GitHub Actions production-candidate run 39773857672](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39773857672) **PASS** Windows Python3.12 **306 tests passed, 88.23% coverage**; Ubuntu Python3.12 **303 passed, 3 Windows-specific skipped, 88.20% coverage**. Ruff, MyPy (61 source files), disabled capability scan and packaging all passed; [Validate records 39773857831](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39773857831) **PASS**. Earlier malformed intermediate development version was superseded before any owner retry. Existing failed runs are not relabelled.

**NOT YET COMPLETE:** actual Exness Pro DEMO W1/D1/M5/M1 read-only observation has STILL NOT HAPPENED. New wrapper's frozen Python market probe remains pinned to `a8945c68397ce06f527f9317c0f7560ad7f73d6b`, requiring exact owner-attested DEMO fingerprint/server/company, Python trading disabled and full requested bars. Next owner action: execute **corrected, tested wrapper at exact code commit `3f435855...`**, not previously saved TEMP script; share sanitized output to adjudicate account identity and history. No demo/live trading authorization, broker order, Python trade toggle, 48h DEMO activation or policy change follows from this correction. PR32 and PR33 remain DRAFT/UNMERGED and production main unchanged.


## NEW FINAL PR33 WINDOWS/UBUNTU CI PASS + VPS PROBE STILL NOT RUN (2026-10-22)

**Exact newly verified complete code/test commit `1848c7c7fd850bb24203d65f830453e2e3b0c975`:** [GitHub Actions production-candidate run 39772152774](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39772152774) **PASS**: Windows Python3.12 **305 tests PASS**, coverage **88.23%**; Ubuntu Python3.12 **303 tests PASS, 2 Windows-specific skipped**, coverage **88.20%**. Exact tests include static PowerShell 5.1 syntax parsing of attended read-only diagnostic, which PASSED on native Windows; source probe safety/shortfall tests also PASS. **Ruff PASS, MyPy PASS (61 source files), execution-disabled-capability scan PASS and package builds PASS on both OS.** [Validate records 39772152748](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39772152748) PASS. Earlier I001/S603/S607 and BE paper lifecycle failures preserved as historical attempts; latest run supersedes those failures **only for this corrected source**.

**Read-only Pro DEMO diagnostic, PREPARED / NOT EXECUTED on VPS:** `phase0/ops/v2_pr33_attended_readonly_mt5_probe_20261022.ps1` wraps `v2_pr33_readonly_mt5_seven_frames_probe_20261022.py`, freezing source **`a8945c68397ce06f527f9317c0f7560ad7f73d6b`**. Verifies admitted fingerprint/company/server/raw DEMO mode, disabled Python trading, seven completed frames, fresh quote and full requested history. Does not print raw account login, enable trading or place orders. **This diagnostic is verified only in synthetic tests and Windows parser, not against Exness/VPS.**

**Remaining active blocker:** native CI is resolved; the new active evidence gate is owner-attended read-only Exness Pro MT5 W1/D1/M5/M1 source proof and then full registered TPB/independently healthy official Event Guard + durable real risk/execution/position watchdog (not yet implemented). **No broker orders, LIVE permission, MT5 Python trading enable, VPS task deployment or 48h DEMO trial.** PR32 and stacked PR33 remain DRAFT/UNMERGED; production main unchanged at `95875ccf1bddc43491ced1dd4358057b62b7800e`.


## LATEST CODE-VERIFIED CI — PR33 + ATTENDED READ-ONLY PROOF PENDING (2026-10-22)

**Owner said GitHub Actions billing was resolved. This is now supported by new native job execution.** [PR32](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/32) `527b631c3a37bf1574266edb8e7b5b6e225e65ad` passed exact-source **Windows/Ubuntu Python3.12** CI in rerun `39758546890` plus Validate records `39758546916`, original fails preserved. Parent stays DRAFT/UNMERGED.

**PR33 source + selected diagnostic tests confirmed native CI PASS at exact code/tests commit `549db58a48de73a91e458e97f25df3311b47ac7c`:** [production-candidate run 39771566444](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39771566444), **Windows Python3.12: 304 passed, 88.23% coverage; Ubuntu Python3.12: 303 passed, one Windows-specific skipped, 88.20% coverage**. Ruff PASS, MyPy PASS for **61 files**, execution-disabled capability scan PASS, package builds PASS. [Validate records run 39771566382](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39771566382) PASS. This includes new synthetic tests for the seven-timeframe VPS probe consent, AST prohibited actions and history-shortfall refusal. Prior source/test failures (import ordering and rejecting legitimate BE stop tighten) are independently fixed. **Neither GitHub synthetic coverage nor paper lifecycle tests qualify real broker execution.**

**Next physical evidence:** new [owner-attended PowerShell wrapper](../ops/v2_pr33_attended_readonly_mt5_probe_20261022.ps1) and [read-only Python XAUUSD source probe](../ops/v2_pr33_readonly_mt5_seven_frames_probe_20261022.py) are PREPARED and NOT RUN on VPS. Wrapper freezes broker-readonly diagnostic source **`a8945c68397ce06f527f9317c0f7560ad7f73d6b`** in TEMP, requiring installed Python3.12, existing Pro DEMO-only MT5, external Python trading **disabled**, previously owner-confirmed fingerprint/server/company and DEMO trade_mode 0. It samples completed W1/D1/H4/H1/M15/M5/M1 and fails closed if tick stale, future, wrong-account, or history too short. It prints only sanitized UTC timestamps/counts and hash, NOT raw login. Possible legacy/new fingerprint-hash algorithm difference must fail closed, never be 'fixed' by removing identity binding. Owner must attend and provide sanitized output; **no broker call has occurred in this ChatGPT session**.

**Current next step:** verify actual Pro DEMO 7-frame history with the prepared read-only script; complete frozen TPB predicates and independent chrono-OOS/cost evidence; then independently implement broker-bound persistent DEMO transaction engine, margin/governor/position reconciliation and alert/watchdog testing. PR33 remains STACKED on draft PR32, both UNMERGED. No order calls, MT5 Python toggle, scheduler changes, OpenAI production API use, 48h DEMO activation or LIVE trade authorized; current Policy A 0.25%/0.01 lot/M1 and Gate0 failure history unchanged.


## MOST RECENT 2026-10-22 — GITHUB ACTIONS CI RECOVERED / DEMO INGESTION NEXT

**Owner confirmed GitHub Actions billing issue resolved; actual native runs now prove the execution-disabled V2 software tests.** Accepted V2 spec main **`95875ccf1bddc43491ced1dd4358057b62b7800e`** unchanged. Both implementation lines are still DRAFT/UNMERGED and must not be deployed without owner review.

- **PR32 parent exact source HEAD `527b631c3a37bf1574266edb8e7b5b6e225e65ad`:** original pre-runner failures preserved, corrected GitHub run `39758546890` Windows Python3.12 **274 PASSED /90.82% coverage**, Ubuntu **273 PASSED /1 skipped/90.78% coverage**, Ruff/MyPy/disabled-capability/build PASS; Validate records run `39758546916` PASS. [Preserved parent evidence](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/32#issuecomment-6339634242).
- **PR33 child independently verified exact source/test commit `b3dc25e0533f47468fc33959dba99decc3c4bfe4`:** production-candidate run `39770548463` **PASS both Windows and Ubuntu Python3.12**, with Ruff, MyPy (61 source files), full tests, 85% coverage gate, capability scan and package build; Validate records `39770548527` **PASS**. An earlier corrected commit `08375a43a22f88ea655fdbd3f0d0a4172eb06181` [run `39769961073`](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39769961073) proved Windows **301 PASSED /88.23%** and Ubuntu **300 PASSED /1 skipped/88.20%**. Subsequent code changed the monetary field name to precise `broker_stop_loss_cash_usd` and is separately included in the final exact CI-PASS code commit `b3dc25...`. [Preserved child evidence](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/33#issuecomment-6339635429).
- **Root causes now observed:** original GitHub jobs had billing-related failure as reported by owner, later actual Ruff import I001 and paper initial-SL validation rejected valid stop tightening to break even; repaired and tested. No original failed evidence erased. **Passing CI verifies synthetic/offline source only, not real broker or profit.**
- **New prospective read-only Pro DEMO market-data verification, NOT EXECUTED:** `phase0/ops/v2_pr33_readonly_mt5_seven_frames_probe_20261022.py` plus `phase0/ops/v2_pr33_attended_readonly_mt5_probe_20261022.ps1`. Wrapper archives immutable source `b3dc25...` in TEMP, requires existing Python3.12 and disabled external-Python trading, checks previously attested sanitized DEMO fingerprint/company/server/raw DEMO trade_mode=0, reads authentic completed W1/D1/H4/H1/M15/M5/M1 with sanitized times/counts only. It may **FAIL CLOSED on source-fingerprint schema mismatch**; no raw login should be emitted or inferred. It is not a scheduler nor an automatic broker action and has **NOT been run on VPS**. A separately attended read-only owner-run capture is the next evidence gate.
- **Scope limits unchanged:** TPB Zone-A partial unqualified research logic, missing official real Event Guard source integration, default-disabled analyst, pure cash Policy A preflight and paper position lifecycle; **NO full autonomous demo executor**, no actual 48h DEMO trading, no MT5 Python trading toggle, no real demo/live order or VPS deployment. Fixed 0.25%, 0.01 lot, M1, E1/P1 and original Gate0 failures preserved; Exness Pro-only, never Standard Cent. PR33 remains STACKED on unmerged PR32.


## LATEST ENGINEERING — FIVE PRIORITIES (2026-10-22)

**Owner authorized progression through five engineering priorities, strictly execution-disabled without broker activation.** New dated [ADR-2026-10-22-002](../decisions/ADR-2026-10-22-002-V2-ENGINEERING-PRIORITIES.md) and [technical progress/evidence](AUTONOMOUS_PRO_V2_PRIORITIES_2_TO_5_IMPLEMENTATION_2026-10-22.md) are in a new **STACKED draft child branch** `implementation/pro-v2-readonly-data-and-tpb-shadow-20261022` founded at parent PR32 HEAD `527b631c3a37bf1574266edb8e7b5b6e225e65ad` (parent still OPEN/DRAFT, not merged). Current production main remains **`95875ccf1bddc43491ced1dd4358057b62b7800e`**.

1. **Python3.12 CI not resolved.** PR32 workflow runs `39758170391` and `39758170378` failed within seconds before exposing runner steps/logs; root cause undetermined. Assistant's local environment only Python3.13; downloading 3.12 blocked by DNS/network. Neither PR32's 13 tests nor child tests may be marked as PASS. Need GitHub Actions UI/quota/runner diagnostic or isolated exact-head Python3.12 native Windows test, and later full exact release CI.
2. **W1/D1/M5/M1 ingestion source prepared, not broker validated.** `src/xauusd_agent/broker/v2_mt5_context_readonly.py` inherits existing read-only MT5 guard, fetches all seven actual closed frames and rechecks exact DEMO profile fingerprint/company/server/currency/raw DEMO trade_mode=0, plus disabled Python trading guard. Five synthetic tests authored. It is NOT connected to VPS/PCR3/real MT5 and has not observed any real additional candles. Symbol must be XAUUSD and account Exness Pro only.
3. **Objective TPB research detection prepared but unqualified.** `src/xauusd_agent/features/v2_tpb_research.py` builds H4/H1/M15 technical Zone-A-only TPB subset with indicators/swings/M15 confirmation from completed bars, returns `NO_TRADE` or `TECHNICAL_HYPOTHESIS` with `execution_permitted=False`. Full frozen P0-SETUPS-001 Zone B/location, cancellation, event/spread/cost and registered chronological replay remain missing; strategy profitability unproven.
4. **Strict Analyst/Event Guard bridge prepared but OFFLINE.** `src/xauusd_agent/features/v2_shadow_analyst_event.py` invokes existing Event Guard on externally attested official-source observation and existing strict AnalystClient; default transport DISABLED (no OpenAI request). Rejects source, epoch, shock, policy and analyst errors; any synthetic SETUP is `RESEARCH_SETUP` not a broker order. Nine synthetic tests authored.
5. **DEMO lifecycle only paper/synthetic, not order capable.** `src/xauusd_agent/ops/v2_demo_paper_lifecycle.py` implements pure state machine for synthetic 0.01-lot position, known-only exit, stop-tightening, duplicate writer refusal and unknown ACK quarantine. Seven synthetic tests authored; actual broker execution, `order_check`, full Policy A cash-math, SQLite intent/reconciliation, watchdog and 48h DEMO are **NOT STARTED**.

**Read-first safety truth:** 26 new tests are AUTHORED (5 read-only broker + 9 Event/TPB + 7 paper lifecycle + 5 frozen Policy A cash), **0 verified passed under exact Python3.12 Windows**. New `src/xauusd_agent/risk/v2_cash_preflight.py` checks 0.25% eligible risk and current M1, period cash caps and min-lot but depends entirely on independently sourced broker inputs; it has no broker connection or order permission. PR33 GitHub Actions `39761671235` and `39761671259` still FAILED before usable test proof; root cause undetermined. No MT5 settings changed, no VPS source/tasks updated, no demo/live account call, no trade order, no OpenAI production call and no real 48h observation. PR24/S2, PR26, PR29 and parent PR32 remain separate draft lines. Existing Gate0 R4/R34/R35 FAIL records immutable; fixed 0.25% Policy A, 0.01 lot cap, M1 and human E1/P1 remain. Owner Pro-only/no Standard Cent policy remains.

**Native Windows fallback prepared but NOT run:** [isolated PR33 Python3.12 test script](../ops/v2_pr33_isolated_py312_source_tests_20261022.ps1) verifies pinned code commit `4bfb431daf078c84d4189a4c033a2d607ae53004`, archives to TEMP, invokes existing Python3.12 and selected synthetic pytest suite + execution-disabled capability scan. No package install, VPS scheduler change, MT5 broker call or terminal trading toggle. Native result remains **UNVERIFIED** until owner-host stdout arrives. **Next gating action:** establish genuine native Python3.12 exact-head test evidence (diagnose GitHub Actions immediate no-steps failures) and review new standalone source/port against existing frozen specs. Then run separately approved read-only Exness Pro DEMO source capture to verify W1/D1/M5/M1; complete exact TPB oracle/replay and official Event Guard source. A new byte-exact broker Risk Governor+order/reconciliation release and separately bounded owner DEMO APC are still required. No LIVE release authority.


## CURRENT CI FINDING — PR32 EXACT HEAD (2026-10-22)

New safe execution-disabled implementation [draft PR32](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/32) at HEAD `358f0181966ed9891fc14e19d6724cb872187557` (from merged specification main `95875ccf1bddc43491ced1dd4358057b62b7800e`). Exactly **six** paths differ: 2 pure code, 1 thirteen-test synthetic unit suite, 1 detail handoff, 2 state files. Source static inspection: no MetaTrader5 import or order submission/position-management methods in new modules. No live market data port or AI production transport has been connected; 48h DEMO clock NOT started.

GitHub Actions exact-head `production-candidate` run **39758170391**, Windows job `119755375230`, Ubuntu job `119755375652`, and `Validate records` run **39758170378**, job `119755375608`, all reported **FAILURE with `steps: null`**. Ubuntu logs returned 404 `BlobNotFound`. Therefore **13 tests are authored but 0 exact-head tests verified PASS**; root cause undetermined, not assumed Python code failure nor assumed account/runner quota issue. [PR32 CI evidence](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/32#issuecomment-6337815142). Do not merge, deploy or claim production-ready. Next is CI account/runner diagnostic OR native Windows Python3.12 exact-source tests, followed by read-only additional timeframe connector and real setup predicates.

## CURRENT VERIFIED WORK — V2 SPEC APPROVED/MERGED; SLICE01 EXECUTION-DISABLED (2026-10-22)

Owner approved draft v2 specification as design and authorized proceeding with the first **execution-disabled engineering slice** (not DEMO/LIVE orders or risk changes). PR31 was merged at **`main=95875ccf1bddc43491ced1dd4358057b62b7800e`** after exact-five-doc scope check, preserving owner Pro-only and AI/multi-timeframe requirements. The accepted `phase0/roadmap/AUTONOMOUS_XAUUSD_PRO_V2_ARCHITECTURE_AND_ACCEPTANCE_2026-10-22.md` is an architectural baseline, **not** a filled-in profit proof, runtime admission, strategy approval, new Policy A rate or broker authorization.

**NEW isolated implementation branch:** `implementation/autonomous-pro-v2-execution-disabled-context-20261022`, born from exact main above. Files: `src/xauusd_agent/features/v2_market_context.py` (W1/D1/H4/H1/M15/M5/M1 completed-bar, healthy-source and fresh-quote validation), `src/xauusd_agent/features/v2_shadow_selector.py` (single unambiguous independently admitted champion **SHADOW** only), `tests/unit/features/test_v2_shadow_context.py` (**13 tests authored but native CI has NOT been proved PASS**), and [slice01 explanation](AUTONOMOUS_XAUUSD_PRO_V2_EXECUTION_DISABLED_SLICE01_2026-10-22.md). Source static scan found **no order_send, MetaTrader5 import or external Python trading enable path**; runtime and VPS unchanged. Context deliberately fails NO_TRADE until W1/D1/M5/M1 real read-only broker bars, official session/Event Guard/shock gate, strategy evidence and complete stable quotes are sourced. No strategy predicates are faked; `research_admitted` defaults false. Selection output `execution_permitted=False` even if shadow setup exists.

**Historical snapshot only:** existing owner Exness Pro DEMO staged S2 hash/deep KILLED+UNUSED preflight PASS remains historical; previous PCR3 installed `XAUUSD Execution-Disabled Shadow` stays untouched. Draft PR24/26/29 and all historic Gate0/CI failures untouched and unmerged. Fixed numeric Policy A 0.25%, 0.01 lot, M1/free-margin/current+stress and period stops remain accepted; proposal to adapt to small Pro capital is NOT granted. No MT5 Python toggle, OpenAI production calls, broker read/write, autonomous DEMO activation or LIVE funding/order/activation authorized.

**NEXT work after review:** verify exact-head native Python3.12/Windows tests/CI (GitHub Actions PR29 had immediate failures of undetermined cause), then build *new* read-only W1/D1/M5/M1 bar adapter and independently source-backed Event Guard/strategy predicate pipeline behind a null execution sink. Always update both human-readable and JSON state and the ADR log when substantive decisions change. The earlier below 'PR31 draft pending' text is historical and superseded by this section.


## NEXT PROPOSED PRODUCT SPEC — Autonomous XAUUSD Pro v2 (2026-10-22)

**PR30 MERGED + V2 SPEC DRAFT:** Owner approved docs-only PR30 and GitHub confirmed merge to authoritative `main=51a7f7de395767a9ae1f9904f752bd74b3cdc010` (October21 UTC / October22 Pakistan time); original owner Pro-only and autonomous trading vision now permanently on main. This read-first note belongs to a **separate unmerged v2 specification proposal branch**, not an execution, strategy, trading or risk-policy grant.

Three initial V2 design artifacts, all **PROPOSED/UNAPPROVED**:
- [V2 architecture and admission specification](AUTONOMOUS_XAUUSD_PRO_V2_ARCHITECTURE_AND_ACCEPTANCE_2026-10-22.md): Exness Pro only, W1/D1/H4/H1/M15/M5/M1 causal structure, strategy champion/shadow challengers, AI bounded non-authoritative research/analysis, broker-bound full Policy A risk, known-position early exit/BE/trailing successor research, 48h DEMO operational requirements, independent later Pro LIVE admission.
- [V2 owner decision packet](AUTONOMOUS_XAUUSD_PRO_V2_OWNER_DECISION_PACKET_2026-10-22.md): proposed strategy/position-exit priorities and **illustrative**, not approved, account-aware risk options ($300/$500/$1000/$10000), exact separation between owner's confirmed design vision and missing permission.
- [V2 proposed acceptance matrix](AUTONOMOUS_XAUUSD_PRO_V2_ACCEPTANCE_MATRIX_2026-10-22.json): 32 `PENDING/NOT_RUN` adversarial/data/strategy/AI/risk/position/recovery/trial/LIVE isolation cases. Nothing accepted or implemented by merely writing the matrix.

**Safeguards/authorities unchanged:** frozen current Policy A `0.25%` planned per trade with 0.01 max, period loss/drawdown, M1 limits; no accepted change for small account, no Standard Cent; no automatic stop-widening, position doubling, LIVE conversion or continuous live prompt self-retraining. Existing PCR3 shadow task remains execution-disabled; PR24/S2 remains attended one-lifecycle and PR29 remains a draft speculative advisory with unknown-cause failed CI. All Gate0 historical failures preserved. No additional DEMO order, MT5 external Python trading enable, LIVE order, OpenAI production call, VPS task, source merger or deployment is authorized.

**NEXT owner action:** review V2 *specification* and proposed choices. Once scoped and explicitly approved for implementation, work proceeds as separate, isolated code/test PRs with independent frozen release acceptance; only a later exact-bound owner permit may activate DEMO. PR31 remains **DRAFT** until approved. We must not infer product-ready or profitable system from documenting architecture.


## Prospective owner product requirements, 2026-10-21 — DOCS PR ONLY

**New dated ADR, not yet merged to authoritative main:** [ADR-2026-10-21-001 — Autonomous Pro Trading Vision](../decisions/ADR-2026-10-21-001-AUTONOMOUS-PRO-TRADING-VISION.md); [Decision Memory Protocol](PROJECT_DECISION_MEMORY_PROTOCOL_2026-10-21.md). This adds the owner's requirement to **use Exness Pro exclusively (never Standard Cent)**, automatically analyze weekly/D1/H4/H1/M15/M5/M1 gold and choose trade directions, monitor and manage **known** positions, and continuously investigate/learn with safe strategy/prompt versioning. The owner favors a **48h automated DEMO operations milestone**, with potential **>USD300 initial LIVE balance** only as a tentative funding idea, not funding or trading permission. Owner desires flexible risk policy and a later Pro LIVE trial; **numeric risk limits and LIVE gating are not changed**. Stop widening from human psychology was an example, **not an approved capability**.

**Why no broker action:** project-approved Policy A (including 0.25% of eligible capital, daily/weekly/drawdown and M1), Exness demo account fingerprint, unknown-exposure quarantine, human E1/P1, Gate0/replay/operational failures and trading-authority flags remain unchanged. Draft PR29 (experimental automatic advisory HEAD `d90d464528c7e32d28710178f8b3573fc1a10be7`) is NOT CI accepted; PCR3 remains execution-disabled. S2 only proves the previously observed one-lifecycle read-only stage, not autonomous execution. No current DEMO order, external Python trading enable, funded LIVE account, real-money order or 48h broker-run proof exists.

**NEXT OWNER REVIEW:** authorize only a new versioned **autonomous Pro architecture & acceptance specification**: market-timeframe/context model, one champion strategy plus shadow challengers, AI analyst/learning promotion, early-close/BE/trailing rules tested without stop widening, full broker-bound risk governor and small-account risk-budget alternatives, events/news, position reconciliation/watchdog, explicit 48h DEMO entry/monitoring gates and separate later Pro LIVE admission. Code/deployment/risk-policy changes remain separate.

**Recover cross-chat context:** `GOVERNANCE.md` and `phase0/DECISION_LOG.md` → latest `phase0/decisions/ADR-*` → `CURRENT_PROJECT_STATE.md` and paired JSON → open PRs/evidence branch. No code, VPS or trade scope is authorized by this read-first note.


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
