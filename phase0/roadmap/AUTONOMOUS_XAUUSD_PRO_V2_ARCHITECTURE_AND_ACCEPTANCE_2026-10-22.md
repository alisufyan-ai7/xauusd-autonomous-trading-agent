# Autonomous XAUUSD Pro — v2 architecture and acceptance specification

**Version:** DRAFT `v2.0-preapproval-1`
**Prepared:** 2026-10-22 Asia/Karachi (2026-10-21 UTC).
**Authority:** RESEARCH / SPECIFICATION ONLY; not accepted to implement, merge into production, deploy to VPS, change MT5 settings, amend risk policy, activate DEMO orders, fund LIVE, or trade real money.
**Repository baseline:** freshly merged `main=51a7f7de395767a9ae1f9904f752bd74b3cdc010` (PR30 merge).
**Owner source:** [ADR-2026-10-21-001](../decisions/ADR-2026-10-21-001-AUTONOMOUS-PRO-TRADING-VISION.md), with [decision-memory protocol](PROJECT_DECISION_MEMORY_PROTOCOL_2026-10-21.md).
**Review status:** Every rule labelled PROPOSED below is a candidate for future independent review. Existing normative specs and failure evidence remain in effect.

## 1. Product mission and separable admission states

Build a VPS-resident, autonomous gold analyst and trader that ingests broker-authoritative Exness MT5 data, understands structure over W1/D1/H4/H1/M15/M5/M1, generates BUY/SELL/NO_TRADE, uses bounded AI to evaluate candidates, sizes only through a deterministic Risk Governor, sends DEMO orders only after separately approved activation, manages known positions, and records every decision for research and safe change control.

**Hard owner constraints:** Exness **Pro only** for DEMO and any eventual LIVE; never Standard Cent or `XAUUSDc`; single `XAUUSD` symbol initially; no screenshots or per-trade manual side selection as the final product workflow. LIVE balance above about USD300 is only an illustrative owner preference, not an admitted account or order. No automatic login/profile selection, account migration, secret handling, funding or LIVE crossover.

| State | Meaning | Permitted broker behavior |
|---|---|---|
| `SPEC_ONLY` | Current v2 draft and tests not admitted | NONE |
| `OFFLINE_REPLAY` | Registered development/held-out historical evaluation | NONE |
| `SHADOW_EXECUTION_DISABLED` | Real read-only broker data; decisions and *simulated* trades | `initialize`, read-only discovery and `shutdown` only; no `order_check`/`order_send` |
| `SINGLE_ATTENDED_DEMO_CANARY` | Existing separate sealed S2 when exact APC approved | At most one owner-bound DEMO entry and one known-position attended close; stop if any gate fails |
| `AUTONOMOUS_DEMO_LIFECYCLE` | New sealed, isolated release after full DEMO-ADMIT and owner activation | Only bounded, known, broker-reconciled Pro DEMO entries/managed exits; never an unknown close |
| `PRO_LIVE_CANDIDATE` | Source, event, replay, long shadow, demo results and account-specific risk reviewed | NO LIVE orders |
| `PRO_LIVE_AUTHORIZED` | Future independent accepted evidence and exact owner-granted release/account/window | Controlled tiny LIVE only; no auto promotion from DEMO or 48 hours |

**Non-equivalence:** a single demo canary is not autonomous DEMO acceptance; 48 hours operation is not a profitable-strategy proof; neither DEMO nor AI performance substitutes for LIVE admission.

## 2. Dependency map and component ownership

```text
Exness Pro MT5 terminal (locked, admitted profile) + authorized official event sources
   -> read-only market and broker observer (UTC / provenance / freshness / gap checks)
   -> deterministic multi-timeframe market context and regime classifier
   -> setup registry and ONE versioned champion proposal (plus shadow challengers)
   -> bounded, tool-free AI Analyst (accept NO_TRADE / reject or annotate only)
   -> Event Guard + session + shock / spreads / trading-hours admission
   -> authoritative deterministic Risk Governor and accountable cash-flow ledger
   -> durable intent + single-writer lease + idempotent broker submission fence
   -> broker-bound order adapter with mandatory stop and exact identity preflight
   -> known-position lifecycle management / reconciliation / audit
   -> VPS watchdog + alerts + immutable evidence
   -> offline research/challenger evaluator (NO execution mutation)
```

