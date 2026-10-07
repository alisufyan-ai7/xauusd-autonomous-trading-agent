# Master roadmap to production

**Roadmap version:** R43 (staged; publication approval required)  
**Recorded:** 2026-10-04  
**Authoritative source revision:** private `main` at `dea79e9aaebdaf81a09191b0d47e0f87157eb9e1` (R42)  
**Current gate:** Gate 0 — `INCOMPLETE_FAIL_CLOSED`, 7 PASS / 1 FAIL / 6 PENDING  
**Current operating mode:** closure only; external Python trading disabled; no demo/live trading authorized

This is the single forward-looking schedule and dependency authority for Gates 0–7. Accepted specifications, evidence, Decision Log entries, and historical revision records remain authoritative for their own claims. This roadmap does not add an acceptance requirement, alter a frozen interface, reclassify evidence, authorize an external action, or replace a gate decision.

## 1. Frozen progression and dependency classes

The only permitted progression is:

`Gate 0 -> Gate 1 -> Gate 2 -> Gate 3 -> Gate 4 -> Gate 5 -> Gate 6 -> Gate 7`

Preparation may run ahead of the active gate, but evidence may be credited only to the gate whose entry criteria have passed. Production/trading-capable implementation may not begin before Gate 0 PASS.

| Class | Meaning |
|---|---|
| `CALENDAR_WAIT` | A prospectively sealed date/window or naturally occurring observation must mature. |
| `ENGINEERING` | Code, tests, packaging, deployment or operational artifacts must be built and verified. |
| `EVIDENCE` | An admitted, immutable result is required; a plan or passing oracle is not enough. |
| `OWNER_APPROVAL` | A separately recorded owner decision/action is mandatory before proceeding. |
| `EXTERNAL_DEPENDENCY` | A provider, broker, market, host or other external system must supply an eligible state or result. |

## 2. Critical path to the first tiny-live trade

1. Close Gate 0 without reclassifying frozen evidence: preserve G0-05/R4 as `FAIL`; seal and publish the prospectively registered R5 successor before its future evaluation data; wait for a genuine G0-04 transition; complete fresh prospective G0-06 normal/weekend and officially published XAU holiday boundaries; and, only after separate operational approval, execute the new G0-07 campaign once under its stronger dual-MT5/OS observation mechanism. If and only if R5 passes, run G0-08 and G0-12; then obtain separate approval for G0-14 and conduct the final Gate 0 review. (`CALENDAR_WAIT`, `EVIDENCE`, `EXTERNAL_DEPENDENCY`, `OWNER_APPROVAL`)
2. Implement the deterministic runtime against the frozen contracts and pass Gate 1. (`ENGINEERING`, `EVIDENCE`)
3. Bind the actual Gate 1 implementation to the frozen adversarial matrix and pass Gate 2. (`ENGINEERING`, `EVIDENCE`)
4. Execute the registered immutable historical replay and pass Gate 3. (`ENGINEERING`, `EVIDENCE`)
5. Run a non-executing live shadow for at least one full market month plus the frozen event coverage and pass Gate 4. (`CALENDAR_WAIT`, `EVIDENCE`, `EXTERNAL_DEPENDENCY`)
6. Obtain separate demo authority, run the Exness demo lifecycle packet, and pass Gate 5. (`OWNER_APPROVAL`, `EXTERNAL_DEPENDENCY`, `EVIDENCE`)
7. Revalidate the live account/symbol and obtain explicit real-money activation approval before the first Gate 6 tiny-live action. (`OWNER_APPROVAL`, `EXTERNAL_DEPENDENCY`)

The current critical-path uncertainty is Gate 0, not engineering throughput. R5 has not yet been registered; G0-04 is event-dependent; the exact XAU holiday boundary is publication-dependent; and G0-07 operation remains separately approval-gated. Therefore no unconditional Gate 0 or production date is defensible. R34 and R35 remain immutable fail-closed attempts; the newly authorized campaign is a distinct prospective generation, not a retry or reinterpretation of either attempt.

## 3. Forecast

Dates below are planning forecasts, not acceptance criteria. “Earliest” assumes every preceding gate passes on its first eligible evaluation, no material defect appears, and required owner decisions are immediate. Gate 5–7 durations are not frozen; their dates are explicitly estimates and will be replaced by predeclared samples before those gates open.

