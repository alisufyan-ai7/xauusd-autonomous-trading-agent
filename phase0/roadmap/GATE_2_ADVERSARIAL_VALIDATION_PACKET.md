# Gate 2 adversarial validation packet

**Status:** prepared, not authorized to execute against a production artifact  
**Entry barrier:** Gate 1 PASS on a byte-exact release candidate  
**Capability boundary:** offline/simulated faults only; G0-07 is not reopened and no restart/disconnect, broker or trading action is authorized

## 1. Purpose and acceptance

Gate 2 binds the actual Gate 1 implementation to every frozen failure mode. Existing Phase 0 oracles are reusable fixtures, not Gate 2 evidence by themselves.

Exit requires:

- a fault-injection matrix and immutable logs for every declared failure mode;
- zero risk-increasing action under uncertain state;
- exact expected quarantine/recovery transitions;
- zero critical surviving mutations; and
- no unexplained deviation or excluded critical path.

## 2. Reusable frozen matrix

| Domain | Existing reusable scope |
|---|---|
| Risk/Analyst | 52 `RG-*`, 35 `AI-*`, non-finite/duplicate/canonical-decimal and confidence-no-authority cases |
| Setup/features | Family negatives, exact boundaries, mirror/no-look-ahead, 90 fill/cancellation paths |
| Execution/reconciliation | Total transitions/restart table/typed precedence; duplicate claim, CAS conflict, uncertain submission, attribution and volume conservation |
| VPS/runtime | 25 exact offline reliability traces, private-chain verifier and exposure preflight tests |
| Event Guard | Source conformance plus revision/move/cancel/disappearance/outage/incomplete-recovery/DST/holiday cases |
| Replay/data | Rights, hash, chronology, split, gap, non-finite, coherence and acceptance vectors |
| Shock/cost | Tail shift, no-look-ahead, normalization gaps and repeated-shock quarantine |
| Analyst runtime | Malformed/refused/tool/injection/late/replayed/state-changed/invented-fact responses |
| Policy/evidence | V1/M1/E1/P1/A1, margin/stress, session, alert/evidence and immutable matrix/hash controls |

The R35 358/358 controlled baseline and R38 focused receipt controls remain regression inputs. They do not prove the future runtime.

## 3. Actual-implementation fault matrix

| ID family | Injected condition | Required observable result | Harness requirement |
|---|---|---|---|
| G2-STATE | Unlisted, duplicate, omitted, out-of-order or conflicting lifecycle event | No risk increase; reject/quarantine; deterministic reason and latched state | Event-stream mutator bound to product journal |
| G2-SUBMIT | Timeout before/after fake fill, delayed/duplicate acknowledgement, late fill after cancel, partial fill | `SUBMISSION_UNCERTAIN`/reconciliation; never duplicate; exact volume conservation | Stateful MT5 protocol simulator with scheduled events |
| G2-STORE | Transaction/CAS/lease/outbox failure; disk full/read-only; torn/corrupt record; crash at each durable boundary | No second attempt; startup quarantine or exact replay; immutable error/audit | Crash-point store adapter and process-restart harness |
| G2-IDENTITY | Account/symbol/build/config/version drift; multiple writers/terminals | Execution off; quarantine; reauthorization/reconciliation required | Sealed-config and identity mutators |
| G2-TIME | Stale/future tick, UTC/monotonic discontinuity, boundary ambiguity | Lock/reject; no favorable boundary synthesis | Injected wall/monotonic clock |
| G2-DATA | Gap, malformed OHLC, forming bar, missing rights/hash, altered split, stale quote | Data invalid/reject; no strategy output reaches broker port | Corpus mutator and provenance/hash substitution |
| G2-RISK | Exact threshold flips, broker normalization, missing cost/margin/cash flow, unknown exposure | Conservative reject/quarantine; never round risk upward | Decimal/broker-grid and ledger boundary generator |
| G2-GUARD | Calendar outage/conflict/revision; session/holiday boundary; shock/normalization interruption | Lock remains until exact healthy recovery; no `UNKNOWN` promotion | Protocol fixtures only; no real provider call |
| G2-ANALYST | Refusal, timeout, truncation, tool content, extra keys, wrong echo, invented values, stale state | Reject and audit; no authority or broker output | Fake Responses protocol fixture only |
| G2-SERVICE | Process death, stale heartbeat, bounded restart exhaustion, dependency unavailable, alert failure | Execution off; bounded retry then quarantine; incident/audit retained | Local service/supervisor simulator |
| G2-EVIDENCE | Log/hash/manifest mutation, secret-shaped content, private path inside repo, missing report | Fail acceptance and publication closed | Artifact mutation/redaction verifier |