Each boundary uses typed data structures, immutable decision and snapshot IDs, UTC timestamps, configuration/model/feature versions and hash-linked audit receipts. No probabilistic model or research workflow receives broker order tooling or controls authorization. A `NO_TRADE` is a fully legitimate output, not a failure to be retried until a trade appears.

Current `src/xauusd_agent/runtime.py`/`host.py` intentionally compose disabled Analyst/Event Guard/session and a `NullExecutionRecord`. The general DEMO adapter deliberately blocks without fully admitted USD risk; PR24/S2 is one attended lifecycle. **No current code base contains the full v2 autonomous composition described here.** Any future implementation is a new release and is not a configuration flip of PCR3 or PR29.

## 3. Market intelligence: causal multi-timeframe data

| Level | Proposed role | Candidate features (research only until test admission) |
|---|---|---|
| W1 + D1 | Strategic regime | Prior-week/day highs/lows, multi-week range, structure, session-open and major gap context |
| H4 | Regime and trend filter | Confirmed swing direction, volatility normalization, EMA20/EMA50, ADX, opposing major zones |
| H1 | Tradable structural zones | Confirmed HH/HL/LH/LL, break/retest, pullback location, invalidation level |
| M15 | Main closed-candle trigger | Predicates of selected frozen setup family, confirmation and missed-entry detection |
| M5 | Entry microtiming, only if validated | Spread-aware refinement, recent rejection/break, avoid chasing |
| M1 and live ticks | Execution health + ongoing position awareness | Fresh bid/ask, tick size/volume, quote age, widening spread, abnormal short horizon jump |

Frozen research specification [P0-SETUPS-001](../specifications/SETUP_FAMILIES_OBJECTIVE_SPECIFICATION.md) currently requires minimum **300 complete H4, 500 H1, 1,000 M15** bars and uses H4/H1/M15. Additional W1/D1/M5/M1 coverage minimum, timescale, lookback, admissible gaps and acceptance fixtures must be **prospectively specified and tested**; they are not silently inferred from existing H4/H1/M15 warmups.

All features are computed only from data available at `decision_time` with measured broker/receipt timestamps, UTC/DST mapping, explicitly versioned vendor/session gaps and account/symbol metadata. Future/unfinished bar data, duplicated or out-of-sequence timestamps, stale ticks, unexplained session boundaries, unsupported symbol specification or conflicting data source => `UNKNOWN/NO_TRADE`, with a reason and alert where severe. Historical replay and VPS use the *same feature code*; no future close, revised macro result or favorable intrabar sequencing can leak into decisions.

**Data inputs:** Existing approved Dukascopy historic corpus may support offline research within licensed scope; fresh eligible Exness Pro DEMO bid/ask/tick/cost/cash-flow metadata are authoritative for actual broker decisions. News/events from approved BLS, BEA, Fed and Census source-health connectors; model-generated/internet-text dates are never the session or news-lock authority. Verify provider terms for any new machine consumption/AI transmission. Source errors and calendar contradictions block affected new entries.

## 4. Strategy engine and objective portfolio selection

Frozen owner-approved research baseline contains **TPB**, **BRT**, **FBR**, **RSR**, **MOC**. Candidate **TPB (Trend Pullback)** is a first review recommendation **only**, not a selected or proven profitable winner. All five should remain individually versioned; no new 'all strategies BUY' consensus mechanism. PR29's EMA20/EMA50 H1 plus M15 breakout remains an *experimental*, unadmitted execution-disabled candidate with GitHub Actions failures of unknown cause.

**Proposed initial rule:** one *independently accepted* champion family may produce broker-eligible proposals; all other variants run only in offline or execution-disabled challenger mode. The selector detects an admitted regime, evaluates mutually exclusive candidate states, applies frozen priority/conflict rules and assigns one setup key. Lack of qualifying regime or ambiguity returns `NO_TRADE`. No averaging, grid, loss recovery, churning, martingale or switching to a less-tested strategy to make up a loss.

