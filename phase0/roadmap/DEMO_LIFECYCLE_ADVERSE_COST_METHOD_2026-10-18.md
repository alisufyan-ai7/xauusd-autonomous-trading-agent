# DEMO-ADMIT adverse-cost method — prospective registration, not admission

**Scope:** `DEMO_LIFECYCLE_ONLY` (0.01-lot XAUUSD, Exness MT5 DEMO); **status:** `REGISTERED_METHOD_ONLY`.  
**Frozen source base:** `ccaa8338aecee8bd3afbc358644410dff6c512e5`.  
**Normative machine-readable preregistration:** `DEMO_LIFECYCLE_COST_PREREGISTRATION_2026-10-18.json`.

## 1. Authority and precedent

Registration must precede source evidence acquisition and numeric selection. The read-only account capture requires its own owner approval and must run later than this GitHub commit. No demo order, MT5 execution enablement, task/service edit, order check or margin calculation is authorized here. No data were newly acquired and no numeric calibration is admitted by this document.

Preserve Dukascopy R1/R2/R3 `FAIL_CLOSED`, R4 preregistration and earlier nonstationarity. Earlier 24-hour Exness quote observations (`0.182` typical, `0.420` peak spread) are **historical diagnostic context only**, not accepted future calibration constants or evidence of execution slippage. Existing PCR-3 `QUARANTINED` observations remain as recorded.

## 2. Prospective observation and provenance

Use a new *isolated*, read-only collector for this exact account fingerprint, broker/server/currency, MT5 DEMO mode and `XAUUSD`. Require a fresh identity/zero-position/zero-order/disabled-trade-API check both before and after collection. Keep the sealed PCR-3 task and shared worktree untouched.

Read-only API allow-list for the *proposed collector*: `terminal_info`, `account_info`, `symbol_info`, `symbol_info_tick`, `copy_ticks_range`, `positions_get`, `orders_get`, `last_error`, `initialize`, `shutdown`. `order_send`, `order_check`, `order_calc_margin`, `order_calc_profit` and all trade mutations are excluded from this capture until separately reviewed. No login IDs or credentials in reports or GitHub. A future collector must be statically audited against this allow-list before use.

Capture begins only after this method is committed *and* the owner approves the exact read-only script. Target at least five distinct market days, three observed rollover boundaries, one observed weekly reopening and eligible ASIA/LONDON/LONDON_NY periods. Nominal quote polling at most every five seconds (plus available MT5 ticks with their true UTC event time); source tick and observer timestamps are separately retained. Record and classify gaps rather than interpolating. If required windows are missing or data/clock/MT5 status is unreliable, status remains `NOT_ADMITTED` and collection must extend under a new explicit record.

Produce privately retained immutable source bytes, raw source SHA-256, collector script SHA-256, environment/version manifest SHA-256, collection boundary times, row counts, coverage, stale/gap statistics, and a sanitized GitHub summary with independent checksum verification. Do not publish sensitive raw evidence. Preserve exact source hashes, provenance chain and evaluator version before computing any calibration object.

## 3. Required separately evidenced components

Use exact Decimal USD amounts per 0.01-lot equivalent; convert XAUUSD price moves using current account-specific tick size/value-loss and contract data, requiring independent numerical consistency checks. For each side evaluate the worse BUY/SELL outcome.

| Component | Prospective conservative estimator | Fail-closed condition |
| --- | --- | --- |
| Spread | Maximum observed eligible `ask-bid` converted to 0.01-lot USD, plus a fresh runtime spread gate | Any stale, inverted or undocumented bid/ask; runtime exceeds calibrated bound |
| Latency/slippage proxy | Maximum adverse directional quote movement at predeclared 1-second, 5-second and 30-second horizons; retain all three | Missing enough timestamps/coverage; never call this observed execution slippage |
| Quote gap | Maximum adverse consecutive executable-side quote jump, separately tagging closed-market/rollover gaps; classify missing periods | Missing boundary evidence or unbounded/unknown stop-fill behavior |
| Commission | Verified **account-specific** round-trip USD schedule with document/source hash (including an evidenced zero if truly applicable) | Undocumented fee or assumed zero |
| Swap/holding | Verified account-specific adverse holding-window/overnight reserve, including day-of-week effects and adverse uncertainty | Unknown swap, rollover applicability or assumed zero |
| USD conversion | Verified tick size/value-loss/contract/account-currency relationship, including direction/asymmetry | Inconsistent/missing metadata or unsupported conversion |

The conservative current envelope sums the separately observed/documented maxima; components need not occur simultaneously. In the stress envelope use at least twice the current aggregate and any greater predeclared scenario-specific component total, rounded *up* to the next USD cent with `Decimal`. This 2× uplift is a **preregistered stress convention, not evidence of a market upper bound**. Missing values remain missing; neither `0` nor stale data is substituted. Numbers cannot be chosen until independently verified source records exist.

Use the two exact derived USD strings in `DemoRiskCalibration(current_adverse_cost=Decimal(...), stressed_adverse_cost=Decimal(...))`. Independently re-create the **five-field, sorted/minified JSON SHA-256** from `risk_binding.py`: `calibration_id`, `source_sha256`, `scope`, `current_adverse_cost`, `stressed_adverse_cost`. Verify the raw source hash separately; merely placing a syntactically valid source hash in the object is insufficient. Match the exact object digest in `DemoPolicy.risk_calibration_sha256` and in the admission record.

## 4. Trading-safety applicability

The scalar calibration amounts are *risk reserves* for the existing M1 margin calculation; they cannot prove actual execution fills, profitability, broker stop-fill bounds or complete Policy A per-trade loss. Entry/stop quote semantics, commission/swap, gap/slippage and runtime price changes must not be silently double-counted in an asserted exact loss formula. A separately reviewed loss-to-stop implementation must cover the frozen `L_plan` and USD 25 maximum at USD 10k, concurrent/period loss and protected-stop semantics before any bounded demo order can be admitted.

An observed spread exceedance, stale tick, data outage, unknown session/news/shock state, account drift or unexpected exposure must fail closed *at runtime*. Weekly reopening/rollover coverage does not authorize trading during uncertain windows. `max_deviation_points` is not a guaranteed slippage ceiling for market execution.

## 5. Required prospective acceptance packet

1. Commit and independently review this protocol **before** collecting new evidence; separate capture authorization.
2. Confirm a static allow-listed collector and synthetic tests, then run an *isolated* read-only VPS capture without interfering with the execution-disabled shadow service.
3. Verify source/manifest hashes, identity, zero exposure, timestamp and coverage controls.
4. Attach exact component breakdowns and source-backed fee/swap/conversion proofs; reject any unsupported zero or missing component.
5. Run an independent Decimal calculator/verifier against the byte-exact source and record object hash.
6. Resolve the implementation gaps recorded in `DEMO_ADMIT_RISK_GAP_REVIEW_2026-10-18.md` with separate exact-SHA implementation review and offline tests.
7. Admit or reject explicitly through a versioned report; only after an admission PASS may a successor demo artifact be reviewed for *execution-off* staging.

There is **no automatic admission**, no retroactive proof of production calibration, no Gate-4 full-month credit, no APC-DEMO permit or activation authority.