| Milestone | Earliest technically defensible | Realistic planning date/range | Basis |
|---|---|---|---|
| Successor G0-05/R5 result | **2026-12-09**, only if complete registration is published by 2026-10-05 UTC, followed by a full UTC embargo day and a 63-complete-day window | **2026-12-16 to 2026-12-18** if the development bundle is sealed and registration is published around 2026-10-12 | Nine full weeks provide defensible sample headroom over R4's observed total-row and ROLLOVER rates; acceptance thresholds are unchanged. |
| Gate 0 PASS | **Not date-certain; no earlier than the R5 result and all other blockers** | **Event- and approval-dependent after mid-December 2026** | G0-04 needs a natural qualifying transition; G0-06 needs three prospective boundary classes including a published XAU holiday; G0-07 needs separate operational approval and a one-attempt PASS; G0-08/G0-12 wait for R5 PASS; G0-14 needs separate approval. |
| Gates 1–3 complete | 7–9 weeks after Gate 0 PASS | 10–14 weeks after Gate 0 PASS | Gate 1 implementation 4–6 weeks; Gate 2 actual-implementation adversarial pass 2–3 weeks; Gate 3 registered replay 1–2 weeks. Preparation runs now. |
| Gate 4 shadow start | First market session after Gate 3 PASS | Within 1 week after Gate 3 PASS | Deployment-off reconciliation and start-record review must pass first. |
| Gate 4 shadow end | Start + at least one full market month and required event coverage | 5–7 weeks after start | Mandatory observation window is not compressed; unresolved incidents extend it. |
| Gate 5 autonomous demo start | First eligible session after Gate 4 PASS and separate owner approval | Within 1 week after Gate 4 PASS/approval | Demo environment and lifecycle packet are prepared during Gate 4; execution remains off until approval. |
| Gate 6 earliest tiny-live start | Earliest estimate: 3–6 weeks after Gate 5 starts, only after Gate 5 PASS and explicit real-money approval | 4–8 weeks after Gate 5 starts | Forecast assumption only; the Gate 5 lifecycle evidence, not elapsed time, controls. |
| Gate 7 first scaling decision | Earliest estimate: 6–12 weeks after Gate 6 activation | 10–16 weeks after Gate 6 activation | Forecast assumption only; a predeclared tiny-live sample and no critical incidents are required. Each increase needs approval. |

The old 2026-09-24 Gate 0 scenario is retired by R4's immutable `FAIL`. Downstream dates must be recomputed from the eventual objective Gate 0 PASS; no downstream elapsed-time estimate changes a frozen acceptance rule or authorizes execution.

## 4. Gate-by-gate authority

### Gate 0 — specification/evidence closure

| Field | Authority |
|---|---|
| Purpose | Close every frozen specification and evidence claim without creating production or trading capability. |
| Entry criteria | Current Phase 0 dossier, Decision Log and final evidence matrix are authoritative; closure-only direction accepted. |
| Exit criteria | Every frozen Gate 0 matrix claim has one admitted typed receipt with matching sanitized artifact hash; final matrix and owner review return PASS. |
| Dependencies | Prospective R5 registration/window/result (`CALENDAR_WAIT`, `EVIDENCE`); natural G0-04 and published G0-06 states (`EXTERNAL_DEPENDENCY`); separate G0-07 operational approval and admitted one-attempt campaign (`OWNER_APPROVAL`, `EVIDENCE`); G0-08/G0-12 after R5 PASS (`EVIDENCE`); G0-14 permission (`OWNER_APPROVAL`). |
| Parallel work | Seal the R5 development bundle and registration; keep G0-04 GET-only capture ready; register and execute eligible G0-06 boundaries prospectively; prepare but do not operate G0-07; maintain G0-08/G0-12 preflight; prepare documentation-only Gate 1–4 packets. |
| Owner actions/approvals | Publication approval for the completed R5 registration; separate operational approval for G0-07 after protocol review; separate approval before G0-14 Sol; final Gate 0 pass/fail review. No owner action is requested for GET-only monitoring or elapsed-time waits. |
| Earliest realistic start | In progress. |
| Target completion range | Not before the R5 result; otherwise event/evidence/approval dependent and currently not date-certain. |
| Blockers | G0-04, G0-05, G0-06, G0-07, G0-08, G0-12 and G0-14. R4 is immutable `FAIL`; R34/R35 are immutable fail-closed attempts. |
| Trading mode | **Disabled.** External Python trading disabled; no demo/live action. |