**Evidence required before selecting champion:** prospectively registered hypothesis, code/data/config hashes, cost/source assumptions, causal completed-bar replay, chronological development and untouched OOS holdout, multiple-testing disclosure, walk-forward and stress tests, reward/risk after broker economics, no critical rule violations and transparent insufficient-evidence status. Existing [registered replay criteria](../specifications/REPLAY_BACKTEST_METHODOLOGY_AND_ACCEPTANCE.md) remain unwaived; an offline trade plot or profit factor alone does not promote a strategy.

## 5. AI Analyst, news research and controlled learning

**Advisory authority:** use the accepted [minimized Analyst contract](../specifications/OPENAI_ANALYST_MINIMIZED_CONTRACT.md) and production [system prompt](../validation/analyst_runtime/PRODUCTION_ANALYST_SYSTEM_PROMPT_V1.txt), unless a versioned successor is explicitly accepted. The local model receives only schema-authorized minimal derived fields, cited evidence IDs and bounded lifetime. `store=false`, no tools, no account identifiers, no credentials or raw secrets; model/config/prompt hash pinned after benchmark and owner approval. Source health, exact echo, finite Decimal-price semantics, schema and stale-response checks are deterministic. Reject/NO_TRADE on refusal, timeout, unsupported quote, hallucinated level or prompt injection.

**Function split:** Researcher may browse permitted public research and propose hypotheses, identify market-event implications and explain losses, but NEVER communicates executable broker commands or changes running settings. Analyst receives frozen local snapshot and may only reject/annotate a deterministic candidate. Risk Governor/Execution controller verifies all numeric limits. OpenAI calls outside previously approved benchmark scope require **separate owner approval**, including privacy/cost budget.

**Learning process:**
1. Capture every cycle, including `NO_TRADE`, proposals, model verdict, setup version, expected and realized costs, broker retcodes, missed fills, exit causes, shock/news and incident flags.
2. Perform per-trade attribution: ordinary planned-loss outcome vs strategy rule mismatch vs cost/slippage vs data fault vs regime drift vs lifecycle defect; avoid treating a few consecutive losses as proof of a regime shift.
3. AI proposes challenger changes (prompts, feature sets, parameter/strategy variants) with immutable trial registry and prospective holdout; each challenger runs offline + SHADOW side by side.
4. Independent quality/economic/fault gates and owner-approved signed promotion move one release through DEMO; LIVE promotion **never automatic**. Immediate defensive `NO_TRADE` on drift or incident is allowed under accepted safety policy, but not silent self-training or risk widening.

## 6. Risk Governor — policy is authoritative and versioned

**Current normative Policy A (NOT changed by this v2 draft):** allocation USD10,000 upper bound; per-trade planned risk <=`floor_cent(0.0025 * min(current_balance,current_equity,approved_allocation))`; concurrent loss <=USD50, daily adjusted loss <=USD75, weekly <=USD150, max strategy drawdown <=USD500, full-risk-equivalent losing streak pause >=3.0; 0.01-lot maximum V1; M1 projected current and 2x stress margin level >=1000% and free margin >=90% equity; valid broker-normalized protective stop. Any unknown monetary cost, stop math, session, identity, cash-flow baseline, margin reserve, fills or exposure must reject or quarantine.

`L_plan = broker-calculated price loss from worst admitted executable entry to validated adverse SL + source-backed commission + swap + adverse slippage + gap reserve`. A SL is not a guaranteed realized floor; recalculate broker costs, normalized lot/stop and margin at execution. No missing-to-zero data, no confidence multiplier and no 'stop present == cash risk PASS'. Broker min XAUUSD on observed Pro DEMO was 0.01 lot / 100oz standard lot = 1oz exposure; future Pro LIVE symbols/fees/margin/stop levels still require fresh independent account-specific evidence.

