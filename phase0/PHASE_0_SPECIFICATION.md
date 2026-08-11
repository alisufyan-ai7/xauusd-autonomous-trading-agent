# XAU/USD Autonomous Trading Agent — Phase 0 Specification and Validation Dossier

**Document status:** Draft 0.9 — not frozen  
**Date:** 2026-08-11 (UTC)  
**Production implementation:** Prohibited until every Phase 0 exit criterion is satisfied  
**Source handoff SHA-256:** `1024ae7fe3cea0305f424e35aa959d9b9fc4863ffa1e7effefecc5df51dd4406`

## 1. Current verdict

**Version:** Draft 0.9 — 2026-08-11 UTC  
**Gate 0 is NOT complete.** Exness/API investigation is sufficiently complete for Phase 0: client-owned MT5 Python automation is operationally supported; no proprietary Exness client API is currently available; API Terms Version 15 July 2026 / 001 are channel-scoped under D-0048; and D-0049 accepts the remaining external-AI contractual/data-use ambiguity as residual owner risk. This is not a claim that Exness approved OpenAI processing. Strict local derivation and data minimization are mandatory. Seven candidate technical specifications now cover the Risk Governor, minimized Analyst contract, five setup families, execution/reconciliation, read-only session/VPS diagnostics, news protection and replay methodology. Empirical diagnostics, provider/source choices, evaluation results and marked thresholds remain unresolved. No production or trading-capable implementation may begin.

The present work authorizes only specification, read-only evidence collection, test-harness design, and validation experiments that cannot send, modify, or cancel orders.

## 2. System objective and boundary

The system may autonomously analyze XAU/USD and, only after later gates are passed, manage bounded positions on one explicitly allow-listed Exness MT5 account.

The OpenAI component is advisory. It may return a typed proposal, but it must have no callable tool, credential, import path, RPC method, or process permission capable of submitting or modifying MT5 orders. A deterministic Risk Governor and deterministic execution state machine remain the only path to order operations.

Success means demonstrated safety, determinism at the execution boundary, broker-state reconciliation, and empirical strategy evaluation. It does not mean compilation, a profitable backtest, a profitable trade, or absence of observed errors.

## 3. Evidence standard

Every claim and acceptance result must use one or more of these evidence classes:

| Class | Evidence | Examples |
|---|---|---|
| E1 | Authoritative specification | Official OpenAI, MetaQuotes/MQL5, Exness, government release calendar, or regulator documentation |
| E2 | Account-specific broker capture | Redacted `account_info`, `terminal_info`, `symbol_info`, tick, trading-session, orders, positions, and server responses from the intended account |
| E3 | Reproducible automated test | Command, environment manifest, seed, input fixture/hash, output log, assertions, and exit code |
| E4 | Independent calculation/oracle | Cross-implementation result, broker `order_calc_profit`/`order_calc_margin`, published indicator vectors, or manually derived golden vectors |
| E5 | Operational observation | Timestamped shadow/demo/tiny-live report with broker reconciliation and incident log |

Screenshots alone, successful compilation, “no errors observed,” and a single profitable backtest are insufficient.

## 4. Assumption register

| ID | Claim from handoff | Status | Phase 0 treatment / required evidence |
|---|---|---|---|
| A-001 | Windows VPS can host MT5 plus Python continuously | Partially supported | The intended Windows Server 2022 VPS completed one read-only MT5/Python capture using CPython 3.12.10, MetaTrader5 5.0.6090, and terminal build 6104. Continuous operation is not established; a 24-hour disconnect/reconnect soak and restart test remain required. |
| A-002 | Symbol is exactly `XAUUSD` | Rejected as universal; observed for current demo target | Exness documents account-dependent suffixes. The reviewed Pro MT5 demo capture selected visible `XAUUSD` on `Exness-MT5Trial15`; this value is evidence-bound to that account fingerprint and must still be rediscovered/fail-closed on every environment or account change. |
| A-003 | Gold contract size is 100 troy ounces and minimum is 0.01 lot | Observed for current demo target only | The reviewed capture reports contract size 100, tick size 0.001, tick value USD 0.10 per lot-tick, and minimum/step 0.01 lot. Eight broker calculation vectors agreed with an independent contract/leverage oracle within half a cent. Runtime broker fields remain authoritative and must be revalidated before any later order operation. |
| A-004 | Published stop levels can be hard-coded | Rejected | Exness says stop levels can change and directs clients to current contract specifications. Read live broker properties and validate again immediately before submission. |
| A-005 | `order_check()` guarantees a fill | Rejected | MetaQuotes explicitly states successful checking does not guarantee execution. `order_send` result plus subsequent order/deal/position reconciliation is required. |
| A-006 | Account supports multiple independent XAU/USD positions | Technically observed; coexistence policy separately resolved | `account_info.margin_mode=2` maps to `ACCOUNT_MARGIN_MODE_RETAIL_HEDGING`. D-0034 prohibits manual/copy/other-EA coexistence on the dedicated account. Technical mode, legal Retail Client status and coexistence policy are non-interchangeable. |
| A-007 | Broker bars/ticks can use local VPS time | Rejected | MetaQuotes documents UTC for MT5 Python bar/tick time. Store UTC only; convert to named zones only at presentation/session-rule boundaries. |
| A-008 | Risk of 0.75–1.5% per trade is acceptable | Unvalidated policy hypothesis | No external source can prove suitability or profitability. Must be explicitly approved, stress-tested, and bounded by live-stage caps. |
| A-009 | Minimum R:R of 1.8 is inherently profitable | Rejected | R:R alone does not establish expectancy. Validate per setup/regime using out-of-sample net returns and uncertainty intervals. |
| A-010 | Official macro calendars are a complete live news service | Rejected | BLS, BEA, Federal Reserve, and DOL are authoritative schedule/result sources, but production needs a machine-readable, monitored feed with revision, cancellation, timezone, latency, and outage behavior. |
| A-011 | Tick volume is equivalent to centralized gold volume | Rejected | It is broker/platform tick activity, not centralized COMEX volume. Label and test it as a broker-specific feature. |
| A-012 | OpenAI output can be made safe by requesting JSON | Rejected | Valid JSON is not schema adherence. Use Responses API Structured Outputs, strict schema validation, semantic validation, freshness binding, and fail-closed refusal/incomplete/error handling. |
| A-013 | Current balance is approximately USD 9,170 | Historical only | Never use in logic. Read account identity, currency, balance, equity, margin, and free margin on every risk decision; bind proposal to a snapshot ID and expiry. |
| A-014 | Exness generally supports EAs, therefore automated trading is permitted on this account | Rejected as universal | Exness documents EA use, but permission must be verified for the intended legal entity, residence/jurisdiction, account, instrument, terminal, and automation method. Capture `account_info.trade_allowed`, `account_info.trade_expert`, `terminal_info.trade_allowed`, `terminal_info.tradeapi_disabled`, symbol trade mode, account verification/access state, and the applicable current contract/terms. General help content is not account-specific authorization. |
| A-015 | A working Exness demo login proves legal eligibility for later live automated trading | Rejected | Demo technical access does not establish residency eligibility, legal-entity onboarding, client classification, instrument availability, or permission for production automation. The exact Exness contracting entity and current jurisdiction/account restrictions require separate documentary verification before Gate 0 freeze and again before live activation. |
| A-016 | Publicly reachable market/news data may be stored, transformed, sent to OpenAI, or redistributed without restriction | Rejected | Every source requires a provenance and rights record. Government material may be public domain subject to source-specific terms and attribution, while exchange/vendor data may require non-display, derived-data, redistribution, retention, or cloud-processing rights. Unknown rights fail closed and block the source. |
| A-017 | Zero unsafe model approvals on a frozen evaluation corpus proves the model is universally safe | Rejected | It is a necessary release test for the tested model/prompt/schema/corpus only. It cannot cover all future inputs, market regimes, provider changes, or model behavior. Deterministic validation, the Risk Governor, and an execution-isolated model boundary remain authoritative on every decision. |