### Gate 1 — deterministic implementation/unit-integration validation

| Field | Authority |
|---|---|
| Purpose | Build the production runtime against frozen contracts and prove deterministic unit/integration behavior. |
| Entry criteria | Objective Gate 0 PASS plus explicit Phase 1 implementation authorization recorded under the existing governance boundary. |
| Exit criteria | Versioned report, golden vectors, property/mutation results, cross-oracle comparisons and requirement coverage; zero failed tests; zero critical surviving mutations; all exclusions justified. |
| Dependencies | Gate 0 PASS (`EVIDENCE`, `OWNER_APPROVAL`); product implementation, journal/outbox, packaging and CI (`ENGINEERING`). |
| Parallel work | Documentation, interface inventory, task graph, fake adapters, test registry design and release/rollback procedure may be prepared now. After entry, modules with stable input ports may be built in parallel while preserving the packet's order at integration boundaries. |
| Owner actions/approvals | Gate 1 implementation authorization if not already included in Gate 0 exit; publication/release approval under repository governance. No broker/OpenAI action is part of Gate 1. |
| Earliest realistic start | First business day after Gate 0 PASS/authorization. |
| Target completion range | Earliest 4–6 weeks; realistic 6–8 weeks after start. |
| Blockers | No production package, persistent ledger/outbox, full CI, dependency lock, release artifact, deployment or rollback implementation exists at R38. |
| Trading mode | **Disabled.** Fake/null broker only; deployment smoke test keeps execution off. |

### Gate 2 — failure/adversarial validation

| Field | Authority |
|---|---|
| Purpose | Demonstrate that the actual Gate 1 implementation fails closed under every frozen failure mode. |
| Entry criteria | Gate 1 PASS on a byte-exact release candidate. |
| Exit criteria | Fault-injection matrix and logs for every declared failure mode; zero risk-increasing action under uncertainty; exact quarantine/recovery transitions; zero critical surviving mutations. |
| Dependencies | Gate 1 artifact (`EVIDENCE`); production-bound simulator/crash/fault harness (`ENGINEERING`). |
| Parallel work | Build fault fixtures, mutation configuration, property generators, store crash points, protocol faults and Windows/Linux CI while Gate 1 modules stabilize; evidence run waits for Gate 1 PASS. |
| Owner actions/approvals | Publication/release approval only. No restart/disconnect drill, broker action or real delivery is included. |
| Earliest realistic start | Immediately after Gate 1 PASS. |
| Target completion range | Earliest 2–3 weeks; realistic 3–4 weeks. |
| Blockers | Existing oracles are not yet bound to the production implementation; no MT5 simulator, durable-store crash harness, full mutation/property runner or service-supervisor harness. |
| Trading mode | **Disabled.** Simulation/fakes only. |

### Gate 3 — registered historical replay

| Field | Authority |
|---|---|
| Purpose | Run the frozen strategies chronologically on the admitted immutable dataset and evaluate all predeclared statistical/risk criteria. |
| Entry criteria | Gates 1 and 2 PASS; admitted data/cost artifact; unopened registered replay holdout; immutable code/config/split/acceptance hashes. |
| Exit criteria | Immutable dataset hashes, complete trial registry, OOS/leakage/cost/stress reports; all predeclared thresholds pass; no unexplained replay/live-feature mismatch. |
| Dependencies | Gate 2 artifact (`EVIDENCE`); replay engine/statistics/reporting (`ENGINEERING`); untouched registered holdout (`EVIDENCE`). |
| Parallel work | Replay engine, ledger, bootstrap/PBO/DSR, robustness runner and templates may be built during Gates 1–2 against synthetic/admitted non-holdout fixtures; the registered result opens only after entry. |
| Owner actions/approvals | Gate 3 final pass/fail review/publication. No broker or trading approval. |
| Earliest realistic start | Immediately after Gate 2 PASS and registered-holdout preflight PASS. |
| Target completion range | Earliest 1–2 weeks; realistic 2–3 weeks, excluding a failed/insufficient-evidence research generation. |
| Blockers | No strategy replay engine, trial registry writer, decision/trade ledger, statistical runner, robustness runner or acceptance report template exists at R38. |
| Trading mode | **Disabled.** Offline historical replay only. |

