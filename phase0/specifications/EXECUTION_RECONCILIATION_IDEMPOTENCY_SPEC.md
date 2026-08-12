# Execution, Reconciliation, and Idempotency State-Machine Specification

**Status:** Phase 0 deterministic baseline frozen; broker-specific mappings remain validation dependencies  
**Version:** 1.0.1  
**Date:** 2026-08-12  
**Authorization boundary:** External Python trading remains disabled. This document specifies later behavior only; it authorizes no `order_send`, order modification/cancellation, position close, demo trading, or live trading.

## 1. Safety invariants

1. Broker-observed orders, deals, and positions are authoritative; local state is a fallible projection.
2. No risk-increasing broker request may be emitted unless account fingerprint, symbol properties, session, data freshness, news state, exposure, risk ledger, and persisted workflow state are reconciled and unambiguous.
3. An acknowledgement is not a fill. A timeout is not a rejection. Absence of a response is `SUBMISSION_UNCERTAIN` until reconciled.
4. A retry may repeat a read or analysis operation. It may not repeat a broker submission unless reconciliation proves that the original submission did not create any order, deal, or position and the retry policy explicitly permits a new attempt.
5. Unknown or unowned exposure causes `QUARANTINED`: prohibit all new risk-increasing activity and alert the operator. Do not assume ownership or close it automatically.
6. OpenAI has no credentials, broker methods, or authority over position size, execution, modification, or closure.
7. Restart, disconnect, clock error, storage error, conflicting broker evidence, or account/symbol change fails closed.

## 2. Persisted objects

### 2.1 Analysis proposal

Immutable analyst output linked to a market snapshot. It cannot itself become an order.

### 2.2 Trade intent

Created only after schema, freshness, semantic, and Risk Governor approval. Minimum frozen fields:

- `intent_id`: UUIDv7 or equivalently collision-resistant identifier;
- `idempotency_key`: SHA-256 over a canonical, length-prefixed encoding of environment, account fingerprint, symbol, strategy/setup version, proposal ID, direction, entry specification, stop, targets, expiry, and approved risk-policy/config hash;
- proposal, snapshot, feature, Risk Governor trace, and configuration hashes;
- requested order type and price constraints, governor-calculated volume, maximum slippage/deviation policy, expiry, and cancellation rules;
- monotonic local revision plus UTC creation timestamp;
- lifecycle state and append-only transition history.

Canonical encoding must define field order, Unicode normalization, decimal serialization, null handling, and schema version. Floating-point textual formatting is prohibited in the key input; use exact decimal/integer units.

### 2.3 Broker observations

Each observation stores receipt time, broker/server time where supplied, request/result identifiers, raw retcode, order/deal/position tickets, magic/comment, symbol, side, type, price, volume, SL/TP, and raw payload hash. Ticket IDs are local confidential data and never enter OpenAI prompts.

## 3. State model

Normal path:

`OBSERVED -> PROPOSED -> REJECTED | APPROVED -> READY -> SUBMITTING -> SUBMISSION_UNCERTAIN | ACKNOWLEDGED -> RECONCILED_OPEN -> MANAGING -> EXIT_SUBMITTING -> EXIT_UNCERTAIN | RECONCILED_CLOSED`

Cross-cutting terminal/control states: `EXPIRED`, `CANCELLED`, `QUARANTINED`, `INCIDENT`.

| State | Meaning | Risk-increasing action allowed? |
|---|---|---|
| `OBSERVED` / `PROPOSED` | Analysis only | No |
| `REJECTED` / `EXPIRED` / `CANCELLED` | Terminal without exposure | No |
| `APPROVED` | Governor approved exact bounded intent | No broker action yet |
| `READY` | Fresh preflight and reconciliation passed | One atomic transition to `SUBMITTING` only |
| `SUBMITTING` | Durable submission-attempt record exists before broker call | No second call |
| `SUBMISSION_UNCERTAIN` | Call outcome cannot be proven | No; reconcile or quarantine |
| `ACKNOWLEDGED` | Broker response received, lifecycle not yet proven | No new risk |
| `RECONCILED_OPEN` / `MANAGING` | Broker exposure mapped uniquely to intent | Only frozen management policy; never add to a failed trade |
| `EXIT_SUBMITTING` / `EXIT_UNCERTAIN` | Risk-reducing request pending/uncertain | No risk increase |
| `RECONCILED_CLOSED` | No remaining intent-owned order/position and deal history reconciled | No |
| `QUARANTINED` / `INCIDENT` | Ownership, state, or safety uncertain | No |

Every transition is an ACID transaction containing prior state/version, event, actor, timestamps, evidence references, transition reason, and new state. Compare-and-swap on version prevents concurrent writers.

### 3.1 Frozen transition rules

The transition relation is allow-listed; an unlisted event/state pair is a protocol error and enters `INCIDENT`. Terminal states never transition back to an active intent. A fresh analysis always creates a new intent.