No matrix item may call an external broker, OpenAI, Telegram/email provider, or deliberately disrupt the VPS/network. The historical G0-07 R34/R35 evidence remains unchanged.

## 4. Mutation and property requirements

Use the Gate 1 critical mutation list. Add mutations for adapter event mappings, durable commit ordering, supervisor retry/quarantine and report admission. Critical mutant score is 100%; a surviving critical mutant is Gate 2 FAIL. Non-critical exclusions require a line-item justification and cannot include safety math, state transition, execution fence, reconciliation, identity, freshness, source health or audit integrity.

Properties must cover:

- safety monotonicity under worse data, higher cost/risk, staler state and additional exposure;
- exact-once effect from duplicate messages, crash/replay and concurrent workers;
- journal replay determinism and canonical hash stability;
- volume/ownership conservation through partial, cancel, reject and late-fill sequences;
- no terminal-state reactivation;
- recovery only after every frozen healthy/reconciliation boundary is observed; and
- redaction: no secret, credential, account/ticket identifier or private evidence enters a public artifact.

## 5. Harness build order

1. Bind the Gate 1 ports and reason/state enums to an event-driven fake MT5 simulator.
2. Add the injected wall/monotonic clock and deterministic scheduler.
3. Add store/outbox/lease crash points and multi-worker CAS control.
4. Add data/calendar/Analyst protocol fixtures at the frozen ports.
5. Add service/supervisor simulation with execution always off.
6. Add property generators and shrink/replay capture.
7. Add mutation configuration and critical-module allow-list.
8. Add evidence manifest, sanitized report and full requirement-to-fault traceability.

## 6. Offline regression commands

```bash
python -m unittest -v phase0.tests.test_risk_analyst_corpora phase0.tests.test_replay_acceptance
(cd phase0/validation/setup_execution && python -m unittest -v test_corpora.py)
(cd phase0/validation/setup_features && python -m unittest -v test_feature_oracle.py test_family_golden.py test_registered_family_corpus.py test_exhaustive_lifecycle_corpus.py)
python -m unittest -v phase0.validation.operational_policy.test_operational_policy
(cd phase0/validation/event_guard && python -m unittest -v test_event_guard.py test_source_conformance.py)
(cd phase0/validation/event_guard/controlled_evidence && python -m unittest -v test_controlled_evidence.py)
(cd phase0/validation/shock_calibration && python -m unittest -v test_shock_calibration.py)
(cd phase0/validation/analyst_runtime && python -m unittest -v test_runtime_contract.py test_replay_sequence_oracle.py)
(cd phase0/validation/replay_admission && python -m unittest -v test_admission.py test_multiframe_admission.py)
python -m unittest -v phase0.validation.margin_evidence.test_margin_evidence phase0.validation.margin_evidence.test_stress_artifact
python -m unittest -v phase0.validation.vps_reliability.test_reliability_oracle phase0.validation.vps_reliability.test_private_probe phase0.validation.vps_reliability.test_fault_drill_orchestrator phase0.validation.exposure_preflight.test_exposure_preflight
```

The future project-wide Gate 2 command must run the above oracle registry, product fault suites, property suites and mutation suites against the exact Gate 1 artifact. `run_g0_07_fault_drill.ps1` is explicitly excluded.

## 7. Evidence and reporting

The Gate 2 packet must contain:

- release/manifest hash of the Gate 1 candidate;
- complete requirement-to-fault map and declared exclusions;
- deterministic seeds and generated-case replay files;
- immutable per-scenario input/event/output/audit hashes;
- crash-point and concurrency results;
- mutation inventory, survivors and score by critical module;
- property run counts, seeds and minimized failures;
- zero-capability/static scan for external broker/trading actions; and
- sanitized final report with PASS/FAIL derived from machine-readable receipts.

A failed scenario stops Gate 2. Repair creates a new release candidate and reruns Gate 1 plus the complete Gate 2 matrix; evidence is appended, never overwritten.
