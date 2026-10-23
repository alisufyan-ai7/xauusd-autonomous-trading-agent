# CURRENT PROJECT STATE — XAU/USD Autonomous Trading Agent

> **CURRENT AGENT HANDOFF:** [AGENT_START_HERE.md](../../AGENT_START_HERE.md). This file contains preserved dated history; its early 2026-10-23 snapshot predates the 26-PR retirement and the owner DEMO-only governance amendment. Read that root index and query live [PR #40](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/40) before acting. No real broker order has been observed or deployed by this record. The latest objective is a continuous Exness Pro DEMO broker trader, not another mandatory four-hour study. Do not treat prior technical NO_GO as final product scope.


## Owner override recorded 2026-10-23 — DEMO NOW, NOT A FOUR-HOUR PHASE; DYNAMIC KNOWN-POSITION MANAGEMENT

Read [ADR-2026-10-23-003](../decisions/ADR-2026-10-23-003-OWNER_DEMO_FASTTRACK_CONTINUOUS_MANAGEMENT_AND_RISK_REVISION.md). **The owner explicitly rejects a separate mandatory four-hour read-only wait before the future real Exness Pro DEMO pilot**, requests actual autonomous MT5 DEMO broker orders and continuous monitoring immediately once executable, and reaffirms human-inspired position management (early exit, tighten/trail SL, break-even, bounded TP changes). The historic v1.1 four-hour acceptance design remains immutable as an *older* protocol, **not a prerequisite for the revised future pilot**. Data collection should continue while a functioning approved demo agent operates; missing stop/fee/gap/slippage cannot be set to zero merely to permit entry.

The owner also explicitly rejects treating **0.25% as an immutable future risk fraction**; do not conflate percentage planned cash loss and SL price distance. Earlier ADR V-10 documented review of capital-aware variable risk. **No replacement numerical cash-risk percentage or algorithm was provided**, so a versioned risk limit must be concretely specified, tested, and checked before enabling actual order sending. The legacy `RISK_RATE=0.0025` is still code, not erased by an ADR. Protect one 0.01-lot cap, fixed DEMO identity, broker-side protective stop, no widening/averaging, E1/P1 quarantine, existing S2 only; LIVE remains prohibited.

**Actual blocking code must not be hidden:** `demo_adapter/src/xauusd_demo/mt5_demo.py` unconditionally denies before `order_check/order_send` with `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED`; `s2_readonly_coordinator_port.py` intentionally emits no live proposals and always refuses to send. No VPS remote-access connector exists here: GitHub PR commits and Actions tests **do not deploy on Windows or execute real Exness MT5 orders**. The owner's standing DEMO intent already covers launch when the code becomes genuinely executable: avoid repeated permission questions and read-only-only diagnostic loops. Engineering priority is *complete one bound S2 order path + a locally executable, source-pinned Windows VPS release*, not another capture ceremony. **DO NOT falsely label the product as deployed.**


## 2026-10-23 13:37Z — NEW LATEST VERIFIED STATIC READ-ONLY BROKER **PASS**

Read [MT5_STATIC_READONLY_VERIFIED_PASS_2026-10-23.md](MT5_STATIC_READONLY_VERIFIED_PASS_2026-10-23.md). Owner attended source-pinned launcher `a54bf80a39faf8a44bdeeed078a912d280b811d8` / Python pin `462ac5e94fbeb656f3415603f12e81fdc3c3bd58`. Real Exness Pro DEMO static collector returned `STATIC_COMPLETE_PROSPECTIVE_NOT_COLLECTED` and exact sanitized report SHA256 `794A326E64B9703CF7066471F708C3E830582E9E2B7A616E6E03440AC7B01A2B`. The correct account and zero positions/orders verified, 0.01-lot six BUY/SELL cash loss and margin calculations passed (USD 2/5/10 loss, USD 2.01 incremental margin, USD 4.02 conservative 2×); seven frames PASS; historical ticks PASS; XAUUSD fee rows **0 observed, NOT a zero-fee proof**. `order_send=0`, `order_check=0`. Four-hour prospective slots/proxy **NULL**, official source and full Policy A **NOT ADMITTED**. Raw broker records private on VPS. Historical earlier failed attempts remain immutable.

The owner-independent PR40 branch now **prepares but does not execute** original comprehensive 4h script `phase0/ops/pr40_one_comprehensive_mt5_readonly_4h_20261023.ps1`, repinned to successful exact collector `462ac5e94fbeb656f3415603f12e81fdc3c3bd58` with matching native PowerShell test. One subsequent 4h observational run requires **separate explicit owner assent and latest exact HEAD CI PASS**; it is not an order or production release. S2 hard execution stop, Gate0 failure history, governance Rule7, DEMO order NO_GO and LIVE NO_GO unchanged.


## 2026-10-23 13:20Z — LATEST OWNER-ATTENDED STATIC-ONLY RESULT: HISTORICAL TICKS REJECTED (NO ORDERS)

**Authoritative most recent VPS observation**: approved static-only launcher reviewed at `b42005212f8f4869b815af2fad3a523c2eaed55b`, pinned collector `723e276ca32f80e6b705c8dd087a4325609c59e5`. The isolated import preflight **PASS**; actual collector `FAIL_CLOSED_NO_ORDER`, `failure_stage=STATIC_HISTORICAL_BROKER_TICKS`, `safe_guard_code=HISTORICAL_TICK_ORDER_OR_PRICE_INVALID`, `order_check_calls=0`, `order_send_calls=0`. Private `failure.json` SHA-256 `84620F5EF9B6FBF7BEDFDBB35FB1CB59110008FCE8128E2F07598186339C0646`. Private static path `%LOCALAPPDATA%\\XAUUSD-BrokerEvidence\\static-diagnostic-20261023T132013Z-7a702da8c903494180c1ea4fbd1881c0`. No 4h registration, no static completed summary. The previous 12:27Z original 4h collector failure remains immutable and its precise guard unrecoverable; a later reproduction does not retrospectively prove the earlier reason.

**Source-stage finding:** current short diagnostic reached historical broker tick validation **after** account fingerprint/flat positions/orders, fresh symbol, actual broker margin/loss matrix, legacy inspector, deal/history and seven-frame reads. Their aggregate data was not persisted because the old collector wrote the full report only after history tick validation. No broker order, no Policy A admission.

**Demonstrated software defect:** the source validator collapsed timestamp before-start/after-end, out-of-order, bid zero and ask crossing into **one** guard. Source also used fractional-second tick range bounds. Do not invent which individual subtype produced this Exness failure. Official MT5 tick reference: `https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py` and `https://www.mql5.com/en/docs/series/copyticks` (zero bid/ask may indicate market depth empty; not safe to accept as executable quote).

**SAME DRAFT PR40 corrected offline:** immutable tick subreason guards; conservative exact whole-second UTC historical and prospective bounds (no dropped ticks, no price relaxation); fail-closed pre-tick private **INCOMPLETE_NOT_ADMITTED** checkpoint preserving money/history/bar observations even when historical tick source fails. Adversarial tests added. Earlier test SHA `1b82ab285b88c00d26bba31d2d130f23519c7ba2` failed one expectation on a valid prior tick; corrected at `462ac5e94fbeb656f3415603f12e81fdc3c3bd58`. Exact optional short static-only launcher `phase0/ops/pr40_existing_failure_static_stage_only_20261023.ps1` now pins `462ac5e94fbeb656f3415603f12e81fdc3c3bd58`. **Check latest five exact-HEAD native CI checks before requesting a single new owner run; no automatic reattempt.** Source fix and history report updates have not been executed on VPS yet.

**Safety:** preserve all historical failures; sole PR40 DRAFT/UNMERGED; `main` and accepted governance rule7 unchanged; S2 `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` remains; external Python trading disabled; no DEMO trading permission or LIVE. See [reconciled incident](MT5_CORRECTED_CAPTURE_FAIL_CLOSED_2026-10-23.md).


## 2026-10-23 — VPS FAILED-CAPTURE INVENTORY RECONCILED; NEXT OPTION ONE SHORT STATIC-ONLY DIAGNOSIS

**Owner supplied private file inventory for the already failed corrected collector.** `failure.json` exists (185 bytes), SHA256 `83292117FAA298CB527459D02CA23C91558F166238AECE98CC2AC5E6F3BCA728`, exactly reproduced by local SHA256 of the pinned collector's six-field canonical failure JSON. `past_four_hour_broker_ticks.jsonl` exists at **0 bytes**. `static_evidence.json`, `prospective_run_registration.json`, both prospective JSONL files, `complete_evidence.json` and `shareable_summary.json` **do not exist**. Source-order proof: **actual MT5 initialize succeeded and static read path was entered**, since the unique private directory and historical-tick file are created only after a successful MT5 initialize. One static safety check or first-tick handling failed before the first valid historical tick write. The exact source guard still **UNKNOWN**; zero quotes, no completed 4h window or v1.1/admitted broker cash evidence. Full inventory, source ordering and hash receipt: [immutable corrected-run incident](MT5_CORRECTED_CAPTURE_FAIL_CLOSED_2026-10-23.md). Earlier pre-MT5 import failure stays separate.

**Owner-independent mitigation (same sole draft PR40):** source commit `723e276ca32f80e6b705c8dd087a4325609c59e5` adds fixed sanitized `failure_stage`, `safe_guard_code` allowlist and adversarial redaction tests to the same existing collector. A **single optional owner-attended short STATIC-ONLY** PowerShell launcher, `phase0/ops/pr40_existing_failure_static_stage_only_20261023.ps1`, exact code pin above, can run the existing collector **without `--prospective-four-hours`**. It must not be used until native CI is verified. Its output may isolate a current-state guard; it cannot retroactively prove the same transient cause from the previous run, and it is not a four-hour capture or execution admission. It does not change terminal/account permissions or place/check orders. No new VPS run has occurred.

**Preserved CI defect:** initial new launcher-test SHA `7981e624991730580d9e4935fcec01a24c68131e` FAILED Windows and Ubuntu in DEMO-admit/release workflows due to Ruff `S603` on the parser-only subprocess call (no broker action). Same-PR correction `89b7c80a75f771fffb1ab16fb8f5bb8a1b934715` marks the parser-only command with an explicit audit annotation matching existing tests. Latest full CI must be checked before relying on the static-only script. Historical failure remains immutable, no blanket reruns.

**Risk/governance:** S2 `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` still blocks `order_check/order_send`; no real DEMO order, no LIVE, no merge/deploy approval, and accepted main rule7 conflict remains unresolved. One active DRAFT PR40 only.


## 2026-10-23 — CORRECTED VPS COLLECTOR ACTUALLY FAILED CLOSED; IMPORT PREFLIGHT PASSED

**LATEST OWNER EVIDENCE, superseding the prior "corrected run output pending" note.** Read the [new immutable incident record](MT5_CORRECTED_CAPTURE_FAIL_CLOSED_2026-10-23.md) before interpreting any earlier progress narrative.

The owner's existing corrected comprehensive PowerShell run loaded PR40 launcher at `a68063d22fa28c04f9c1f505dd3821af15a5e814` and collector source pin `10425e6180ef660226e298ef06a0fa423334332e`. Exact console: `PINNED_LOCAL_IMPORT_PREFLIGHT_PASS_NO_MT5` **PASS**; subsequently `{"error_type":"DemoSafetyError","no_retry_without_source_review":true,"order_check_calls":0,"order_send_calls":0,"output_location":"PRIVATE_LOCAL_ONLY","status":"FAIL_CLOSED_NO_ORDER"}` followed by PowerShell fail-closed. **This is NOT the earlier ModuleNotFoundError.** Actual MT5 initialize, exact account/flat exposure, money matrix, 7 bars, 4h historical/prospective samples are **UNKNOWN** from this transcript. No shareable completion JSON or SHA printed; 4h capture NOT ADMITTED. The printed private path is an intended location, not proof of files.

Demonstrated defect: prior collector's sanitized exception output removed *all* failing-stage context, so its `failure.json` (if any) cannot recover the exact guard. In SAME PR40, a diagnostics-only offline change adds fixed failure-stage labels, booleans for already persisted private artifacts and privacy/no-order tests. This change is **not active in the original source pin** and is **not evidence that the original MT5 failure is fixed**; native CI must be assessed at the exact new HEAD. The one allowed next owner action is **local-only, no-MT5 inventory of existing captured private file names, sizes and optional row counts/hashes**; no blanket new 4h attempt or extra broker diagnostics. Preserve raw evidence only on VPS and do not publish account/ticket data. S2 hard Policy A execution denial, accepted main governance rule7 and LIVE NO_GO remain intact.


## 2026-10-23 — NEW-CHAT LIVE GITHUB RECONCILIATION; VPS OUTPUT NOT YET RECEIVED

- Connected GitHub API verified accepted `main=bf6c931fac208ed2b781a2d22734df1124dea1e6`, and the one OPEN / DRAFT / UNMERGED engineering PR #40, branch `integration/real-exness-demo-v2-single-lineage-20261023`, at **pre-receipt** HEAD `dcb9afcffbf969d31d7a1c46e844f7d499cc13b1`. PR40 was 41 commits ahead of main, 0 behind, with 108 changed files. This documentation-only receipt itself advances the PR branch: **re-query latest HEAD/CI**; never claim this pre-receipt SHA is still current.
- For exact pre-receipt HEAD `dcb9afc...`, GitHub Actions returned **five successful workflows / nine successful jobs**: Validate records `39951460275` (1); v1.1 source seal `39951460152` (1); demo-first-order-release-offline `39951460279` (Windows, Ubuntu); demo-admit `39951460153` (Windows, Ubuntu); production-candidate `39951460225` (Windows, Ubuntu). These are **synthetic/offline CI**, not ForexVPS or broker-order evidence.
- The owner has **reported invoking the corrected read-only launcher**, pinned to source `10425e6180ef660226e298ef06a0fa423334332e`, but its corrected-run console/JSON **has not been supplied in this chat**. Status remains `CORRECTED_SCRIPT_OWNER_REPORTED_RUN__RESULT_PENDING_OWNER_OUTPUT`; import preflight, MetaTrader5 connection, exposure, cash matrix, 4h sample count, evidence hash and overall success/failure **UNKNOWN**. Do not conflate with the immutable *older* pre-MT5 `ModuleNotFoundError: xauusd_agent` attempt. **No repeat collector action** absent review of the existing output/private evidence.
- Direct source inspection in PR40 confirms the existing `mt5_demo.py` hard `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` rejection precedes `order_check/order_send`; `s2_readonly_coordinator_port.py` refuses order submission. This is **code inspection, not VPS runtime proof**. No speculative code correction was made before observing the corrected-run output.
- Accepted `main` `GOVERNANCE.md` rule 7 still blocks trading-capable production while Gate0 is incomplete. Its narrow PR40 reconciliation is **UNACCEPTED PROPOSAL**. No PR merge, ForexVPS deploy, terminal-setting change, DEMO broker order or LIVE release is authorized by this recovery. Frozen Policy A and historical Gate0 failures remain unmodified.
- **Next exact owner dependency:** provide the *already generated* corrected-script console output / sanitized `shareable_summary.json` and its SHA-256, if produced; redact private account/terminal/deal identifiers. Diagnose that evidence before choosing any corrective action. No new VPS script or blanket four-hour rerun.


## 2026-10-23 — new-chat continuation: corrected VPS run OUTPUT PENDING

**NEWEST PRIORITY: [START HERE — authoritative new-chat handoff](START_HERE_NEXT_CHAT_BROKER_CAPTURE_HANDOFF_2026-10-23.md).** The owner reports having run the **corrected** source-pinned comprehensive read-only PowerShell script on the ForexVPS and will supply its **actual output in the NEXT CHAT**. **The run result is UNKNOWN until that output is inspected**: do not call it PASS/FAIL, assume 4h completed, or request another run. The previous distinct first attempt (missing `xauusd_agent` import) is already diagnosed and preserved. PR40 remains the one draft engineering PR; no broker orders, no VPS trading activation, no main code merge or LIVE authority has been established. Future chat: reconcile GitHub dynamically, read the forthcoming output, record its disposition in PR40, then continue the single S2 source-admitted Exness DEMO broker path. Keep source privacy and one-feature/one-PR discipline.


## Latest 2026-10-23 — PRE-MT5 IMPORT FAILURE CORRECTED; ONE SOURCE-CAPTURE ATTEMPT PENDING

The owner's first attended comprehensive launcher at prior pinned source `150b60e8884b13d6a934c1e9ff77bd523826c75e` failed **before MetaTrader5 initialization** with `ModuleNotFoundError: No module named 'xauusd_agent'`, due to a missing exported core `src` path under `python -I`. **NO prospective four-hour observation started, NO broker order was checked/sent, and no MT5 setting was changed.** This is NOT a trading result or a completed calibration. Exact [incident diagnosis and retained failure](MT5_SINGLE_CAPTURE_IMPORT_FAILURE_2026-10-23.md).

**Corrected same-PR40 single script:** `phase0/ops/pr40_one_comprehensive_mt5_readonly_4h_20261023.ps1` now pins corrected source `10425e6180ef660226e298ef06a0fa423334332e` and runs `python -I -S --self-check-imports` against the exported Git tree **before the four-hour source collection or any MT5 import/connection**. Windows/Ubuntu native source CI [39949092166](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39949092166) PASS (342 Windows, 339 Ubuntu +3 skips; Ruff/MyPy and S2 order hard-stop PASS). This isolated native import test deliberately removes CI editable/site packages. The next attended VPS invocation is the first *actual* four-hour data collection, not a repetition. Do not run old scripts or open a new correction PR. Full broker execution remains blocked pending independent source/risk/official-calendar admission and an exact owner deployment permit. Real-money LIVE is not authorized.


## Latest M1 owner dependency — ONE comprehensive genuine Exness MT5 read-only source capture

**Do not request or run multiple incremental VPS diagnostics.** The single canonical owner-run instrument is `phase0/ops/pr40_one_comprehensive_mt5_readonly_4h_20261023.ps1`, staging exact code source SHA `10425e6180ef660226e298ef06a0fa423334332e` from sole draft [PR40](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/40). Operator runs it ONCE against the already-running attached Exness Pro **DEMO** MetaTrader5 terminal using `-ConfirmAttendedReadOnlyFourHourCapture`. It does **not** change MT5 login, enable Python trading, submit/check an order, restart the terminal, or touch scheduled tasks. It never checks out the VPS Git worktree.

That ONE run captures: exact account fingerprint/trade mode/permissions, cash balance/equity/leverage/margin/free margin, global positions/pending orders, detailed XAUUSD symbol lot/tick/contract/stop/freeze/swap/execution specs, actual directional broker `order_calc_profit` and `order_calc_margin` at 0.01-lot with three stop distances each, all available account history (2000 onward) and sanitized XAUUSD historical fees/swap/commissions, seven timeframe H4/H1/M15/D1/W1/M1/M5 inventories, four-hour historical broker ticks, a **single prospectively registered four-hour window with 2,880 actual five-second bid/ask observations** plus broker tick history, offline v1.1 true-pair quote coverage/adverse-move metrics, source and output hashes, and missing-data/coverage reasons. It persists quote and tick JSONL evidence under **`%LOCALAPPDATA%\XAUUSD-BrokerEvidence\capture-*`** on the VPS, not in the PUBLIC-facing Git repository. Only `shareable_summary.json` should be pasted here; it excludes login, deal/order IDs and account history. Never upload raw local evidence without a separately verified private route.

**One run does NOT itself authorize broker orders.** This collection registers source/timing before sampling but cannot retroactively satisfy the independent owner-selected v1.1 four-hour official event/session preregistration, cannot prove a broker's actual commission/slippage/gap where no XAUUSD execution history exists, cannot certify source-complete lifetime cash history, and cannot source-authenticate BLS/BEA/Fed/Census/DOL future high-impact calendars (not an MT5 API property). All absent fields stay `NOT_ADMITTED`. Incomplete/mismatched data fails closed; there is no automatic repeat. Later source-specific issue resolution or real order acceptance tests are different tasks, not repetitions of MT5 discovery. The existing single S2 sender remains blocked by `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED`.

**Tests:** source/test HEAD `68f24ff7d22762a2a72f86ceebeb60da56975094` passed [native demo-first-order offline run 39945287070](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39945287070) with 340 Windows passed, 337 Ubuntu passed/3 skipped, Ruff PASS, MyPy PASS 20 source files, and S2 static broker-call hard stop PASS; [DEMO-admit](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39945287060), [production candidate](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39945287203), [v1.1 source-seal](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39945287086) and record validation PASS. All proof is **synthetic CI, not real VPS MT5 evidence**. Historic smaller diagnostics in `phase0/ops/` are superseded for discovery, preserved as historical reproducibility only.

**Product:** genuine MetaTrader5 `order_send` to Exness DEMO broker server using virtual account funds, once fully risk admitted and deployed; not paper fills, and never real-money LIVE automatically. PR count remains **ONE** draft PR40 with one coherent release slice, don't reopen stacked PRs. Next steps after the single VPS run: reconcile sanitized report, independently admit/reject costs and official event/session source, finish one S2 qualified STOP broker submission/PLACED→DEAL_FILL→SL/TP reconciliation, complete alerts/restart/P1 controls, obtain exact owner deployment/trading authorization. Accepted main governance rule7 conflict still requires prospective owner decision.


## 2026-10-23 — owner-run REAL broker evidence source PIN prepared, not executed

**Next actionable source step (requires attended owner/VPS action):** [`../ops/real_exness_demo_broker_money_readonly_pr40_20261023.ps1`](../ops/real_exness_demo_broker_money_readonly_pr40_20261023.ps1) is a **source-pinned, read-only** PowerShell 5.1 diagnostic. It fetches the sole consolidated PR40 lineage, verifies code source `dc5bed52682f3ece8ebd1b120bd24723d1f716b8` is an ancestor, checks exact Windows repo-root and Python3.12, exports the tested source to an isolated temporary ZIP, then attaches *only to the existing* Exness Pro DEMO terminal and reads actual symbol quote, stop-loss price-to-cash, incremental margin and broker cash/account values for both BUY and SELL 0.01-lot. It refuses LIVE/wrong fingerprint/unknown exposure and requires Python external trading disabled. It invokes NO `order_check`, NO `order_send`, NO login change or scheduled-task mutation; clears temp files afterward. Its native tests **parse only**; no VPS run, real broker receipt or numeric fee-calibration admission was performed. User must separately authorize/run on the Windows ForexVPS after the source is correctly staged; do not claim this is the promised one-command **trading** launcher.

**Current engineering on PR40:** `s2_readonly_coordinator_port.py` with exact TPB-to-S2 source preview and pending/known position/deal reconciliation; submit is still unconditionally blocked, no phantom durable order. [One coherent feature/one PR policy](../governance/PR_LIFECYCLE_POLICY_2026-10-23.md) and [prospective governance rule7 reconciliation](../governance/PROPOSED_RULE7_DEMO_ENGINEERING_RECONCILIATION_2026-10-23.md) reside on the SAME PR40, neither is silently adopted into accepted `main`. All historical 26 PRs remain CLOSED UNMERGED with five source archive refs. Owner's goal remains **genuine Exness DEMO server-side MT5 orders with virtual account funds, not paper trading**, followed by observed continuous DEMO and independent future LIVE authorization if risk admission passes. User run + real source provenance, complete v1.1 commissions/swaps/slippage/gap calibration, operational official economic calendar/session, fully qualified S2 submit and real pending/filled recovery/alerts remain release blockers.


## Latest M1 source integration and PR hygiene — 2026-10-23

**Active engineering:** sole draft [PR #40](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/40). Implemented `demo_adapter/src/xauusd_demo/s2_readonly_coordinator_port.py`, combining the objective TPB-to-S2 inspection with the existing *read-only* MT5 pending order and position/deal observers. This port rejects every `submit_qualified` call, even on math PASS; and `one_cycle_proposal` returns NO_ORDER to prevent creating phantom durable PREPARING records while the real broker sender remains unadmitted. Real authoritative broker order sending is still NOT ready or enabled. Native tests of source-only integration were green at correction HEAD `e00b0e9b849a815a94b7b44ba111041799ffee80` (and later source updates need their own exact native CI). All former 26 PRs were closed unmerged with full archival refs; keep one coherent feature/release slice per PR, prefer direct `main` bases, and do not open correction-stack PRs for ongoing PR40 work. [Prospective PR policy](../governance/PR_LIFECYCLE_POLICY_2026-10-23.md). [Narrow proposed rule7 reconciliation](../governance/PROPOSED_RULE7_DEMO_ENGINEERING_RECONCILIATION_2026-10-23.md) is NOT ACCEPTED by main and no broker/VPS activation consent follows.

**Product target remains actual MetaTrader5 Python `order_send` into Exness Pro DEMO server** on the existing account (real broker-side orders using virtual account funds), not simulated fills. Later tiny 0.01-lot LIVE is separate and not authorized; 24–48h DEMO results cannot prove profitability or auto-promote. Full broker cash and independent v1.1 numeric cost calibration, official source/authenticated session Event Guard, one gated S2 submitter and attended alert/restart/VPS evidence remain mandatory. S2 `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` is unchanged.


## Latest PR retirement / single main-based V2 engineering line — 2026-10-23

**Exactly 1 open draft PR [#40](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/40).** Original 26 open PR10–26/28/29/32–38 closed UNMERGED with archival comment; exact Git branch heads preserved in five archive refs. PR40 source snapshot `62248cd6250fde34c7b5989446f2692493cce442`: [Win 303 PASS, Ubuntu 302 PASS/1 skip, Ruff+MyPy+S2 trading hard stop PASS](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447739); v1.1 source seal [PASS](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447795); demo-admit [PASS](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447741) and production-candidate [PASS](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447779). PR40 imports 77 cumulative V2 code/source files plus 12 useful PR28 read-only source files, directly based on current main, no missing V2 source. Read the full [source archive and close ledger](CLOSED_PR_SOURCE_ARCHIVE_AND_V2_INTEGRATION_2026-10-23.md). Real MT5 Exness DEMO broker orders are NOT yet supported/authorized/observed, S2 always hard denies; main `bf6c931fac208ed2b781a2d22734df1124dea1e6` unchanged, governance7 conflict unresolved and LIVE prohibited.


## 2026-10-23 — MAIN-BASED DOCS CONSOLIDATION CANDIDATE, NOT A CODE RELEASE

[Read-first PR audit](OPEN_PR_CONSOLIDATION_AUDIT_2026-10-23.md): GitHub currently has **26 open DRAFT PRs**, arranged as three unmerged development families. Old v1.1/v1.2 research (#10–22,#28), attended S2 canary (#23–26) and failed alternative advisory (#29) require selective source reuse / evidence retention, **not wholesale merges**. Current V2 integration is the stacked #32→#38 lineage (PR32 has failed validation at its own HEAD; PR38 synthetic CI is green at its HEAD, but not a real VPS/broker pass). This DOC-ONLY branch copies **74 existing historical roadmap/decision/sanitized evidence-metadata blobs** directly from their exact GitHub source revisions without importing trading-capable code. It also adds the portfolio index and preserved owner decisions. No source PR is closed/merged yet.

**Owner execution target (unchanged):** real MetaTrader5 `order_send` to the exact connected Exness Pro **DEMO** broker server on ForexVPS, with genuine broker orders/deals/positions and virtual funds. Autonomous XAUUSD TPB; no simulator substituted. Later LIVE 0.01 lot is desired only as a separate approved pilot, never an automatic 24–48h promotion. [Product path](REAL_BROKER_DEMO_TO_TINY_LIVE_CRITICAL_PATH_2026-10-23.md). Full frozen Policy A and guard/source admissions remain blocking and S2 pre-order hard stop remains in the DRAFT code.

**Main governance conflict:** accepted `GOVERNANCE.md` rule 7 prohibits trading-capable implementation before Gate 0 closure. Later draft owner approval in principle for fast-tracked real broker DEMO cannot silently supersede it. Need a separately approved explicit scoped accepted rule update (if owner wants acceleration); none issued by this doc consolidation. Historic G0 failures intact. No real broker order/VPS access/merge verified.


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