### Gate 4 — live shadow

| Field | Authority |
|---|---|
| Purpose | Observe live inputs and produce non-executing decisions while reconciling live and replay features, audit, supervision and incidents. |
| Entry criteria | Gates 1–3 PASS; release manifest and execution-off deployment/rollback checks PASS; shadow observation plan frozen. |
| Exit criteria | At least one full market month plus frozen event coverage; no execution capability; complete decisions/audit; broker/live feature reconciliation within tolerance; every incident resolved. |
| Dependencies | Gates 1–3 (`EVIDENCE`); live market/broker read access (`EXTERNAL_DEPENDENCY`); supervision, audit, monitoring and incident tooling (`ENGINEERING`); mandatory observation window (`CALENDAR_WAIT`). |
| Parallel work | During observation, prepare the Gate 5 Exness demo environment, retcode/lifecycle fixtures, runbook, rollback and report; do not enable order execution. |
| Owner actions/approvals | Approval for any external service/provider action not already authorized; Gate 4 pass/fail review. Demo authority is requested only after Gate 4 PASS. |
| Earliest realistic start | First eligible market session after Gate 3 PASS and deployment-off verification. |
| Target completion range | Minimum one full market month plus event coverage; realistic 5–7 weeks if no unresolved incident extends the window. |
| Blockers | No service/supervisor, production audit implementation, monitoring/SLO, incident packet, shadow decision ledger, replay/live reconciler or acceptance report exists at R38. |
| Trading mode | **Shadow-only.** `execution_enabled=false`; no order capability. |

### Gate 5 — Exness demo execution validation

| Field | Authority |
|---|---|
| Purpose | Validate the broker lifecycle and reconciliation behavior using the Exness demo environment. |
| Entry criteria | Gate 4 PASS; fresh account/symbol fingerprint; demo deployment and rollback packet PASS; separate owner approval to enable demo execution/external Python. |
| Exit criteria | Frozen demo lifecycle suite covers restarts, rejects, reproducible partial behavior, pending expiry, modifications and OCO races; 100% state reconciliation; zero duplicate exposure; every broker-specific assumption evidenced. |
| Dependencies | Gate 4 (`EVIDENCE`); Exness demo/MT5 behavior (`EXTERNAL_DEPENDENCY`); adapter/retcode mapping and runbook (`ENGINEERING`); demo activation (`OWNER_APPROVAL`). |
| Parallel work | During Gate 4, build and verify the demo environment with execution off. During Gate 5, prepare Gate 6 tiny-live activation, kill, rollback, monitoring and report packets without live activation. |
| Owner actions/approvals | Separate demo activation approval; Gate 5 pass/fail review. |
| Earliest realistic start | First eligible session after Gate 4 PASS and approval. |
| Target completion range | Planning estimate 3–6 weeks; completion is lifecycle-evidence driven, not time driven. |
| Blockers | No production MT5 executor, frozen real retcode mapping, measured reconciliation bounds, demo runbook or broker lifecycle report at R38. Unsupported broker behaviors remain fail closed. |
| Trading mode | **Demo only.** No real money. |

### Gate 6 — tiny-live validation

| Field | Authority |
|---|---|
| Purpose | Validate real execution at the smallest permitted exposure with immediate containment and rollback. |
| Entry criteria | Gates 0–5 PASS; fresh live account/symbol/terms validation; predeclared execution-focused sample and monitoring plan; explicit human real-money approval. |
| Exit criteria | Predeclared sample complete; no critical incident or policy breach; reconciliation and monitoring pass. Performance is reported but cannot alone justify scaling. |
| Dependencies | Gate 5 (`EVIDENCE`); live account and broker (`EXTERNAL_DEPENDENCY`); activation/kill/rollback packet (`ENGINEERING`); explicit activation (`OWNER_APPROVAL`). |
| Parallel work | Packet preparation during Gate 5. During Gate 6, prepare Gate 7 defect list, rollback drill, scaling evidence and per-step approval records; do not scale. |
| Owner actions/approvals | Separate explicit real-money activation; approval of the frozen sample; Gate 6 pass/fail review. |
| Earliest realistic start | Only after Gate 5 PASS and explicit approval; planning estimate 3–6 weeks after Gate 5 start if its evidence completes cleanly. |
| Target completion range | Planning estimate 6–12 weeks; replace with the predeclared sample before activation. |
| Blockers | No current activation packet, predeclared live sample, live-account revalidation or real-money approval. A 0.01-lot cap is an upper bound, not an entitlement. |
| Trading mode | **Tiny-live.** Fixed minimal exposure; Policy A/V1/M1 and all fail-closed controls remain binding. |