## 5. Frozen safety principles (candidate for Gate 0 approval)

These are normative requirements, not strategy hypotheses:

1. **SAF-001 — Fail closed:** uncertainty in account, symbol, market data, broker state, model output, news protection, sizing, process ownership, or reconciliation yields `NO_TRADE` and prevents risk-increasing operations.
2. **SAF-002 — Deterministic authority:** model output is data only. The model cannot bypass or configure the Risk Governor at runtime.
3. **SAF-003 — Mandatory protection:** every accepted entry has a broker-side stop loss included atomically when the broker/order type supports it. Any later unprotected position is an incident requiring immediate deterministic handling.
4. **SAF-004 — No loss expansion:** no averaging down, martingale, grid recovery, stop widening, or risk-increasing modification after entry.
5. **SAF-005 — Account allow-list:** trade mode must be real only at authorized gates, and login/server/company/currency/account-mode fingerprints must match the sealed deployment configuration.
6. **SAF-006 — Single writer:** one lease-holder may perform order operations. Duplicate or uncertain ownership disables new orders.
7. **SAF-007 — Reconciliation before action:** broker state is authoritative. Startup and every risk-increasing action require reconciliation of orders, deals, and positions.
8. **SAF-008 — Human kill switch:** the operator can disable new entries without relying on OpenAI or the strategy process. Risk-reducing reconciliation and emergency close policy must be separately defined.
9. **SAF-009 — Immutable audit linkage:** every proposal, decision, request, response, and state transition is linked by IDs and versioned hashes.
10. **SAF-010 — No readiness by proxy:** compilation, unit-test success, and profitable backtests cannot independently authorize live trading.
11. **SAF-011 — Authorized automation only:** no automated/EA trading may be enabled until the intended Exness entity, jurisdiction/residency, client/account classification, account and symbol permissions, and applicable legal terms are evidenced and approved. Technical connectivity is not legal permission.
12. **SAF-012 — Licensed and attributable data only:** no external market/news data enters research, prompts, models, production decisions, logs, or redistributed artifacts unless its provenance, entitlements, permitted uses, retention, transformation, attribution, and third-party-processing rights are recorded and current.

## 6. Broker and market-data contract

### 6.1 Required account-specific probe and read-only collector contract

A read-only evidence collector must capture and redact sensitive values while preserving stable hashes for:

- OS build, Python version/architecture, `MetaTrader5` package version, MT5 terminal build, terminal path, and terminal connectivity flags;
- account login pseudonym, server, company, currency, trade mode, margin mode, leverage, margin-call/stop-out modes and levels;
- automation permission evidence: `account_info.trade_allowed`, `account_info.trade_expert`, `terminal_info.trade_allowed`, `terminal_info.tradeapi_disabled`, connection state, symbol trade mode, and an explicit statement that these runtime flags do not replace the applicable Exness agreement or jurisdiction review;
- all XAU-containing symbols and the selected symbol’s visibility, digits, point, trade mode, execution mode, fill/order modes, calculation mode, contract size, tick size/value, volume min/max/step/limit, stops/freeze levels, swap fields, and trading sessions;
- current tick with millisecond timestamp, bid, ask, spread, and local receipt timestamp;
- bars for every requested timeframe with UTC timestamps and completeness/gap statistics;
- open orders/positions and recent deals;
- `order_calc_profit` and `order_calc_margin` vectors for both directions and multiple lot/price distances.

The collector must not call `order_check`, `order_send`, order modification, or cancellation on a real account during Phase 0.

The Phase 0 collector is accepted for operator use only if all of the following objective controls pass:

