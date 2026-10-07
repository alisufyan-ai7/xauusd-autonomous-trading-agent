# Owner Open-Policy Decision Packet — Gate 0

**Status:** FULL BUNDLE APPROVED under D-0074/D-0075 for specification/testing  
**Scope:** Strategy volume cap, margin reserve, emergency handling, pause/resumption, and operator alerts  
**Trading authorization:** NONE; external Python trading must remain disabled

**Recorded owner selection (2026-08-23):** `V1 + E1 + P1 + A1` for
specification and testing only; automatic closure of unknown exposure `NO`;
primary alert `EMAIL`; secondary alert `TELEGRAM_PUSH`; acknowledgement role
`OWNER_DESIGNATED_ACKNOWLEDGER`. M1 was subsequently approved under D-0075 with
the exact thresholds in section 3. The personal identity-to-role mapping is retained
outside the sanitized repository record.

## 1. How to decide

Select one option in each of Decisions 1–5 and record any changes. The recommended defaults are deliberately conservative and grant the smallest practical future execution authority. They do not authorize an order, demo trading, live trading, or automatic closure. A selected option becomes normative only after an explicit owner decision is added to the append-only Decision Log and its dependent specification/tests pass.

Existing Policy A cash-loss ceilings remain unchanged: USD 25 maximum planned loss per trade at the USD 10,000 reference allocation, USD 50 concurrent planned risk, USD 75 daily loss, USD 150 weekly loss, USD 500 total drawdown, and pause at 3.00 full-risk-equivalent losses. Every new-risk decision must pass **all** applicable caps; a volume or margin limit can only reduce permitted exposure.

## 2. Decision 1 — Strategy volume cap

The observed Phase 0 XAUUSD profile reports a 0.01-lot minimum and step, but this is evidence for one account fingerprint, not a permanent broker rule. The strategy cap must never default to broker maximum.

| Option | Absolute strategy cap | Effect | Assessment |
|---|---:|---|---|
| **V1 — Minimum-grid cap (recommended)** | `0.01 lot` | At most the observed minimum volume. Reject if 0.01 lot exceeds the cash-risk, margin, stop, cost, or stress limit. If the broker minimum/step changes or 0.01 is invalid, fail closed. | Smallest initial authority and simplest reconciliation; some otherwise valid tight-stop setups will be rejected. |
| V2 — Two-grid cap | `0.02 lot` | Allows two minimum steps only when every other deterministic limit passes. | More execution flexibility but doubles the maximum quantity versus V1. Requires stronger slippage and partial-fill evidence. |
| V3 — Five-grid cap | `0.05 lot` | Allows up to five minimum steps when every other limit passes. | Not recommended for the first execution release; tight stops can concentrate quantity and operational error despite the same planned-loss cap. |

**Proposed freeze text for V1:** `strategy_volume_cap = min(0.01 lot, account_validated_cap)` for the first separately approved execution stage. Volume is enumerated from current broker `volume_min` in exact `volume_step`, rounded down, then fully re-priced and re-tested. There is no entitlement to trade the minimum volume.

**Owner selection:** `V1 — APPROVED FOR SPECIFICATION AND TESTING (D-0074)`

## 3. Decision 2 — Margin reserve and stress rule

Both the current-state test and the stressed-state test must pass. `Projected margin level = stressed projected equity / stressed projected used margin × 100`; an account with zero projected used margin is not blocked by an undefined/infinite ratio, but the free-margin rule still applies. Broker calculations must use the current verified symbol/account fingerprint.

| Option | Required after candidate and all counted exposure | Assessment |
|---|---|---|
| **M1 — High reserve (recommended)** | Projected margin level `>= 1,000%` **and** projected free margin `>= 90%` of projected equity, under both current conditions and a provisional `2.0×` incremental-margin stress. Equity also absorbs the frozen adverse spread/slippage/gap/cost stress. | Matches the existing conservative proposal and leaves a large reserve. The provisional multiplier must be replaced or reaffirmed after demo/account-specific stress evidence. |
| M2 — Very high reserve | Margin level `>= 2,000%`; free margin `>= 95%`; same stress method. | Strongest reserve, but may reject most setups and provides little additional value if the 0.01-lot cap is selected. |
| M3 — Moderate reserve | Margin level `>= 500%`; free margin `>= 80%`; same stress method. | Not recommended initially; materially less buffer against broker margin changes and price shocks. |

For every option: missing/stale margin inputs, a failed `order_calc_margin`, currency ambiguity, non-finite values, account-fingerprint change, or an unfrozen equity shock makes the result `UNKNOWN` and rejects new risk. The higher of broker-reported projected margin and the stressed calculation controls. Leverage is never used to relax a cash-loss cap.

**Owner selection:** `M1 — APPROVED FOR SPECIFICATION AND TESTING (D-0075)`