**Proposed policy comparison, NOT owner-approved:** keep A unchanged; optionally research B (lower-balance scaled *higher* fractional cap with absolute daily/week/drawdown circuit breaker); optionally C (fixed cash-risk floor with proportional equity scaling). Alternative B/C must be separately risk-modelled with worst-case minimum-lot/structural-stop feasibility at USD300/500/1000/10000, independent source-backed costs, loss-of-equity probabilities under drawdown stress, broker minimum margin and owner-selected explicit hard limits. If the min trade does not fit, `NO_TRADE`—never Standard Cent and never remove SL or hide position loss. No current numeric replacement selected or authorized.

**Important illustration, not market prediction:** at 0.01 lot on a 100oz Pro XAUUSD contract, 1.0oz exposure gives USD1 price P/L per USD1/oz move. The old S2 **engineering-only** adverse-cost buffers total USD9.50 at 0.01 lot (USD0.50/oz slip+USD2/oz gap+USD5 commission+USD2 swap), not admitted general LIVE Pro costs. Under present 0.25% rule, USD300 eligible equity caps planned loss at USD0.75 and cannot accommodate those illustrative costs, let alone an effective structural stop. Proposed fraction comparisons: 1%=>USD3, 2%=>USD6, 5%=>USD15 at USD300. These are **exposure examples, not risk choices or permission to trade**.

## 7. Known-position management — proposed v2 successor rules

**Lifecycle** (proposed): `KILLED -> PREARMED -> ARMED -> ADMISSION_CHECK -> INTENT_DURABLE -> ENTRY_IN_FLIGHT -> KNOWN_POSITION -> EXIT_INTENT -> EXIT_IN_FLIGHT -> FLAT_RECONCILED -> KILLED`. Failure/unknown at any broker write or unowned ticket => `QUARANTINED`, no repeat submit, no adoption or auto close of unknown exposure; alert human. Human emergency E1 and human-only rearm P1 remain as accepted.

**Entry:** exact DEMO fingerprint/server/company/mode/currency/XAUUSD, fresh symbol/quote, zero unknown exposure, verified news/session/shock/calendar, active lease, certified current and stress risk, one ledgered intent, broker `order_check` then at most one `order_send` under specific granted mode, broker-authoritative order/deal/position reconciliation. Failure after send is ambiguous until broker-history reconciliation; never blindly resubmit. Exit/stop modifications use similarly fenced intent and reconciliation.

**Exit policy candidates** (NOT v1-released):
- `INITIAL_STOP_AND_FINAL_TARGET`: broker-protected fixed stop and frozen final target, time/session exit if independently defined.
- `KNOWN_EARLY_EXIT`: close entire **known** position when original structural thesis invalidation is objectively confirmed and broker/identity/order lifecycle is verified. No lookahead and no open-ended model discretionary close.
- `BREAK_EVEN`: tighten SL toward effective net BE *only* after qualifying favorable excursion/confirmed structure and transaction costs; candidate never removes broker protective stop and only reduces remaining risk.
- `TRAILING`: tighten stop along completed structural swing/ATR-defined rule with minimum confirmation/tick/freeze/hysteresis; do not tighten prematurely or oscillate on M1 noise.
- `TP_REFINEMENT`: prospective versioned target logic may lock profit or elect early total close. Never move target farther merely to avoid recording a loss; no position size increase.

**Invariant:** stop never widens and no known-position planned loss, volume, or exposure increases from an AI management decision. Stop/TP modification is idempotent, retcode-checked and broker-reconciled before declaring success. At min 0.01 lot / 0.01 step, a 0.005-lot partial close is invalid; total known-position close is the default until verified broker grid permits otherwise. Market gap, stop slippage and server outage remain residual risks. Emergency unknown-exposure automatic close is prohibited.

## 8. VPS/MT5 runtime, isolation and operations

Use separate Windows Python3.12-compatible isolated release directory, reproducible wheels/lockfile, installer/manifest hashes, one exclusive agent writer, immutable schema and durable SQLite journal/lease/outbox plus broker history reconciliation. A sealed DEMO executor must be physically and logically unable to select a LIVE profile, and revalidate exact admitted *Pro DEMO* identity at every order; switch/login to any unadmitted account disables and quarantines. Do not store credentials/number/tickets or private evidence in GitHub.