### Gate 7 — controlled scaling

| Field | Authority |
|---|---|
| Purpose | Increase exposure only through evidence-backed, reversible, explicitly approved steps. |
| Entry criteria | Gate 6 PASS; predeclared live sample for the proposed step; unresolved-defect list; rollback drill; owner/risk decision. |
| Exit criteria | Each cap increase has its own explicit approval and acceptance evidence; automatic scaling remains prohibited. Gate 7 is an ongoing controlled process, not a one-time unlimited authorization. |
| Dependencies | Gate 6 (`EVIDENCE`); scaling packet/rollback (`ENGINEERING`); each increase (`OWNER_APPROVAL`); continued broker/market operation (`EXTERNAL_DEPENDENCY`). |
| Parallel work | Prepare the next step's evidence and rollback while the current approved cap is observed; never activate the next step early. |
| Owner actions/approvals | Explicit owner approval for every cap increase and any risk-policy/allocation change. |
| Earliest realistic start | After Gate 6 PASS; earliest planning estimate 6–12 weeks after tiny-live activation. |
| Target completion range | First decision realistically 10–16 weeks after Gate 6 activation; subsequent scaling is evidence-driven and has no fixed end date. |
| Blockers | No scaling ladder, step sample, defect/waiver packet or scaling acceptance report exists. No automatic increase above the approved allocation. |
| Trading mode | **Scaled live, bounded by the currently approved step only.** |

## 5. Gate 0 closure queue

| Item | Status/dependency | Earliest eligible action | Parallel preparation now |
|---|---|---|---|
| G0-04 | `EXTERNAL_DEPENDENCY`, `EVIDENCE`; no qualifying natural transition observed | Event-dependent | Continue GET-only monitoring; do not cause an outage or manufacture a transition. |
| G0-05 | `FAIL` for immutable R4; successor R5 is `PREPARED_NOT_REGISTERED` | Earliest R5 result 2026-12-09 only under the stated publication/embargo/window assumptions | Seal the chronological development bundle, complete all hashes, publish registration before future data, enforce one full UTC embargo day, and never open/extend/retune the evaluation. |
| G0-06 | `CALENDAR_WAIT`, `EXTERNAL_DEPENDENCY`, `EVIDENCE`; September checkpoints elapsed unverified | After fresh prospective registration of exact rendered XAU rows | Capture new normal rollover and weekend BEFORE/INSIDE/AFTER sets; separately wait for and prospectively register the next officially published XAU holiday boundary. No backfill. |
| G0-07 | `OWNER_APPROVAL`, `EVIDENCE`; R34/R35 immutable fail-closed; new campaign prepared only | After protocol publication and separate operational approval | Complete static/offline preparation for a distinct one-attempt campaign using two independent MT5 observers plus an OS observer. No disconnect/restart/mutation yet. |
| G0-08 | `EVIDENCE`; requires successor G0-05 PASS | Only after admitted R5 PASS | Keep stress-artifact/account-evaluation packet and hash bindings ready; do not start. |
| G0-12 | `EVIDENCE`; requires successor G0-05 PASS and new untouched holdout | Only after admitted R5 PASS | Keep replay engine/report preparation separate from the unopened holdout; do not start. |
| G0-14 | `OWNER_APPROVAL`, `EVIDENCE`; requires G0-12 PASS | Same/next UTC day after approval and G0-12 PASS | Offline request/response validation only; stop and ask before any Sol action. |

## 6. Preparation control plane

R40 adds machine-readable preparation records to reduce Gate 1–4 startup delay. They remain subordinate to this roadmap and to their referenced frozen contracts.