1. It attaches to the already-open terminal and accepts no login, password, token, server, or account credential in arguments, files, prompts, or environment variables.
2. Before any account/history/price collection, it reads terminal status and aborts unless MT5 reports `tradeapi_disabled=true`. MetaQuotes states that Python scripts can perform trading operations only when the terminal option **Disable automated trading via external Python API** is disabled; requiring it to be enabled provides a terminal-enforced barrier in addition to source restrictions.
3. Its MT5 adapter exposes only this frozen allow-list: `initialize`, `shutdown`, `last_error`, `version`, `terminal_info`, `account_info`, `symbols_get`, `symbol_info`, `symbol_info_tick`, `copy_rates_from_pos`, `copy_ticks_from`, `orders_get`, `positions_get`, `history_orders_get`, `history_deals_get`, `order_calc_profit`, and `order_calc_margin`. The two calculation calls are local/broker calculations and do not submit requests.
4. The executable collector/adapter contains no dynamic attribute dispatch and no call path to `order_send`, `order_check`, trade requests/actions, modification, removal/cancellation, position close, `login`, `symbol_select`, market-book subscription, shell/process execution, network clients, `eval`, `exec`, `ctypes`, or arbitrary plugin loading. Credential/identifier field names may exist only in redaction and verification policy. A syntax-tree verifier must fail on forbidden imports, calls, attributes, or non-allow-listed MT5 access.
5. A fake-MT5 behavioral test records every adapter call and contains trap methods for risk-changing operations; the test must show only allow-listed calls and zero trap invocations.
6. The runner re-verifies source hashes and the syntax-tree policy before launch. The collector rechecks the terminal protection flag immediately before and after evidence capture and records both values. If either is not true, the run fails and the bundle is marked invalid.
7. Output is written only to a newly created timestamped evidence directory. Credentials are never collected. Login, account holder, ticket/order/deal/position identifiers, comments, and user-profile path components are removed or HMAC-pseudonymized with a per-run secret that is not included in the bundle.
8. The bundle contains canonical JSON, UTC timestamps, per-file SHA-256 hashes, a manifest, tool/package/runtime versions, requested parameters, completeness/errors, the verifier report, and a final archive hash. Hashes prove integrity of the captured bundle, not truth of broker responses.
9. Evidence collection has no internet client and does not upload data. The operator manually returns the generated archive after inspecting the filename and size; credentials must never be pasted into chat.
10. The Windows dependency lock must name every direct and transitive distribution with an exact version and approved SHA-256 and must reject source distributions. The pre-run verifier checks the exact lock contents, and the runner checks the installed versions before importing the live adapter. A dependency-resolution or version mismatch is a safe stop.

#### 6.1.1 Accepted collector artifact register

| Field | Frozen value |
|---|---|
| Purpose | Phase 0 read-only evidence collection only |
| Artifact | `XAUUSD_Phase0_ReadOnly_Evidence_Collector_v0.1.1.zip` |
| Collector version | `v0.1.1` |
| Archive SHA-256 | `3be08021c4d2c9e8206819e9e14838d5f811ac5a295422e4db501232700a1a59` |
| Runtime/dependency scope | 64-bit CPython 3.12; binary-only `MetaTrader5==5.0.6090` and `numpy==2.5.0`, both exact and SHA-256-pinned |
| Objective pre-run evidence | Static AST allow-list PASS; 3/3 behavioral tests PASS, including dependency-lock completeness; zero forbidden-operation trap calls; protection-disabled fail-safe queried no account; package manifest PASS; re-extracted archive verification PASS |
| Acceptance status | Accepted for one operator evidence run under D-0028 and D-0029; not a production dependency or trading authorization |

Collector `v0.1.0` (SHA-256 `0e20f68ca4d62f208127f9795f5fc1c60b631aa8c54f50228eca4adeddda7237`) is withdrawn from operator use. Its lock omitted the transitive `numpy` requirement, so pip correctly rejected installation under `--require-hashes`. It remains recorded in D-0026 for history and is superseded by D-0028/D-0029; it must not be modified or run.

Artifact identity is byte-exact. Any change to the ZIP, packaged source, dependency lock, runner, verifier, or manifest invalidates this acceptance and requires a new collector version, new SHA-256, complete re-verification, and an appended Decision Log entry. A successful run would provide account/VPS evidence for review; it would not establish contractual authorization, model safety, profitability, production readiness, or Gate 0 completion.

The collector cannot determine residency eligibility or the governing Exness legal entity from MT5 alone. It records broker/server/company clues and a `MANUAL_DOCUMENTARY_VERIFICATION_REQUIRED` finding. Gate 0 requires a separate redacted account/legal-document record naming the contracting entity, country of residence, client/account type, applicable agreement/version/date, and any automated-trading or instrument restrictions.

#### 6.1.2 Reviewed VPS/account evidence and identity model

The received evidence archive is frozen as follows:

| Field | Reviewed value |
|---|---|
| Evidence archive | `xauusd-phase0-evidence-20260809T235355Z-c6a411ea.zip` |
| Archive SHA-256 | `021f658ac2acb463d17e17d4ad2150f3fcb24750fce49789024e3b150645c62f` |
| External sidecar | Exact SHA-256 match |
| Internal `MANIFEST.json` SHA-256 | `b032e078b7fce8d313dc6225d2878584712e95350e47ab42b174756896f12226` |
| Collector provenance | `v0.1.1`; all seven package-source hashes match the accepted `v0.1.1` files |
| Capture interval | 2026-08-09 23:53:55.209Z–23:53:58.336Z |
| Run result | `PASS`, zero reported collection errors; Gate 0 explicitly `INCOMPLETE` |
| Read-only barrier | `tradeapi_disabled=true` before and after; `terminal.trade_allowed=false` |

Identity and organizational fields are independent provenance claims and must never be aliased, overwritten, or inferred equal merely because they contain an Exness or MetaQuotes name:

| Canonical field | Value | Source | Verification status |
|---|---|---|---|
| `contracting_legal_entity` | `Exness (SC) Ltd` | Owner-reported Personal Area footer, 2026-08-10 | Recorded separately; official Exness material confirms the entity exists, but account linkage and the applicable agreement/version still require a redacted documentary hash/review |
| `personal_area_account_type_label` | `Pro — MT5 Demo — USD` | Owner-reported Personal Area account card, 2026-08-10 | Partially corroborated by demo trade mode, USD currency, `Pro\\Forex\\XAUUSD` symbol path, no suffix, and 1,024 pending-order limit; the exact PA label is not emitted by MT5 |
| `mt5_account_serving_company` | `Exness Technologies Ltd` | `ACCOUNT.json` → `account_info.company` | Verified from the hashed evidence bundle; MetaQuotes defines this property as the company serving the account, not the contracting legal entity |
| `mt5_trade_server` | `Exness-MT5Trial15` | `ACCOUNT.json` → `account_info.server` | Verified from the hashed evidence bundle |
| `mt5_terminal_vendor_company` | `MetaQuotes Ltd.` | `TERMINAL.json` → `terminal_info.company`, before and after | Verified from the hashed evidence bundle; this is the terminal vendor field |

The reviewed technical profile is: USD 10,000 balance/equity, demo trade mode, leverage 1:2000, retail-hedging margin mode, no open orders or positions, visible `XAUUSD`, 100-unit contract size, 0.001 tick/point, 0.01 minimum and step, 200 maximum volume, zero reported static stop/freeze levels, and eight profit/margin calculation vectors. The technical flags `account.trade_allowed=true`, `account.trade_expert=true`, and symbol trade mode `4` show account/symbol capability at capture time only; they do not establish contractual or jurisdictional authorization.

The bundle contains 3,072 bars across D1/H4/H1/M15/M5/M1 with zero duplicate timestamps, zero non-monotonic transitions, and zero invalid OHLC rows under the review checks. Its current `symbol_info_tick` was 3.857 seconds old at completion. The separate 2,000-row tick array begins one hour before capture but stops 2,110.335 seconds before completion because `copy_ticks_from` returns from the requested start and the count cap was reached; it is not accepted as a latest-tail or full-hour distribution. Eleven tick rows share millisecond timestamps, with no backwards ordering or crossed/non-positive quotes.

This evidence does **not** provide the authoritative weekly XAUUSD trading-session table, prove 24-hour VPS reliability, prove residency/client classification, identify the exact Exness agreement/version accepted by this Personal Area, or establish automated-trading permission under that agreement. Those remain Gate 0 blockers.

### 6.2 Sizing requirement

For a proposed entry and stop, lot size must be solved against account-currency loss using broker calculation functions where available, then rounded **down** to the volume step. After rounding, recompute loss and margin. Reject if any of these are false:

- computed stop-loss cash risk is finite, positive, and at or below the risk budget;
- volume is within min/max/directional limits;
- margin safety remains above a frozen buffer under spread/slippage stress;
- entry, SL, and TP align to tick size and comply with current stop/freeze constraints;
- price snapshot is fresh and symbol is fully tradable;
- both an independent oracle and broker calculation agree within a frozen tolerance.

### 6.3 Data integrity

- UTC-aware datetimes are mandatory internally.
- Closed-candle features must never read the forming candle.
- Every feature vector includes `source_symbol`, `server`, `bar_close_utc`, `data_asof_utc`, and an input hash.
- Gaps, duplicates, non-monotonic time, zero/negative prices, crossed bid/ask, stale ticks, and missing history are explicit errors.
- Session definitions must use IANA time zones and tested daylight-saving transitions; “London,” “New York,” and broker day may not be inferred from VPS local time.
- Broker tick volume must be named `broker_tick_volume`; no claim of centralized volume is permitted.

## 7. OpenAI Analyst contract

### 7.1 API boundary

Use the OpenAI Responses API with Structured Outputs (`text.format` with a strict JSON schema) after model availability, latency, cost, refusal, incomplete-response, and schema behavior have been benchmarked. Official OpenAI documentation states that Structured Outputs provide schema adherence whereas JSON mode only provides valid JSON.

The request must use a pinned model snapshot when available, a pinned prompt hash, `store: false` unless a separate data-governance decision approves storage, an explicit timeout, bounded output tokens, and no trading or shell tools.

### 7.2 Proposal schema — required semantics

The final schema must include at least:

- `schema_version`, `proposal_id`, `decision`; where decision is `NO_TRADE` or `PROPOSE_TRADE`;
- `snapshot_id`, `data_asof_utc`, `valid_until_utc`, `symbol`, `account_fingerprint`;
- `setup_family`, `regime`, `direction`, `entry_type`, `entry_price`, `stop_loss`, `take_profit_plan`;
- `invalidation_rules` expressed as a finite enumerated rule set, not executable/free-form logic;
- `suggested_risk_tier` as an enum only; no percentage authority;
- `confidence` as a calibrated model score with no claim that it is a probability until calibration evidence exists;
- `reason_codes` from a controlled vocabulary and a short audit summary.

All numeric prices remain proposals. The Risk Governor recalculates tick alignment, distance, cash risk, R:R, freshness, spread, margin, limits, and broker constraints from current state.

### 7.3 Failure handling

Refusal, incomplete status, rate limit, timeout, network error, server error, missing output, duplicate proposal ID, unknown enum, NaN/infinity, stale snapshot, inconsistent direction/prices, or semantic-rule failure results in `NO_TRADE`. Retries must be bounded, jittered, and incapable of duplicating an order; a retry creates analysis only, never an execution retry.

### 7.4 Model acceptance benchmark