Preserve installed `XAUUSD Execution-Disabled Shadow` PCR3 task, other VPS schedulers and previously staged S2. New autonomous runtime is separately installed under explicit owner scope; no unapproved parallel writer or duplicate broker client. State after crash, terminal restart, MT5 update, Windows reboot, missing tick, partial fills, journal disk-full, source outage, login change or alert failure: stop new risk, reconcile known position, alert and require a reviewed restart where necessary. Do not let a watchdog retry a broker order. Testing must cover forced process deaths, partial ACK, order retcode unknown, missing ticket, network partitions, duplicate scheduler execution, DST/holiday and end-of-week.

Realtime VPS monitor owns heartbeats, alert routing, position/SL state, risk limits, quote quality, broker costs, delayed order acknowledgements, events/news and disconnect detection. Audit includes exact config/model/strategy release IDs and sanitized immutable outputs. Existing A1 email+Telegram alert channel may be reused only after current release-specific delivery/ack verification. ChatGPT does not provide persistent VPS control or direct monitoring itself.

## 9. Prospective DEMO 48-hour operational trial

**Start point:** 48h clock only after separately approved, byte-exact **autonomous DEMO** release is installed and owner-observed exact Pro fingerprint/flat exposure/API setting/stop calculation/Event Guard/sessions/rollback/watchdog are confirmed. 48 wall-clock hours may contain closed markets; record actual *eligible market hours*, eligible cycles, reject reasons, executed trades and observation gaps separately. Do not force trades to fill sample size. A 48h supervised **one-order S2** canary cannot be mistaken for 48h autonomous monitoring.

**Hard trial conditions, proposed:** zero wrong-account orders, zero unowned/duplicate orders, zero missing protective stops on admitted positions, zero risk-governor bypasses, zero unmanaged unknown exposure, zero journal integrity faults, owner-verifiable watchdog/alert path, broker history/orders/positions reconciled for every action, confirmed shutdown/rollback. Exits including broker SL/TP/scheduled closures must be witnessed; actual spread, latency, commission, swap, gap and net P/L reported in USD. Faults cause immediate new-risk stop and open incident, not a quiet PASS.

**Result classes:** `OPERATIONAL_PASS` only if the entire predetermined 48h and all critical checks meet admission and meaningful eligible observation occurs; `OPERATIONAL_FAIL_CLOSED` on critical breach; `INSUFFICIENT_TRADING_EVIDENCE` when safe but too few trades/regimes to assess expectancy; `NOT_STARTED/INTERRUPTED` when startup/session evidence missing. Profitability is **never** accepted solely because 48 hours elapsed; any replay/shadow/empirical-cost/Gate0 LIVE dependency remains independent.

## 10. LIVE is a distinct optional admission track

Owner desires a tiny Pro LIVE trial after a clean DEMO operational review, but `LIVE` is a separate mode with **zero currently admitted LIVE account identity** and no trading authority. Real-money threshold, budget, Pro margin/leverage/entity-specific specifications, data costs, emergency recovery and full signed LIVE release must be separately tested and explicitly accepted. No shared profile, stored LIVE creds in DEMO, aliasing account modes, auto-arming, same-release DEMO→LIVE toggle, or promotion solely from an AI forecast.

The previously accepted [Accelerated Production Candidate Plan](ACCELERATED_PRODUCTION_CANDIDATE_PLAN_2026-10-05.md) preserves Gate 0 R4 failure, G0-07 R34/R35 failures, unresolved R5/G0-08/G0-12/G0-14 and formal full-month shadow prerequisites pre-LIVE. A future owner-requested alternative timeline is a **proposal to amend sequencing only**, not a passed risk gate or retroactive evidence correction. Until a separately accepted versioned governance decision, LIVE remains disabled.

## 11. Test strategy and release evidence (mandatory before runtime activation)