- `APPROVED -> READY` requires one coherent preflight snapshot and an exact Governor approval for the request hash.
- `READY -> SUBMITTING` is the only transition that may authorize a later risk-increasing broker call, and only after the durable transaction commits.
- `SUBMITTING` may become `ACKNOWLEDGED` only with a syntactically valid broker result tied to the exact attempt; otherwise it becomes `SUBMISSION_UNCERTAIN`.
- `ACKNOWLEDGED` may become `RECONCILED_OPEN`, `RECONCILED_CLOSED`, or `SUBMISSION_UNCERTAIN`; acknowledgement alone never proves exposure state.
- Any active state becomes `EXPIRED` only when reconciliation proves there is no attributable live or historical exposure. Otherwise expiry produces uncertainty/quarantine.
- Any unexpected account, symbol, ownership, ledger, lease, or broker-state observation enters `QUARANTINED`; evidence corruption or an impossible transition enters `INCIDENT`.
- Recovery from `QUARANTINED` or `INCIDENT` is a separately audited operator action after root cause and full reconciliation. It cannot resume the old intent or emit a broker request.

Events are typed before transition evaluation. Precedence is total and fixed:

1. `EVIDENCE_CORRUPTION` or `PROTOCOL_INVALID` -> `INCIDENT`.
2. Otherwise `SAFETY_OBSERVATION` (unknown/conflicting account, symbol, ownership, ledger, lease or broker state) -> `QUARANTINED`.
3. Otherwise `NORMAL_TRANSITION` is evaluated against the allow-listed transition relation; an unlisted pair is reclassified `PROTOCOL_INVALID` and enters `INCIDENT`.

If one input contains more than one event class, the highest item above wins. Thus corruption/impossible protocol evidence can never be downgraded to quarantine, and a valid safety observation cannot be misclassified as a normal transition.

At most one lifecycle writer may hold the account/symbol lease. Losing the lease immediately removes call authority. Wall-clock reversal never changes ordering; durable sequence and monotonic time order local events.

## 4. Submission protocol

1. Acquire a single-writer lease scoped to environment + account fingerprint + symbol.
2. Re-read account, positions, orders, tick, symbol properties, session/news/health state and policy configuration.
3. Recompute all sizing and constraints locally. Any material change returns to `REJECTED` or a fresh approval; the executor cannot silently increase size.
4. Prove the idempotency key has no active or historical submission conflict.
5. Persist `SUBMITTING`, submission-attempt number, exact request hash, and durable outbox record; commit before any future broker call.
6. A later authorized executor may issue exactly one call for that attempt.
7. Persist raw result, then reconcile broker orders/deals/positions. Retcodes are inputs to reconciliation, not final truth.
8. Transition only on uniquely attributable broker evidence. Ambiguity becomes `SUBMISSION_UNCERTAIN` then `QUARANTINED` after the bounded reconciliation deadline.

No automatic resubmission follows timeout, process crash, IPC failure, missing response, or a broker rejection. **Frozen first-release rule:** there is exactly one risk-increasing submission attempt per intent. If reconciliation proves no exposure was created, that intent becomes `REJECTED`, `EXPIRED`, or `CANCELLED`; any later attempt requires a fresh proposal, snapshot, Governor decision, intent ID, and idempotency key.

The durable call fence is `(environment, account_fingerprint, intent_id, attempt_no=1, request_hash)`, unique in storage. The outbox worker must atomically claim it by compare-and-swap. A claimed row is never reclaimed for another call after crash; it is reconciled as uncertain.

## 5. Attribution and reconciliation

Attribution uses multiple agreeing fields: account fingerprint, symbol, strategy-specific magic, compact intent fingerprint in comment where supported, direction/type, volume, price/time window, and order/deal/position linkage. Ticket alone is insufficient across environments; comment/magic alone is insufficient because of truncation/collision/manual reuse.

Reconciliation occurs at startup; before and after every later authorized broker action; after reconnect; on every broker event/poll cycle; after lease takeover; and before declaring closure. It classifies each broker object as `OWNED_UNIQUE`, `KNOWN_EXTERNAL` (not permitted on the dedicated account), `UNKNOWN`, or `CONFLICTING`. Any class other than uniquely owned or an empty expected state quarantines new risk.

Required checks include volume conservation across orders, deals and positions; side and net/gross exposure under retail hedging; price/SL/TP conformity within broker rounding; pending versus filled/cancelled state; partial fills/closes; fees/swap; and absence of orphan orders.

The reconciliation snapshot is one logical observation cut: account fingerprint, open orders, open positions, and bounded deal/order history are read with start/end timestamps. If the broker state changes during the cut or linkage/history is incomplete, the result is uncertain and no new risk is permitted. Closure requires (1) zero remaining owned order/position volume, (2) conserved entry/exit deal volume after broker rounding, and (3) the history horizon covering the entire intent lifetime.

## 6. Partial fills, OCO, and management races