Before model selection, run a versioned evaluation corpus containing valid setups, no-trade cases, stale/inconsistent inputs, prompt injection strings inside market/news text, extreme numbers, missing fields, and adversarial instruction conflicts. Required result for safety invariants: zero unsafe approvals in the frozen corpus. This is a **necessary acceptance test limited to the exact frozen corpus, model snapshot, prompt, schema, tool configuration, and harness**; it is not proof of universal model safety or a substitute for online deterministic controls. Any unsafe approval fails the candidate, while zero observed unsafe approvals only permits progression to later gates. The model remains non-authoritative: schema validation, semantic validation, freshness checks, the Risk Governor, state reconciliation, and execution isolation decide whether any action is possible. Model selection must report latency percentiles, API-error rate, schema-valid rate, semantic-valid rate, disagreement rate, token use, and cost. Strategy quality is evaluated separately.

## 8. Deterministic Risk Governor

### 8.1 Required inputs and invariants

The governor consumes current broker/account state, current tick, the proposal, open exposure, realized/unrealized P&L, risk ledger, news state, and sealed policy configuration. It returns only `REJECT`, `APPROVE`, or `APPROVE_RESIZED`, with reason codes and a complete calculation trace.

It must enforce:

- cash risk per trade and aggregate worst-case risk;
- realized daily/weekly loss, equity drawdown, and consecutive-loss pauses;
- maximum positions and directional exposure;
- mandatory SL and prohibition of stop widening/averaging;
- spread, slippage stress, stale-data, news, market-hours, and liquidity locks;
- account/symbol fingerprint, volume/margin/stop constraints, and duplicate intent;
- entry expiry and one-way state transitions;
- commission, swap where relevant, and conservative transaction costs in R:R/expectancy filters.

### 8.2 Approved Risk Policy A specification baseline

Policy A is approved for specification and deterministic testing only. It does not authorize demo or live trading.

- Per-trade planned risk: `0.25% × min(current_balance, current_equity, approved_strategy_allocation)`; initial `approved_strategy_allocation = USD 10,000`.
- It scales downward automatically as balance/equity falls and never scales above USD 25 merely because capital exceeds the approved allocation. Any allocation increase requires a new owner decision.
- Concurrent planned risk: USD 50; daily loss ceiling: USD 75; weekly loss ceiling: USD 150; total strategy drawdown ceiling: USD 500 / 5% of the reference allocation.
- Pause after approximately three full-risk-equivalent losses; the exact deterministic accumulation/cooldown definition and tests must be frozen before Risk Governor implementation.
- Daily and weekly loss are computed as period-start adjusted strategy equity versus current adjusted strategy equity, normalizing deposits, withdrawals and transfers. Realized and unrealized P/L reconcile that equity change and must not be added in a way that double-counts one economic loss.
- No AI-confidence override, martingale, grid/recovery loss expansion, or averaging a failed trade.

Recommended safety baseline for discussion—not an approved setting:

- shadow/demo: no real-money risk;
- tiny live: fixed 0.01 lot where broker-computed worst-case loss also stays below 0.25% of current equity;
- no “high-conviction” risk override;
- scaled-live limits remain disabled until out-of-sample, shadow, demo, and tiny-live evidence passes.

Stop-loss orders reduce risk but cannot guarantee the intended loss because gaps, slippage, liquidity, and execution failures exist. Stress tests must therefore include fills beyond the stop.

## 9. Execution and position state machine

The frozen specification must define a single persisted state machine before execution code exists. Minimum states:

`OBSERVED → PROPOSED → REJECTED | APPROVED → SUBMITTING → ACKNOWLEDGED → RECONCILED_OPEN → MANAGING → EXIT_SUBMITTING → RECONCILED_CLOSED`

Exceptional states: `UNKNOWN`, `QUARANTINED`, and `INCIDENT`.

Required properties:

- each intent has a globally unique deterministic idempotency key derived from account fingerprint, symbol, strategy version, setup, direction, and proposal ID;
- `SUBMITTING` is durably recorded before the broker call;
- process failure after broker submission must reconcile by magic number/comment/ticket/deal/position evidence before any retry;
- `order_send` acknowledgement is not sufficient; subsequent broker state must match the intended transition;
- partial fills, partial closes, requotes, rejected modifications, pending activation during restart, manual trades, and unknown positions have explicit transitions;
- OCO behavior is local orchestration unless broker evidence proves native behavior; race conditions must be adversarially tested;
- risk-reducing actions may use a separate emergency path, but it must never open or increase exposure.

## 10. News and macro protection

Authoritative schedules exist for BLS CPI/employment releases, BEA GDP/PCE, and Federal Reserve meetings/statements. They establish when many protected events are scheduled, but they do not by themselves provide a complete low-latency production feed.

Phase 0 must select a provider or redundant acquisition design and freeze:

- covered event taxonomy and impact level;
- authoritative source, update frequency, latency target, timezone, revision/cancellation handling, and health check;
- pre-event and post-event lock durations by event type;
- spread/volatility normalization criteria for resumption;
- behavior when calendar/feed sources disagree or fail: fail closed for protected windows;
- treatment of unscheduled Fed/geopolitical shocks; at minimum an abnormal-volatility circuit breaker independent of news classification.

The model may summarize macro context but cannot change lockout state or predict a release as a reason to bypass protection.

### 10.1 External data provenance and licensing gate

Before any external market, price, calendar, headline, article, sentiment, or event data is admitted, the source register must contain:

