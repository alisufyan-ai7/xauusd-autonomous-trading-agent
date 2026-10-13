# Accelerated Production Candidate Plan

**Status:** PROPOSAL ONLY — not an accepted governance baseline  
**Prepared:** 2026-10-05 Asia/Karachi / 2026-10-04 UTC  
**Source baseline:** private `main` R42 at `dea79e9aaebdaf81a09191b0d47e0f87157eb9e1`  
**Delivery objective:** production-grade, execution-disabled XAUUSD production candidate operating continuously on the VPS by 2026-10-31  
**Non-authority statement:** this plan does not authorize publication, implementation, deployment, an OpenAI call, a VPS disruption, a broker mutation, demo execution, or real-money execution.

## 1. Decision and delivery boundary

Adopt two independent acceptance tracks:

1. **Production Candidate Readiness (PCR):** software may be constructed, tested, deployed and operated in live shadow mode while its execution sink is physically and logically incapable of submitting, modifying, cancelling or closing an order.
2. **Real-Money Risk Admission (RMRA):** 0.01-lot tiny-live remains prohibited until every frozen empirical, replay, operational, shadow and demo requirement has passed and the owner separately approves activation.

Gate 0 does not disappear. Its current state remains **7 PASS / 1 FAIL / 6 PENDING**. The proposed change is dependency placement: unresolved Gate 0 evidence would no longer block construction or an execution-disabled shadow deployment, but it would continue to block real-money admission.

R4 remains an immutable `FAIL`. R34 and R35 remain immutable fail-closed attempts. Nothing in this plan reclassifies, overwrites or interprets them as positive evidence.

## 2. Current technical starting point

R42 contains 394 repository blobs, extensive frozen specifications, deterministic validation oracles, Gate 1–4 planning schemas and read-only VPS tools. It does **not** contain a production application package, package/build configuration, production service, order executor, durable production journal/outbox, production supervisor, release artifact or production deployment/rollback implementation. Every entry in the R42 Gate 1 port catalog records `production_implementation_present=false`.

The October plan is therefore a greenfield production implementation against unusually mature contracts and test oracles—not a deployment of an already-built agent.

## 3. Proposed new governance baseline

These changes require explicit owner acceptance and publication as a new baseline before implementation begins.

| Proposed change | Why it accelerates delivery | Additional risk | Compensating safeguards | Preserved history / pre-tiny-live requirement |
|---|---|---|---|---|
| Permit Gate 1 production construction before overall Gate 0 PASS | Removes an artificial dependency between empirical closure and writing contract-bound software | Rework if later evidence changes configuration or reveals a defect | Strict ports; configuration and policy identities hash-bound; unresolved inputs produce `DENY`, `UNKNOWN` or quarantine; no order-capable adapter in PCR | R4/R34/R35 unchanged; all unresolved Gate 0 items still required before tiny-live |
| Permit Gate 2 product-bound adversarial work continuously as components stabilize, with a final same-release full run | Compresses implementation and fault-validation into one interval | Early tests may exercise incomplete compositions | No partial result is a PASS; final release requires zero failed tests, zero critical mutation survivors and all eleven frozen scenario families on the sealed artifact | Gate 2 criteria unchanged; only timing changes |
| Permit live read-only ingestion and continuous shadow after PCR acceptance, before Gate 0/Gate 3 completion | Starts operational learning in October instead of waiting for long-duration research | Live system may expose defects while research evidence is incomplete | Static absence of order capability; `execution_enabled=false`; broker action count fixed at zero; startup capability scan; append-only audit; fail-closed quarantine; rollback tested before deployment | Early shadow time is operational evidence only. Formal Gate 4 PASS still requires the frozen full market month, event coverage, reconciliation and incident criteria |
| Permit a bounded Exness demo lane to overlap shadow after a separate Demo Admission Gate and owner approval | Validates the real broker lifecycle within October | Demo behavior could be mistaken for live safety or performance evidence; demo faults can create simulated exposure | Dedicated demo identity; one XAUUSD symbol; 0.01-lot maximum; one concurrent position; no averaging/martingale; bounded daily submissions; deterministic Risk Governor authority; kill switch; full reconciliation; demo results cannot validate profitability or any live threshold | Demo does not cure R4/R34/R35 and does not count as real-money evidence. Full demo lifecycle acceptance remains required before tiny-live |
| Permit actual Sol transport integration in non-authoritative shadow before G0-12/G0-14, under separate approval | Allows production integration to finish in October | Cost/privacy/availability/model-output risk | `store=false`; no tools; minimized allow-listed fields; strict schema and echo binding; deadline/state binding; budget cap; every failure rejects; Sol has no risk or execution authority | G0-14 remains pending until its frozen post-G0-12 chronological validation passes; pre-G0-14 calls confer no Gate 0 credit |
| Move G0-04/G0-05/G0-06/G0-07/G0-08/G0-12/G0-14 and formal Gate 3/4 closure to parallel or post-PCR, but keep them pre-tiny-live | Allows calendar- and event-dependent evidence to mature while software operates safely | A production candidate may exist that cannot lawfully or safely trade real money | Immutable execution barrier, visible `NOT_LIVE_ELIGIBLE` state, CI capability scan, no live credentials, activation artifact absent, two-person-style owner confirmation through explicit approval | Every frozen acceptance requirement remains binding for tiny-live |