- A partial entry creates actual exposure immediately. Recompute residual allowed risk before considering any remainder; default is cancel the remainder if safely attributable and supported by later authorization, otherwise quarantine.
- Never enlarge another order to compensate for missed or partial volume.
- TP1/TP2 or stop counterparts are locally orchestrated unless the exact account proves native broker linkage. Before acting, reconcile actual remaining volume.
- If both OCO legs appear executable/fill during a race, do not assume one cancelled the other. Reconcile all deals/orders/positions, cancel nothing blindly, and enter incident/quarantine if exposure differs from policy.
- Failed Zone A is closed as its own trade. Zone B needs a new proposal, snapshot, intent, idempotency key, and risk approval; it is never recovery/averaging.

**Frozen first-release management scope:** no synthetic OCO, automatic partial-profit leg, trailing stop, break-even move, pending-entry replacement, or automatic remainder resubmission is permitted until its broker-specific state table and demo evidence pass a later gate. Protective SL/TP attached in the original exact request may be specified later only after account capabilities are probed. Uncertain exits block all new risk and require reconciliation/operator escalation; they never authorize an inverse order as a presumed close.

## 7. Restart and recovery

Startup begins with execution disabled. Load the append-only ledger, verify its hash chain/checkpoints and schema, acquire the lease, fingerprint the connected terminal/account/symbol, then reconcile complete broker state. `SUBMITTING`, uncertain, orphaned, conflicting, unknown, corrupt, or mismatched state remains quarantined. A watchdog may restart analysis/read-only services, but cannot automatically enable execution. Repeated restart/reconciliation failure escalates to `INCIDENT`.

After ledger integrity and broker reconciliation succeed, the persisted-state outcome is total:

| Persisted state | Restart outcome |
|---|---|
| `OBSERVED` | `OBSERVED` |
| `PROPOSED` | `PROPOSED` |
| `REJECTED` | `REJECTED` |
| `APPROVED` | `APPROVED` (fresh preflight required; no call authority) |
| `READY` | `APPROVED` (prior readiness is revoked; fresh preflight required) |
| `SUBMITTING` / `SUBMISSION_UNCERTAIN` / `ACKNOWLEDGED` | `QUARANTINED` |
| `RECONCILED_OPEN` / `MANAGING` | `QUARANTINED` pending full exposure/runbook reconciliation |
| `EXIT_SUBMITTING` / `EXIT_UNCERTAIN` | `QUARANTINED` |
| `RECONCILED_CLOSED` | `RECONCILED_CLOSED` |
| `EXPIRED` | `EXPIRED` |
| `CANCELLED` | `CANCELLED` |
| `QUARANTINED` | `QUARANTINED` |
| `INCIDENT` | `INCIDENT` |

Any ledger/hash/schema corruption overrides this table and produces `INCIDENT`. Any account/symbol/ownership/lease/broker mismatch overrides a non-incident outcome and produces `QUARANTINED`. No restart outcome grants broker-call authority; `APPROVED` must pass a new `APPROVED -> READY` preflight after a separately authorized later gate.

## 8. Frozen preimplementation test vectors

The later deterministic harness must prove, without a broker call:

1. same canonical intent produces the same key; every safety-relevant field change changes it;
2. concurrent workers permit one `SUBMITTING` transition;
3. crash before durable commit emits no call; crash after commit/before response never duplicates a call;
4. timeout plus later discovered fill reconciles to the original intent;
5. acknowledgement without order/deal evidence remains uncertain;
6. partial fill and rejected remainder conserve volume and risk;
7. pending activation during restart is detected;
8. duplicate/comment collision, unknown position/order, unexpected symbol, or account change quarantines;
9. OCO double-fill/race never creates an additional action under uncertainty;
10. stale data, session closure, news lock, clock drift, and changed symbol properties prevent `READY`;
11. database unavailable/corrupt or lease lost prevents submission;
12. risk-reducing operations cannot invert a position or increase gross exposure.

Additional mandatory vectors:

13. duplicate outbox claim and lease takeover yield zero additional calls;
14. a rejected/expired/cancelled intent cannot return to `READY`;
15. a broker result with mismatched request ID/hash is conflicting evidence;
16. history truncation prevents closure;
17. an external order with a colliding comment/magic remains unknown, not owned;
18. restart from every persisted state has one deterministic fail-closed outcome;
19. clock rollback preserves sequence ordering and blocks freshness-dependent action;
20. exit volume exceeding reconciled remaining volume is rejected before any call.

Acceptance for specification freeze: all transitions have total deterministic handling; forbidden transitions are machine-enumerable; every uncertain state prohibits new risk; golden, property, mutation, crash-point, and concurrency tests are specified with expected outcomes. Broker-specific behavior remains for later demo gate and is not inferred.

## 9. Remaining validation dependencies (do not reopen the frozen core)

- Exact MT5 retcode-to-event table and account-specific partial-fill behavior.
- Bounded reconciliation intervals/timeouts derived from measured VPS/broker latency.
- Exact magic/comment encoding limits and collision strategy on the target account.
- Owner decision for emergency handling beyond quarantine/alert; automatic closure is not approved.
- Retention, operator acknowledgement, incident severity, and manual recovery/runbook rules.

These dependencies may narrow supported behavior or keep execution disabled. They may not weaken single-attempt fencing, uncertainty quarantine, unique attribution, broker-authoritative reconciliation, or the prohibition on unapproved risk increase.