- provider and original owner; dataset/feed/product name and version; delivery endpoint/channel; direct versus redistributor lineage;
- governing terms/license identifier, effective date, evidence copy/hash, account/entitlement ID pseudonym, permitted users/devices/locations, and renewal/termination date;
- explicit rights for automated trading/non-display use, research/backtesting, persistent storage and retention duration, derived features/labels, internal display, cloud/VPS processing, disaster-recovery copies, and audit retention;
- explicit rights or prohibition for sending raw or derived content to OpenAI or any other subprocessor, model training/fine-tuning, and human support access;
- redistribution/export rights for logs, evidence bundles, reports, screenshots, alerts, client dashboards, and derived data; required attribution and provider disclaimers;
- event/observation timestamp from the source, provider publication timestamp, receipt timestamp, revision/cancellation/version markers, timezone, sequence/event ID, raw payload hash, parser version, and transformation lineage;
- SLA/rate limits, outage and correction behavior, geographic/client-class restrictions, security obligations, deletion duties, and a named owner for periodic rights review.

Public-domain status is source-specific, not inferred from a `.gov` domain or public URL. BLS states its publications are generally public domain but requires API citation/access-date language and prohibits false representation; BEA and Federal Reserve Board material is generally public domain unless otherwise indicated and third-party material remains restricted. Exchange data is different: CME explicitly distinguishes internal non-display use, distribution, and derived-data licensing. Therefore each intended use must map to an affirmative right. `UNKNOWN`, expired, conflicting, or unverifiable rights make the source `BLOCKED`; no data from it may be persisted, put into a model prompt, or drive a trade decision.

## 11. Strategy and backtest governance

Each setup family is a separate versioned strategy with objective, computable entry, invalidation, stop, target, and expiry definitions. Natural-language names such as “trend pullback” are not implementation specifications.

Before testing a family, freeze:

- feature formulas and warm-up windows;
- parameter search space and number of trials;
- event labeling and fill assumptions;
- train/validation/out-of-sample partitions by chronology;
- embargo/purging rules where labels overlap;
- commission, spread, swap, slippage, missed-fill, and gap models;
- primary metric and rejection threshold.

Reports must show all trials, not only the winner. They must include out-of-sample expectancy, uncertainty intervals, drawdown duration and depth, tail losses, regime/session/setup breakdowns, cost sensitivity, Probability of Backtest Overfitting where applicable, and Deflated Sharpe Ratio or another predeclared multiple-testing correction. Research on PBO and the Deflated Sharpe Ratio demonstrates why unreported trial counts and selection bias can make apparently strong backtests unreliable.

Candidate Gate 3 thresholds requiring approval before any strategy search:

- positive out-of-sample net expectancy whose predeclared confidence procedure does not support a materially negative value;
- no single month/session/setup variant supplies an unacceptable share of total performance;
- drawdown and loss-streak stress stay inside the owner-approved risk envelope;
- strategy remains non-catastrophic under at least 2× observed median spread, adverse slippage, missed entries, and delayed exits;
- all trials and excluded data are recorded; look-ahead/leakage tests pass;
- PBO/DSR thresholds are frozen before optimization, not chosen after seeing results.

No universal minimum trade count is declared yet; the minimum must be derived from the effect size and uncertainty target, while reports must warn when a setup is too sparse for inference.

## 12. Deployment, security, and operations

- Windows VPS is the provisional production host because the official Python integration communicates directly with an installed MT5 terminal.
- The Mac is a development/monitoring client only and is not required for continuous operation.
- Secrets must use OS-protected storage/service environment, least-privilege accounts, and redaction. They must never enter prompts, logs, source control, crash dumps, or support bundles.
- Network egress is allow-listed to OpenAI and required news/monitoring endpoints; MT5 connectivity is separately controlled.
- Dependency versions and hashes, MT5 terminal build, Python architecture, model snapshot, prompt/config hashes, and database schema version form the release manifest.
- Logs are append-only at application level and copied off-host; timestamps use synchronized UTC with clock-drift alerts.
- Watchdog restart is bounded. Restart loops or repeated reconciliation failure enter quarantine instead of repeatedly touching broker state.
- Backup/restore, audit retention, log-disk exhaustion, certificate expiry, OS patching, MT5 auto-update, and rollback procedures must be tested.
- Deployment includes separate `analysis_enabled` and `execution_enabled` switches; execution defaults off after installation, config change, account change, version change, or failed health check.

## 13. Validation gates and objective acceptance

| Gate | Minimum objective evidence | Acceptance rule |
|---|---|---|
| 0 — Specification freeze | Approved requirements, schemas, risk policy, state machine, threat/failure model, data/news sources, test plan, release thresholds, and Decision Log; document hashes | No unresolved safety/execution/account assumptions; all owner decisions recorded; production implementation explicitly authorized only for Phase 1 |
| 1 — Deterministic unit/integration | Versioned test report, golden vectors, mutation/property tests, cross-oracle comparisons, coverage of requirements | Zero failed tests; zero critical surviving mutations in safety math/state transitions; all exclusions justified |
| 2 — Failure/adversarial | Fault-injection matrix and logs for every declared failure mode | Zero risk-increasing action under uncertain state; exact expected quarantine/recovery transitions |
| 3 — Historical replay | Immutable dataset hashes, all trials, OOS report, leakage audit, cost/stress report | Meets predeclared statistical/risk thresholds; no unexplained mismatch between replay and live feature calculations |
| 4 — Live shadow | At least one full market month plus event coverage defined by the frozen test plan | No execution capability; complete decisions/audit; broker/live feature reconciliation within tolerance; incidents resolved |
| 5 — Exness demo | Broker lifecycle test suite including restarts, rejects, partial behavior where reproducible, pending expiry, modifications, OCO races | 100% state reconciliation; zero duplicate exposure; all broker-specific assumptions evidenced |
| 6 — Tiny live | Fixed minimal exposure and an explicit human approval; execution-focused sample and monitoring | No critical incidents or policy breaches; performance is reported but cannot alone justify scaling |
| 7 — Controlled scaling | Predeclared live sample, risk committee/owner decision, unresolved-defect list, rollback drill | Explicit approval for each cap increase; automatic scaling is prohibited |

## 14. Phase 0 exit checklist