| Stage | Proof required | Admission |
|---|---|---|
| Spec review | Exact owner option choices, source dependencies, version/hash freeze, unresolved-fields register | no code changes except separately approved |
| Offline component tests | Deterministic completed-bar fidelity, symmetric BUY/SELL, risk Decimal boundary, news/session/source locks, no unauthorized MT5 import | all critical tests pass at exact SHA |
| Replay and strategy admission | Licensed chrono-split registered trials, realistic bid/ask fills and costs, independent OOS and stress; record all failed variants | strategy champion must earn evidence, otherwise `NO_TRADE` |
| Analyst integration | Exact schema/echo, no-tools/store=false/minimization, timeouts/injections/no hallucinated prices, budget | only separately permitted OpenAI calls |
| Adversarial integrated tests | Process crash on each journal commit, missing order response, unknown exposure, wrong account, margin/stops gap, clock/session breach, duplicate task, disk-full, lost alerts | every critical failure causes no new risk, clear incidents |
| Native Windows/read-only preflight | Python/MT5 version pin, exact DEMO fingerprint, projected margin/stops, sealed release and rollback | separately owner-authorized read-only run |
| Bounded broker trial | Existing supervised S2 lifecycle if separately approved; clean open/known close, protective SL, reconcile and KILLED | no assumption this proves autonomous runtime |
| Autonomous DEMO activation | New release sealed and exact activation packet owner-approved, 48h monitor and watchdog already validated | no LIVE authority |
| LIVE proposal | Existing frozen empirical/replay/shadow/demo requirements + independent Pro LIVE risk/rights and exact signature | never automatic |

Produce machine-readable test receipts with immutable requirement IDs, expected output and observed result; **DO NOT** mark `PASS` from a proposal. GitHub PR29's current CI status is **FAILED/UNKNOWN CAUSE** and cannot be counted as passed source validation.

## 12. Interfaces and version-pinned evidence

Each `MarketSnapshot` must include `decision_time_utc`, source receipts, completed H1/H4/M15 bars plus optional W1/D1/M5/M1 context with explicitly qualified readiness, quote and symbol metadata (internal only), feature version, config hash and source health.

`SetupCandidate`: strategy version, setup key, LONG/SHORT, cause evidence IDs, valid entry envelope, adverse structural stop, target/time exit, TTL and deterministic invalidation reason; no broker authority.

`AnalystAssessment`: strict `NO_TRADE/PROPOSE_TRADE` with echoed IDs, evidence citations and semantic validation; no size/account/order fields.

`RiskDecision`: immutable accepted policy hash, broker current/stressed calculations, worst admissible entry/stop/cash L-plan and cap, normalized lot, period loss/available budget, account snapshot epoch, `DENY/PASS` and reason.

`ExecutionIntent/Receipt`: single writer + lease, monotonically increasing journal revision, deterministic order idempotency identity, exact broker request and unredacted private broker ticket OUTSIDE GitHub, confirmed stop state and reconciliation.

`PositionReview`: exact-known position identity, source/quote freshness, original thesis and invalidation, allowed management action (`HOLD`, `TIGHTEN_STOP`, `CLOSE_KNOWN`, `QUARANTINE`), action fence and broker acknowledgement.

`LearningReport`: immutable fill/cost/result, hypothesis and strategy/model versions, reasons/errors/regime/features, future challenger experiment key, not a direct live config write.

## 13. Open owner decisions and *explicit* next acceptance

**No one has selected any new numerical Policy A replacement or offered capital-account authorization.** Owner must review: (A) champion strategy/family and whether v1 frozen strategy logic stays exact initially; (B) active management version/exit triggers; (C) account-aware risk ceiling alternatives and daily/weekly/drawdown budget in real USD including a >=USD300 Pro account impossibility check; (D) AI usage authority, privacy/cost and precise prompt/model; (E) DEMO activation prerequisites and monitoring report; (F) any proposal to revise original LIVE prerequisites. Keep source-code implementation separate from these decisions.

**Next recommended deliverable after review:** accepted/prospectively frozen V2 functional contracts + machine acceptance matrix → isolated code PRs with no execution ability → offline/adversarial/native Windows read-only validations → a separately approved exact release for supervised DEMO/continuous DEMO. This spec does not approve source merges, OS changes or broker actions.

**Historical records are immutable.** Decisions and failure corrections are append-only under `phase0/DECISION_LOG.md` and `phase0/decisions/ADR-*`. Open owner requests, uncertainty, and source mismatch always appear in read-first `CURRENT_PROJECT_STATE` and accompanying JSON.