| Artifact | Purpose | Current authority |
|---|---|---|
| `phase0/roadmap/GATE_1_4_PARALLEL_PREPARATION_REGISTER_R40.json` | Parallel task/dependency register with every premature implementation or external action explicitly blocked | Preparation scheduling only; no gate credit |
| `phase0/roadmap/GATE_1_3_REQUIREMENT_TEST_TRACEABILITY_R40.json` | Requirement-to-existing-oracle and future product/adversarial/replay test mapping | Traceability only; existing oracles are not product evidence |
| `phase0/roadmap/GATE_1_RELEASE_MANIFEST_SCHEMA_R40.json` | Frozen release-identity fields and execution-off defaults | Planning schema only; no release exists |
| `phase0/roadmap/GATE_4_SHADOW_RECORD_SCHEMAS_R40.json` | Shadow decision, incident and acceptance record shapes | Planning schema only; Gate 4 has not started |
| `phase0/roadmap/GATE_1_BUILD_TEST_PIPELINE_R41.json` | Existing oracle commands and the future product CI/release ordering | Orchestration preparation only; no product stage executed |
| `phase0/roadmap/GATE_2_FAULT_SCENARIO_SCHEMA_R41.json` | Per-scenario simulated fault evidence contract | Planning schema only; no real fault or Gate 2 evidence |
| `phase0/roadmap/GATE_3_TRIAL_REGISTRY_SCHEMA_R41.json` | Append-only all-trial and holdout-opening bindings | Planning schema only; no trial/holdout opened |
| `phase0/roadmap/GATE_4_OBSERVATION_REGISTRATION_SCHEMA_R41.json` | Pre-start duration/coverage/tolerance/incident identity bindings | Planning schema only; Gate 4 has not started |
| `phase0/roadmap/GATE_1_PORT_CONTRACT_CATALOG_R42.json` | Logical catalog of existing frozen component boundaries and denied capabilities | Index only; no new signature or implementation |
| `phase0/roadmap/GATE_2_FAULT_MATRIX_REGISTER_R42.json` | Eleven frozen simulated-fault families prepared for later artifact binding | Register only; no scenario executed |
| `phase0/roadmap/GATE_3_ACCEPTANCE_REPORT_SCHEMA_R42.json` | Frozen replay acceptance fields and procedure in machine-readable form | Schema only; no trial or holdout opened |
| `phase0/roadmap/GATE_4_MONITORING_REGISTER_R42.json` | Pre-start monitoring inventory with thresholds deferred to hash-bound Gate 1–3 outputs | Inventory only; Gate 4 has not started |
| `phase0/roadmap/G0_05_R5_PREREGISTRATION_DRAFT.json` | Successor R5 design, unchanged frozen acceptance and 63-day sample-sufficiency window | Draft only; not registered until the development bundle is sealed and the complete registration is published |
| `phase0/roadmap/G0_06_PROSPECTIVE_CAPTURE_PLAN_R43.md` | Fresh normal/weekend capture and future officially published XAU holiday readiness | Preparation only; missed September checkpoints are not backfilled |
| `phase0/roadmap/G0_07_PROSPECTIVE_CAMPAIGN_V2.md` | Stronger observation, safety controls, one-attempt budget, reconciliation, rollback and exact owner actions | Protocol preparation only; no operational action authorized |
| `phase0/roadmap/G0_07_CAMPAIGN_V2_REGISTRATION.json` | Machine-readable G0-07 campaign identity and frozen acceptance | Prepared, not operationally approved or started |
| `phase0/roadmap/GATE_0_RECOVERY_CRITICAL_PATH_R43.json` | Conditional dependency/parallelism/forecast register | Planning only; no item promoted and no external action authorized |

The preparation register is the task-level execution view. This master remains the only forward-looking gate/schedule authority.

## 7. Change control

- Update this roadmap after an admitted gate result, a critical-path dependency change, or a material evidence-backed defect.
- Do not turn planning estimates into gate criteria without an accepted Decision Log entry.
- Do not mark a gate PASS from a roadmap statement. Only its frozen evidence procedure may do so.
- Do not publish to private `main` without the separately required publication approval.
- Do not contact a provider, purchase/trial, run a restart/disconnect drill, send a real alert, perform an OpenAI action, touch a broker, or enable trading without the separately required authority.