This baseline changes sequencing, not acceptance semantics. Any later change to a threshold, sample, claim or pass rule would require a separate governance decision.

## 4. Requirement disposition

| Existing requirement | Construction | Execution-disabled VPS shadow | Bounded demo | 0.01-lot tiny-live |
|---|---:|---:|---:|---:|
| G0-01/02/03/09/10/11/13 already PASS | Reuse as inputs | Required | Required | Required |
| G0-04 natural Event Guard transition | Parallel GET-only monitoring | May remain pending; uncertainty locks affected decisions | May remain pending if affected periods are locked | **PASS required** |
| G0-05 R4 failure / successor R5 | R4 preserved; build configurable governor now | May remain pending; candidate labelled unqualified | Test-only demo envelope only; no performance claim | **R5 PASS required** |
| G0-06 normal/weekend/holiday boundaries | Build and test guard now | Capture prospectively while shadow runs | Trade only outside ambiguous/boundary locks | **PASS required** |
| G0-07 operational reliability campaign | Build/simulate watchdog now | Natural non-disruptive observations allowed | Separate campaign approval; demo does not substitute | **New campaign PASS required** |
| G0-08 account-specific M1 stress | Prepare now | Read-only preparation | Demo metrics may inform but cannot promote | **PASS after R5 required** |
| G0-12 registered chronological replay | Build engine and registry now | May remain pending | May remain pending; demo is lifecycle-only | **PASS after R5 required** |
| G0-14 production Analyst chronology | Build fake/strict adapter now | Optional non-authoritative calls only after separate approval | Same limitation | **PASS after G0-12 and separate approval required** |
| Gate 1 product implementation | Start under new baseline | **PCR PASS required first** | Required | Required |
| Gate 2 adversarial validation | Run incrementally; final sealed run | **Final same-release PASS required first** | Required | Required |
| Gate 3 registered replay | Build now; evidence later | Not required to start provisional shadow | Not required for lifecycle-only demo | **PASS required** |
| Gate 4 observation | Register thresholds before start | Start immediately after PCR; formal criteria unchanged | Run in parallel | **Full market month + event coverage + PASS required** |
| Gate 5 demo lifecycle | Prepare in parallel | Not required for shadow | Admission gate + approval required | **Final lifecycle PASS required** |

## 5. Production Candidate release gates

### PCR-0 — baseline and capability boundary

- Owner accepts and authorizes publication of this sequencing baseline.
- Implementation authority is limited to an execution-disabled production candidate.
- Real-money credentials and an order-capable live adapter are absent from the build and VPS.
- CI rejects imports/calls capable of order submit/modify/cancel/close outside the separately packaged demo adapter.