## 4. Decision 3 — Emergency handling beyond quarantine

This decision concerns an unexpected position/order, an unprotected position, or a policy breach observed after exposure exists. An inverse order is never presumed to close exposure, and ownership is never inferred from symbol, comment, magic number, timing, or apparent strategy similarity alone.

| Option | Permitted response | Assessment |
|---|---|---|
| **E1 — Human-only broker action (recommended first release)** | System blocks new risk, preserves evidence, raises a critical alert, and continues read-only reconciliation. It emits no cancel/modify/close request. A human verifies account/object identity in MT5 and chooses any broker action manually. | Least automation authority; avoids turning an ownership error into a second trade. Requires reachable operator coverage. |
| E2 — Uniquely-owned protective action only | Includes E1 for unknown/external/conflicting exposure. A later, separately tested emergency adapter may cancel a uniquely attributed pending remainder or close/reduce a uniquely owned unprotected/over-limit position, never increasing risk. | Potentially faster containment, but requires exact broker request semantics, idempotency, partial-fill handling, independent demo evidence, and separate release authorization. |
| E3 — Automatic close of all unexpected XAUUSD exposure | Close/cancel exposure even when ownership is unknown. | **Reject as an initial policy.** It can act on manual/external exposure, duplicate or reverse exposure, and conflicts with the current no-inferred-ownership invariant. |

Under E1 or E2, `UNKNOWN`, `KNOWN_EXTERNAL`, `CONFLICTING`, account/symbol mismatch, submission uncertainty, or ledger ambiguity remains quarantined until full reconciliation and audited human disposition. Emergency authority cannot create a new entry, widen a stop, increase volume, retry an uncertain close blindly, or re-enable execution.

**Owner selection:** `E1 — APPROVED FOR SPECIFICATION AND TESTING (D-0074)`  
**Explicitly authorize automatic closure of unknown exposure?** `NO — APPROVED (D-0074)`

## 5. Decision 4 — Pause and resumption

| Option | Resumption authority and minimum conditions | Assessment |
|---|---|---|
| **P1 — Human-gated resumption (recommended)** | No risk/safety pause resumes automatically. A designated human may create a new enablement decision only after the trigger-specific hold, complete reconciliation, required diagnostics, alert acknowledgement, and a fresh preflight all pass. The old intent remains expired/blocked. | Clearest accountability and safest first release. |
| P2 — Boundary auto-reset for daily/weekly limits | Daily/weekly limit states may clear automatically at a verified boundary; incident, quarantine, drawdown, and 3R pauses remain human-gated. | Less operator load, but a clock/boundary/ledger defect could restore risk authority without review. Not recommended initially. |
| P3 — Health-check auto-resumption | A service may resume after a quiet period and automated health checks. | Not recommended for Policy A loss, ownership, reconciliation, or incident pauses. Suitable only for later, non-risk market-condition blocks under separately frozen rules. |

**Recommended P1 trigger matrix:**

| Trigger | Minimum hold | Additional conditions before a human can authorize a fresh enablement |
|---|---|---|
| Daily USD 75 limit | Through the next verified trading-day boundary | Cash-flow-normalized boundary snapshot; ledger/account/owned exposure reconcile; cause reviewed; weekly/drawdown limits remain clear. |
| Weekly USD 150 limit | Through the next verified trading-week boundary | Same controls using the frozen week boundary; drawdown remains clear. |
| 3.00 full-risk-equivalent losses | At least 24 hours **and** through one complete broker trading session after the triggering completion | All instances/costs reconciled; no unknown residual; loss cluster reviewed; no policy/model/config change is made merely to erase the pause. |
| USD 500 total drawdown | Indefinite | Owner reauthorization through a new recorded policy decision after root-cause review and fresh validation. It cannot be reset by deposit, restart, redeploy, or boundary rollover. |
| Quarantine or incident | Indefinite | Root cause documented; state and immutable ledger fully reconciled; corrective tests pass; designated operator acknowledges. Corruption or unresolved ownership blocks resumption. |
| Manual kill switch | Until the same or higher authority deliberately re-enables | Fresh preflight and reconciliation; no restart or deployment may clear the switch. |

Any resumption creates a new authorization epoch and requires a new proposal/intent. It cannot revive or submit a pre-pause approval. If any prerequisite is missing or stale, remain paused.

**Owner selection:** `P1 — APPROVED FOR SPECIFICATION AND TESTING (D-0074)`

## 6. Decision 5 — Operator alert expectations