Gate 0 cannot be marked complete until all items below are satisfied:

- [ ] Contracting entity is linked to the intended account by a redacted documentary record; jurisdiction/residence/client classification, applicable agreement version/date, and automated-trading restrictions are reviewed.
- [x] One read-only account/VPS/terminal/symbol probe has been run and its byte-exact evidence reviewed under D-0030.
- [x] Dedicated-account coexistence policy approved by D-0034; demo target separately reports technical retail hedging.
- [ ] Authoritative account-specific XAUUSD weekly trading sessions are captured and specified.
- [ ] Intended VPS restart/reconnect and 24-hour soak evidence passes.
- [ ] Risk policy is approved in cash/equity terms for every deployment stage.
- [ ] Setup families included in first implementation have algorithmic specifications; vague families are deferred.
- [ ] Analyst JSON Schema, semantic rules, prompt policy, model benchmark, and data-governance policy are frozen.
- [ ] Execution/position state machine and idempotency/reconciliation algorithms are frozen.
- [ ] News/calendar source, protected events, health SLA, licensing/provenance rights, and lockout/resumption rules are frozen.
- [ ] Data retention, audit schema, secret handling, operator access, kill switch, incident response, rollback, and recovery are frozen.
- [ ] Backtest dataset plan, trial accounting, split methodology, cost model, and acceptance thresholds are frozen before optimization.
- [ ] Gate 1–7 test matrices map each requirement to objective evidence.
- [ ] All critical `TBD`, `TBR`, and `UNKNOWN` items are resolved or explicitly deferred outside the first release.
- [ ] Specification and Decision Log hashes are recorded and owner approval is explicit.

## 15. Blocking inputs/evidence needed from the owner

These do not require the owner to review source code:

1. A redacted Personal Area/account-information record that binds `Exness (SC) Ltd` and `Pro — MT5 Demo — USD` to the intended account without exposing login, name, address, email, or documents; plus the exact accepted Client Agreement/General Business Terms version or effective date.
2. Confirmation of country of residence/client classification and any entity-, jurisdiction-, account-, VPS-, API-, EA-, or automated-trading restrictions shown in the Personal Area or governing documents.
3. Emergency treatment beyond quarantine for unknown exposure. Coexistence itself is decided by D-0034: it is prohibited; unknown exposure quarantines new risk and alerts, without automatic closure.
4. Maximum acceptable loss limits stated as: per trade, daily, weekly, and total strategy drawdown; and whether emergency closure of unrecognized exposure is authorized or must only quarantine/alert.
5. Acceptable decision latency and monthly OpenAI/news-data budget.
6. Preferred operator alert channels and required response expectations.

## 16. Authoritative source register