### PCR-1 — deterministic product

- Exact-value/time/identity foundation; immutable market snapshots; setup/feature engine; Event Guard; deterministic Risk Governor; Sol strict adapter; durable journal/lease/outbox; audit/reconciliation; alerts/health; supervisor; packaging.
- Differential tests bind the implementation to the existing frozen oracles.
- Zero failed tests and zero critical surviving mutations.

### PCR-2 — same-release adversarial acceptance

- All eleven registered Gate 2 families pass against the sealed product artifact.
- Crash/restart, torn store, stale data, identity drift, submission uncertainty, analyst corruption, calendar ambiguity and alert failure all produce deterministic reject/quarantine behavior.
- Windows Python 3.12 and CI parity pass.

### PCR-3 — execution-off VPS deployment

- Release manifest and dependencies sealed; secrets separated; least privilege and owner-only ACLs verified.
- Preflight proves zero positions, zero pending orders, `execution_enabled=false`, no order-capable live adapter and external Python real-money trading disabled.
- Deployment, service start, read-only Exness/MT5 XAUUSD ingestion, rollback and recovery reconciliation pass.
- Continuous shadow begins with broker action count fixed at zero.

### DEMO-ADMIT — separate and optional

- Separate owner approval after PCR-1/PCR-2 PASS and at least 48 hours of clean shadow operation.
- Dedicated demo account fingerprint; zero demo exposure at start; order routing refuses non-demo identity.
- Hard envelope: XAUUSD only, 0.01 lot maximum, one position, no averaging/martingale, bounded submissions, protective stop required, deterministic kill/quarantine, no credential sharing with live.
- Demo adapter packaged separately and impossible to select with a live account fingerprint.
- Activation starts demo lifecycle validation; it is not Gate 5 PASS.

## 6. Maximum-parallel October schedule

Dates assume governance acceptance on 2026-10-05, repository publication/branch authority by 2026-10-06, immediate engineering capacity across all lanes, and timely VPS access. Any critical safety defect moves the dependent milestone; the date does not relax the gate.

| Dates (2026) | Lane A — core/durability | Lane B — data/features/guards | Lane C — broker/risk/reconciliation | Lane D — Analyst/alerts/ops | Integrated milestone |
|---|---|---|---|---|---|
| Oct 5–6 | Baseline approval; project/package/CI skeleton; exact types, clocks, identities | Snapshot and completed-bar ports | Fake broker contract; deterministic governor skeleton | Service/config/secrets skeleton; null Sol transport | Build authority and release boundary established |
| Oct 7–11 | Journal, CAS lease, hash chain, outbox, recovery | MT5 read-only ingestion; H4/H1/M15/quote admission; feature families | Fake lifecycle scheduler; normalization; exposure ledger | Strict Sol schema/timeout/state binding; Event Guard and alert adapters | First end-to-end null-execution vertical slice |
| Oct 12–16 | Crash recovery and audit verifier | Setup lifecycle; session/holiday/shock locks | Reconciliation/idempotency; demo adapter behind compile/package boundary | Watchdog, monitoring, incident and rollback tooling | Component unit/differential tests green |
| Oct 17–21 | Store/lease/outbox fault matrix | Data/time/guard adversarial matrix | Risk/submission/identity fault matrix | Analyst/service/evidence fault matrix; Windows service packaging | Integrated release candidate 1; no external execution |
| Oct 22–24 | Full regression, property and mutation closure | Replay/live feature reconciliation fixtures | Demo-account fingerprint and zero-exposure preflight, no orders | Sol live-transport test only if separately approved; alerts health | Sealed RC2; PCR-1/PCR-2 decision |
| Oct 25 | Release manifest, backup and rollback rehearsal | Live read-only feed soak | Reconciliation dry run | Supervisor/monitoring dashboard and alert preflight | PCR-3 deployment-ready decision |
| **Oct 26** | Durable service active | Live XAUUSD ingestion active | Null execution sink; zero broker actions | Monitoring/audit/watchdog active | **Production software operational on VPS; continuous shadow starts** |
| Oct 27–29 | Audit/restart continuity under natural operation | Shadow reconciliation and incident burn-down | Demo preflight and test-only envelope | Sol/alerts operational soak if authorized | 48-hour clean-shadow requirement; DEMO-ADMIT review |
| **Oct 30** | — | — | Demo adapter enabled only after separate approval | Demo monitoring/kill/rollback armed | **Earliest autonomous Exness demo start** |
| Oct 31 | Release/rollback evidence complete | Shadow continues | Demo lifecycle evidence continues | Operations handoff | October delivery checkpoint; no real-money authority |