| Option | Delivery and acknowledgement | Assessment |
|---|---|---|
| **A1 — Dual-path critical alerts (recommended)** | Every alert is written immediately to the append-only local audit log. Critical alerts additionally use two independently configured off-host paths where feasible (for example email plus push/SMS), repeat every 5 minutes until acknowledged, and require acknowledgement within 15 minutes during an execution window. Warning alerts require acknowledgement within 4 hours; informational events enter a daily digest. | Strongest practical detection while retaining a durable local record. Requires maintained contacts and channel-health tests. |
| A2 — One off-host channel | Local audit log plus one remote channel; critical acknowledgement within 30 minutes. | Simpler and cheaper, but a single provider/account/network failure can hide the incident. |
| A3 — Local console/log only | No off-host alert requirement. | Not recommended for any execution-capable stage; unsuitable when the operator is not continuously watching the VPS. |

**Recommended A1 severity contract:**

| Severity | Examples | System behavior |
|---|---|---|
| `CRITICAL` | Unknown/conflicting exposure; owned exposure lacks verified protection; account/symbol fingerprint change; submission uncertainty; ledger/hash corruption; risk/drawdown breach; emergency action failure; execution enabled outside an authorized epoch | Immediate fail-closed state; local plus off-host alert; repeat until acknowledgement; no alert-delivery failure may restore risk authority. |
| `WARNING` | Repeated connection/reconciliation failure with no observed exposure; stale provider/data; clock drift beyond threshold; margin/news/session state unknown; one alert channel unhealthy | Block affected new risk; alert and record; escalate to `CRITICAL` if duration/count threshold or exposure uncertainty is reached. |
| `INFO` | Clean startup/reconciliation; authorized configuration/version change; pause acknowledgement; verified manual resumption; normal shutdown | Append-only record and digest; no paging by default. |

Required alert content is minimized: UTC timestamp, environment, severity, typed reason code, state/authorization epoch, affected component, first/last occurrence, retry count, acknowledgement identity/time, and hashes or pseudonymous object references needed for reconciliation. Do not put credentials, account numbers, identity documents, raw broker exports, or unnecessary position/account values in alert bodies.

Before any execution-capable stage, test channel delivery, retry/deduplication, acknowledgement, escalation, outage behavior, contact rotation, and the invariant that alert failure cannot enable or increase risk. Quiet hours never suppress `CRITICAL` alerts during an authorized execution window.

**Owner selection:** `A1 — APPROVED FOR SPECIFICATION AND TESTING (D-0074)`  
**Primary off-host channel:** `EMAIL`  
**Secondary off-host channel:** `TELEGRAM_PUSH`  
**Designated acknowledgement role/person:** `OWNER_DESIGNATED_ACKNOWLEDGER`

## 7. Recommended conservative bundle

For a first separately approved execution release, the internally consistent conservative bundle remains:

`V1 + M1 + E1 + P1 + A1`

This means a 0.01-lot absolute cap, high current-and-stressed margin reserve, no automated broker action in emergencies, human-gated resumption, and dual-path critical alerting. The bundle intentionally prefers missed trades and operator intervention over automated recovery. It does not resolve the separate dependencies for costs/gap/slippage calibration, account-specific sessions, broker-request semantics, attribution, testing, or execution authorization.

Approved bundle: `V1 + M1 + E1 + P1 + A1` for specification and testing only.
It authorizes no implementation, broker request, demo/live trading, automatic
unknown-exposure closure, or external-Python enablement.

## 8. Owner response block

Copy and complete:

```text
I select:
- Volume cap: V__
- Margin reserve: M__
- Emergency handling: E__
- Pause/resumption: P__
- Operator alerts: A__
- Automatic closure of unknown exposure: NO / separately specified YES
- Primary alert channel:
- Secondary alert channel:
- Designated acknowledgement role/person:
- Modifications or conditions:

This decision is for specification and testing only. It does not authorize demo/live trading or enable external Python trading.
```

## 9. Required work after owner selection

1. Append the exact selection and scope to the Decision Log without rewriting history.
2. Incorporate the selected constants, state transitions, reason codes, authority roles, acknowledgement records, and time boundaries into the Risk Governor and execution specifications.
3. Add exact-boundary, stale-state, restart, duplicate-event, channel-failure, missing-acknowledgement, margin-shock, and emergency-path test vectors.
4. Obtain account-specific diagnostic evidence for margin and broker request semantics relevant to the selected policy.
5. Keep external Python trading disabled until all Gate 0 evidence is complete and the owner issues a separate execution-stage authorization.

## 10. Existing normative foundations

- `OWNER_RISK_DECISION_SHEET.md` — Policy A monetary limits and prior conservative margin/tiny-live proposals.
- `specifications/RISK_GOVERNOR_POLICY_A_SPEC.md` — fail-closed sizing, margin dependency, loss pauses, and unknown-exposure invariants.
- `specifications/EXECUTION_RECONCILIATION_IDEMPOTENCY_SPEC.md` — unique ownership, quarantine, restart behavior, and separately audited recovery.
- `PHASE_0_SPECIFICATION.md` — human kill switch, mandatory protection, incident logging, and staged evidence requirements.