Accessed 2026-08-07 through 2026-08-10:

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI Responses API overview](https://developers.openai.com/api/reference/responses/overview/)
- [OpenAI Responses migration notes](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [MetaQuotes Python integration](https://www.mql5.com/en/docs/python_metatrader5)
- [MetaQuotes initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py)
- [MetaQuotes account information](https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py)
- [MetaQuotes account properties and margin modes](https://www.mql5.com/en/docs/constants/environment_state/accountinformation)
- [MetaQuotes symbol information](https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py)
- [MetaQuotes symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants)
- [MetaQuotes tick retrieval semantics and UTC](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py)
- [MetaQuotes order preflight](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py)
- [MetaQuotes order submission](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py)
- [MetaQuotes broker-side profit calculation](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py)
- [MetaQuotes UTC bar handling](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py)
- [Exness legal documents by entity](https://www.exness.com/legal-documents/)
- [Exness Pro account](https://get.exness.help/hc/en-us/articles/17537794560540-Pro-account)
- [Exness trading servers](https://get.exness.help/hc/en-us/articles/12232298502684-Available-trading-servers)
- [Exness commodities specifications](https://get.exness.help/hc/en-us/articles/17854173039388-Commodities)
- [Exness account suffixes](https://get.exness.help/hc/en-us/articles/360014560220-Account-type-suffixes)
- [Exness stop levels](https://get.exness.help/hc/en-us/articles/360011676519-About-stop-levels)
- [Exness higher margin requirements](https://get.exness.help/hc/en-us/articles/20618327917596-Higher-Margin-Requirements-HMR)
- [Exness slippage rule](https://get.exness.help/hc/en-us/articles/18054855363484-Slippage-rule)
- [NFA risk disclosure guide](https://www.nfa.futures.org/members/member-resources/files/cta-disclosure-documents.pdf)
- [Bailey et al., Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)
- [Bailey and Lopez de Prado, Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)
- [BLS release schedule](https://www.bls.gov/schedule/)
- [BEA release schedule](https://www.bea.gov/news/schedule)
- [Federal Reserve FOMC calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)

## 17. Known limitations of this draft

- One point-in-time Windows VPS/MT5/demo-account capture is reviewed; continuous availability, reconnect, restart, upgrade, and clock-drift behavior remain untested.
- The contracting entity and PA account label are owner-reported observations. The exact account-linked documentary record, agreement version/effective date, residence/client classification, and automated-trading restrictions remain pending.
- MT5 reports the account-serving company and server, not the contracting legal entity; those fields are intentionally separate.
- The authoritative weekly XAUUSD session table is absent. Static zero stop/freeze fields are not accepted as a permanent promise, and all broker constraints must be refreshed later at the deterministic execution boundary.
- The 2,000-row tick array is a count-limited forward sample from one hour before collection and is not the latest tick tail or a complete hour.
- No OpenAI API key or intended API project was used; model availability, rate limits, latency, cost, schema behavior, and retention settings remain untested for the owner's account.
- No production news provider is selected or licensed.
- Risk limits and statistical thresholds require explicit owner approval and prospective freezing.
- Setup definitions remain taxonomy labels rather than executable mathematical specifications.

## 18. Legal-document evidence and automation boundary

The canonical clause-level review is `EXNESS_SC_LEGAL_APPLICABILITY_REVIEW.md`. Client Agreement v038 (SHA-256 `ae02ca31a9e2ba1d8ef81cc973caa169e901aa6d802b4f9949a05e3cb1217ddc`) and General Business Terms v021 (SHA-256 `a8e8e0942d402c415770943283ef2f44b4d680339530d28b167fc79928174b11`) are the primary supplied contractual evidence.

The owner is provisionally classified as a Retail Client under Client Agreement Part A 3.1-3.3 unless Exness has issued written notice otherwise. This must never be aliased to MT5 retail-hedging margin mode.

Basic client-owned MT5 Python/EA automation is operationally supported by account-specific written Exness support evidence. Exness support also states that no proprietary client trading/data API is currently available, so no Exness API-key interface is assumed. The official API Terms of Use, Version 15 July 2026 / 001, are scoped under D-0048 to Exness API/API-Key use and are not presumed to govern the present no-key MT5 Python channel.

Under D-0049, external-AI processing ambiguity is an owner-accepted residual risk rather than a Gate 0 blocker; Exness has not explicitly approved it. MT5 data is obtained locally; indicators, structure, regimes, levels and volatility are computed locally; only necessary derived setup features may be sent to OpenAI. Credentials, account/server identifiers, ticket IDs, exact account/risk/margin state and unnecessary bulk/raw feeds are prohibited. External-Python trading protection remains enabled and no risk-changing MT5 call is authorized. Reopen Exness research only for contradictory authoritative evidence or a material channel/data-use change.

## 18A. Frozen architecture boundary

The intended broker path is `Exness MT5 -> local Python -> deterministic Risk Governor -> MT5 Python execution`. The reasoning path is `MT5/market data -> deterministic local features -> OpenAI analytical proposal -> deterministic semantic/risk validation -> MT5 Python execution`.

OpenAI is an analytical component, never broker interface or execution authority. It has no MT5 credentials or order-sending capability. A proposal passes schema validation, snapshot/freshness validation, semantic validation, deterministic Risk Governor and the execution state machine before an order can exist. Malformed, contradictory, stale or unsafe output yields `NO_TRADE`, `REJECT` or `QUARANTINE`. Model-proposed lot size never overrides deterministic sizing.

## 19. Dedicated-account coexistence policy

The future agent is bound to a dedicated account with no manual XAUUSD trades, external copied/signal trades, other EA, trade copier, or unrelated automation. Any order or position whose ownership cannot be cryptographically and broker-state-wise proven transitions the system to `QUARANTINED`, blocks every new risk-increasing action, and alerts the operator. Automatic closure of unknown exposure is not authorized.

## 20. Account-specific XAUUSD execution semantics

The hashed demo capture records the following raw values. Official MetaQuotes enum meanings are recorded without overwriting the broker values.

| Property | Raw | Interpretation / rule |
|---|---:|---|
| `trade_exemode` | 2 | `SYMBOL_TRADE_EXECUTION_MARKET`; broker selects execution price; `ORDER_FILLING_RETURN` is not allowed for market execution |
| `filling_mode` | 1 | bit flag `SYMBOL_FILLING_FOK`; refresh at runtime and never infer from account marketing |
| `order_mode` | 127 | observed bitmask enabling market, limit, stop, stop-limit, SL, TP, and close-by capabilities; each bit must be validated before use |
| `order_gtc_mode` | 0 | `SYMBOL_ORDERS_GTC` |
| `trade_mode` | 4 | `SYMBOL_TRADE_MODE_FULL` at capture time |
| `trade_calc_mode` | 0 | `SYMBOL_CALC_MODE_FOREX`; broker calculation remains authoritative |
| digits / point | 3 / 0.001 | price normalization inputs only |
| tick size/value | 0.001 / USD 0.10 | separately observed profit/loss values both USD 0.10 |
| contract size | 100 XAU | point-in-time demo observation |
| volume min/max/step/limit | 0.01 / 200 / 0.01 / 0 | zero limit means no aggregate limit reported, not unlimited risk permission |
| stops/freeze | 0 / 0 points | dynamic point-in-time fields; never hard-code or bypass broker validation |
| swaps | mode 1; long -523.8; short 0; triple day 3 | account/jurisdiction status may change; refresh before any later stage |

Generic published Pro-account expectations and the account-specific evidence must be stored in separate fields with a discrepancy status. A future real account requires its own read-only probe.

## 21. Phase 0 work products and remaining design contracts

- Risk Policy A is approved under D-0045; candidate deterministic mathematics and vectors are in `specifications/RISK_GOVERNOR_POLICY_A_SPEC.md`.
- Ranked blockers and plain-language actions are in `GATE_0_BLOCKERS_AND_OWNER_ACTIONS.md`.
- The candidate read-only session/VPS plan is `specifications/XAUUSD_SESSIONS_VPS_READONLY_DIAGNOSTIC_PLAN.md`; any runnable artifact requires separate verification and authorization.
- The OpenAI Analyst remains structurally isolated from credentials and execution. Its strict schema, semantic rules, freshness binding, enums, bounded failures/retries, injection corpus, pinned model, latency/cost and audit hashes must be frozen before implementation. Zero unsafe approvals on a finite corpus remains necessary evidence, never universal proof.
- Candidate objective definitions for all five families are in `specifications/SETUP_FAMILIES_OBJECTIVE_SPECIFICATION.md`. Any rule marked unresolved fails closed. Zone B after Zone A invalidation is always a fresh analysis/trade, never averaging, martingale, grid or recovery exposure.
- Candidate Analyst, execution/reconciliation, news and replay/backtest contracts are stored under `phase0/specifications/`; empirical evidence and explicitly marked owner/provider choices remain open. No paid provider may be purchased without owner approval.