Parallel evidence lanes continue throughout: R5 registration/window; GET-only G0-04; prospective G0-06; G0-07 preparation and, only if separately approved, its one operational campaign. G0-08/G0-12 do not start until R5 actually passes. G0-14 remains separately approval-gated.

## 7. Three delivery dates

1. **Production software operational on VPS: 2026-10-26.** This means a sealed production candidate with live XAUUSD read-only ingestion, deterministic decisions, audit/reconciliation, monitoring, watchdog and rollback operating continuously with a null execution sink and zero broker actions.
2. **Autonomous Exness demo trading: 2026-10-30, conditional.** This is the earliest activation date, not demo acceptance. It requires PCR-1/PCR-2 PASS, 48 clean shadow hours, dedicated demo identity, zero-exposure preflight and separate owner approval no later than 2026-10-29. If any condition fails, demo remains disabled.
3. **Earliest defensible 0.01-lot tiny-live activation: 2026-12-21, strictly conditional and not guaranteed.** This assumes complete R5 registration is published by Oct 8; Oct 9 is a full UTC embargo day; the untouched 63-day window runs Oct 10–Dec 11; R5 passes on Dec 12; every other Gate 0 item, registered replay, full shadow month/event coverage and demo lifecycle passes in parallel or by Dec 18; a qualifying XAU holiday boundary and natural G0-04 transition actually occur; and the owner separately approves real money. If either external event does not occur or any gate fails, there is no defensible tiny-live date.

## 8. Critical safeguards that cannot be traded for schedule

- The PCR artifact has no live order capability; configuration alone cannot enable it.
- Demo and live adapters are different sealed packages with mutually exclusive account fingerprints.
- Risk Governor is deterministic and authoritative; Sol can only reject or annotate and can never increase risk or cause execution.
- Unknown/stale/conflicting data, calendar state, exposure, identity, storage, analyst output or recovery state always rejects or quarantines.
- One writer, durable fencing, append-only hash chain and broker-authoritative reconciliation are mandatory.
- No automatic retry after uncertain submission; reconcile first.
- Rollback is tested before VPS deployment; monitoring and kill controls are live before demo activation.
- No October schedule date converts an incomplete test or evidence item into PASS.

## 9. Owner decisions required before action

Approval should be granular:

1. **APC-BASELINE:** accept the dual-track sequencing baseline and authorize production-candidate implementation with no live order capability.
2. **APC-PUBLISH:** separately authorize publication of the accepted baseline and implementation branch/records; this may also name the exact R5 registration publication when its hashes are complete.
3. **APC-SOL-SHADOW:** separately authorize bounded, `store=false`, tool-free, non-authoritative Sol transport tests and shadow use.
4. **APC-VPS-SHADOW:** separately authorize execution-off VPS deployment and continuous read-only live shadow.
5. **G0-07-OPERATE:** separately authorize the previously requested one-attempt prospective G0-07 campaign after its complete protocol is reviewed.
6. **APC-DEMO:** separately authorize the sealed demo adapter and autonomous Exness demo activation after DEMO-ADMIT passes.
7. **TINY-LIVE:** later, after every pre-live requirement passes, separately authorize the exact 0.01-lot live activation artifact, account fingerprint, start window and kill/rollback packet.

Until those approvals are given, this file is a proposal only and the R42 sequencing baseline remains controlling.
