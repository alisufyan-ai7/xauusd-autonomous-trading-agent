# Gate 4 shadow operations packet

**Status:** advance preparation only  
**Entry barrier:** Gates 1–3 PASS  
**Mandatory mode:** shadow-only; no order capability; `execution_enabled=false`

## 1. Purpose and frozen acceptance

Gate 4 observes live inputs and creates complete non-executing decision/audit records. It must run for at least one full market month plus the event coverage frozen before the observation starts. The window is not shortened for schedule convenience.

Gate 4 passes only when:

- the deployment has no execution capability;
- decision and audit records are complete;
- broker/live inputs and shared replay features reconcile within the frozen tolerance;
- the required market/session/event/regime inventory is complete; and
- every incident is resolved and its evidence admitted.

## 2. Service and deployment requirements

| Area | Required control |
|---|---|
| Release identity | Byte-exact Gate 3 release, dependency hashes, Python architecture, database schema, MT5 build, model/profile/prompt/config hashes and source commit. |
| Execution barrier | Separate `analysis_enabled`/`execution_enabled`; execution absent or hard-disabled. Install, config/account/version/build change and failed health check restore execution off. |
| Service supervision | One controlled instance; bounded restart; repeated failure/reconciliation ambiguity latches quarantine; no restart loop. |
| Startup | Verify account/symbol fingerprint, clock, storage, audit chain, data/session/Event Guard health and current broker observations before analysis. |
| Storage | ACID append-only decision/event journal, immutable hashes, tested backup/restore and capacity guard. |
| Time | UTC everywhere; wall/monotonic tracking; drift alert; no favorable synthesis across missing intervals. |
| Network/secrets | Allow-listed read-only endpoints; OS-protected secrets; no secret/account/ticket/private evidence in prompts or published logs. |
| Deployment | Staged execution-off install, health/reconciliation smoke test, immutable start receipt and rollback readiness. |

The service may attach/read through approved ports. It must have no order submission, modification, cancellation or closure method available to the shadow composition root.

## 3. Shadow decision record

Every eligible decision instant produces exactly one immutable record, including no-trade/reject/quarantine outcomes:

```json
{
  "schema_version": "shadow-decision-1.0",
  "decision_id": "<uuid>",
  "decision_time_utc": "<timestamp>",
  "release_manifest_sha256": "<sha256>",
  "account_symbol_fingerprint_sha256": "<sha256>",
  "snapshot_roots": {"H4": "<sha256>", "H1": "<sha256>", "M15": "<sha256>", "quote": "<sha256>"},
  "session_event_shock_state": "<hash-bound typed state>",
  "feature_root_sha256": "<sha256>",
  "setup_result": "NO_TRADE|REJECT|CANDIDATE|QUARANTINE",
  "reason_codes": [],
  "analyst_request_response_hashes": null,
  "governor_trace_sha256": "<sha256>",
  "hypothetical_intent_sha256": null,
  "execution_enabled": false,
  "broker_action_count": 0,
  "audit_prev_sha256": "<sha256>"
}
```

If a later approved Analyst call is part of the Gate 4 design, it remains tool-free, minimized, strict-schema and non-authoritative. No OpenAI action is implied by this packet; separate authority applies.

## 4. Monitoring and alerting

Monitor and hash-record:

- service process/heartbeat, restart count and quarantine state;
- execution barrier state and static capability fingerprint;
- account/symbol/build/config identity;
- quote/bar freshness, gaps and completed-bar timing;
- session/holiday/Event Guard/shock health and source disagreements;
- clock drift and monotonic anomalies;
- journal/audit continuity, write latency, backup age, disk capacity and off-host copy state;
- decision completeness and duplicate/missing decision instants;
- replay/live feature and setup reconciliation mismatch count/tolerance;
- Analyst transport/schema/freshness failures if separately authorized;
- alert path health under the accepted A1 contract.

Thresholds and reconciliation tolerances must be frozen from Gate 1–3 outputs before the shadow start. Their values are not invented by this packet. G0-09 proves one canary, not a general delivery SLA; Gate 4 must report actual shadow-period alert health.

## 5. Incident handling

| Severity | Trigger | Required action |
|---|---|---|
| Critical | Execution barrier/capability defect, identity mismatch, audit corruption, unknown broker exposure, risk-increasing output path | Latch quarantine, stop analysis if needed, alert, preserve evidence; Gate 4 window cannot pass until resolved and reviewed. |
| High | Replay/live feature mismatch beyond tolerance, repeated service failure, clock/storage/source-health ambiguity | Quarantine affected decisions; bounded recovery only; open incident. |
| Medium | Isolated rejected input, recoverable source outage or late data with correct fail-closed result | Record full trace and recovery; include in acceptance inventory. |
| Informational | Expected no-trade/reject/lock state | Record normally; no promotion or suppression. |

Incident record fields: immutable ID/times, affected release/identity/decision hashes, detected condition, safety state, broker action count, evidence roots, containment, root cause, repair release, regression tests, recovery/reconciliation, owner decisions and closure receipt. History is append-only.

## 6. Observation inventory and acceptance report

Before start, register:

- exact start rule and definition of the full market month;
- required market/session/holiday/event/regime coverage;
- expected decision instants and allowed documented gaps;
- replay/live feature and setup tolerance/matching procedure;
- monitoring thresholds, incident classification and extension rule;
- release/config/account/symbol identities; and
- report schemas and hashes.

The acceptance report must include total expected/observed/missing decisions; data/source health; complete event/session/regime coverage; no-trade/reject/candidate/quarantine counts; replay/live feature mismatches; all incidents and recovery; service/restart/storage/clock results; alert health; execution barrier proofs; broker action count zero; and the derived verdict.

Any deployment/config/model/prompt/account/symbol/build change creates a new identity, restores execution off, and follows the predeclared continuation/restart rule. It may not silently combine incomparable observation periods.

## 7. Deployment and rollback checklist

1. Verify Gates 1–3 receipts and the exact release manifest.
2. Verify backup/restore, schema migration, disk/clock/audit and off-host-copy controls.
3. Install with execution hard-disabled and no order-capable adapter in the composition root.
4. Reconcile read-only broker/account/symbol and historical warm-up state.
5. Run a no-send/no-order smoke test and capture the start receipt.
6. Start only at the registered market boundary.
7. On failure, latch quarantine, preserve journal/logs, restore the prior execution-off release/config, rebuild/reconcile state and append the incident/supersession record.

## 8. Gate 5 preparation during Gate 4

Without enabling execution:

- provision the segregated Exness demo environment and revalidate account/symbol/build identity;
- implement the MT5 adapter behind the Gate 1 port and freeze retcode/event mappings;
- prepare lifecycle cases for rejects, delayed/uncertain results, reproducible partial behavior, pending expiry, modifications and OCO races;
- verify one-attempt fencing, reconciliation, no duplicate exposure, deployment, kill and rollback using the demo simulator/configuration with connection/order authority off;
- prepare the demo runbook, out-of-repository evidence locations and sanitized acceptance template; and
- stop for separate owner approval before any demo order capability or external Python trading is enabled.

Gate 4 PASS alone does not authorize Gate 5 execution.
