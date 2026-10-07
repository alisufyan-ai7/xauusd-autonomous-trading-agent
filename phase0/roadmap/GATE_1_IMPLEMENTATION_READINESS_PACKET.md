# Gate 1 implementation readiness packet

**Status:** prepared, not authorized to execute  
**Entry barrier:** objective Gate 0 PASS and recorded Phase 1 implementation authority  
**Capability boundary:** documentation and existing offline oracles only; external Python trading remains disabled

## 1. Reuse boundary

Gate 1 must implement the accepted contracts without copying the existing independent oracles into the product path. The oracles remain cross-check authorities.

| Contract area | Frozen authority | Reusable verification |
|---|---|---|
| Risk | `phase0/specifications/RISK_GOVERNOR_POLICY_A_SPEC.md` | 52 `RG-*` vectors; operational-policy V1/M1/E1/P1/A1 tests |
| Setups/features | `phase0/specifications/SETUP_FAMILIES_OBJECTIVE_SPECIFICATION.md` | feature oracle, 35-case registry, five-family mirror/boundary cases, 90 lifecycle paths |
| Analyst boundary | `phase0/specifications/OPENAI_ANALYST_MINIMIZED_CONTRACT.md` plus V1 field/schema/profile/prompt | 35 `AI-*` vectors and runtime/chronology oracles; use null/fake transport in Gate 1 |
| Execution/reconciliation | `phase0/specifications/EXECUTION_RECONCILIATION_IDEMPOTENCY_SPEC.md` | total transition/restart/precedence oracle, CAS and one-attempt fixtures |
| Event/session/shock | frozen news/session/calibration specifications and registrations | Event Guard, session, shock and empirical protocol suites |
| Replay acceptance | `phase0/specifications/REPLAY_BACKTEST_METHODOLOGY_AND_ACCEPTANCE.md` | 15 `RA-*` vectors; evaluator consumes computed metrics only |

## 2. Exact module and build order

Later work may be assigned in parallel, but integration must respect this dependency order.

| Order | Product module/task | Frozen input/output contract | Gate 1 evidence |
|---:|---|---|---|
| 1 | Foundation domain | Exact Decimal/account-currency values; broker integer units; canonical length-prefixed serialization; SHA-256 IDs; UTC and monotonic clocks; typed reason/state enums; immutable snapshots/events | Serialization/hash golden vectors, float/NaN denial, time/identity boundaries |
| 2 | Immutable input ports | Bars, quotes, account/symbol fingerprint, session/calendar state, stress artifact and configuration all carry provenance, freshness and content hashes | Invalid/stale/unknown/identity-drift tests; source allow-list checks |
| 3 | Completed-bar feature engine | H4/H1/M15 completed-bar rules and formulas from `P0-SETUPS-001`; forming bars excluded | Differential output against `feature_oracle.py`; mirror and boundary properties |
| 4 | Setup evaluators and lifecycle | TPB/BRT/FBR/RSR/MOC three-valued predicates, selector precedence, setup identity, fill/eight cancellation terminals | Differential output against golden/registered/exhaustive corpora |
| 5 | Session, Event Guard and shock gates | Frozen health/transition/session/holiday/normalization states; `UNKNOWN` cannot clear a lock | Cross-oracle output plus fail-closed integration tests |
| 6 | Analyst local boundary | Minimized payload builder, strict schema/echo/freshness/fact validator and execution-isolated null transport | AI/runtime vectors; static capability denial; no network call |
| 7 | Risk Governor and normalized risk ledger | Policy A, V1/M1, exact sizing grid, adjusted-equity day/week/drawdown/Q and all subordination rules | RG/operational vectors and monotonicity/differential tests |
| 8 | Persistent journal, lease and outbox | Append-only lifecycle, schema/hash chain, monotonic revision/CAS, single-writer lease and durable one-risk-increasing-attempt fence | Restart replay, crash points, CAS races, byte-equivalent rebuild |
| 9 | Reconciliation engine and broker port contracts | Broker observations authoritative; typed request/result/event mapping; ownership/volume conservation; uncertainty/quarantine | Fake broker only; no live adapter binding; total transition/restart tests |
| 10 | Composition, audit, health, alerts and release | Null execution sink; `analysis_enabled` separate from `execution_enabled`; execution defaults off; append-only audit; bounded supervisor contract | End-to-end deterministic smoke test, capability scan, package/manifest/rollback verification |

No production MT5 order adapter, OpenAI call, credential path or order-capable deployment is needed to pass Gate 1. The broker and Analyst ports use fakes/nulls. A later demo adapter cannot bypass the same frozen ports.

## 3. Requirement-to-test map

| Requirement | Existing oracle evidence to preserve | Product test required |
|---|---|---|
| Fail closed on missing/stale/conflicting/non-finite state | RG invalid-state cases, setup common locks, M1 invalids, Analyst envelope, Event Guard health | End-to-end composed request returns reject/quarantine and emits no broker command |
| Model has no execution/risk authority | AI vectors, strict runtime schema, deterministic selector/governor | Static capability graph and integration assertion that only Governor output can reach fake broker port |
| Protective stop and risk limits mandatory | RG stop/risk vectors, setup reward/risk boundaries | Request-builder contract rejects missing/unsupported SL and any broker normalization that increases risk |
| No martingale/averaging/risk expansion | RG monotonicity, TPB zone sequence, exit-volume conservation | Position-management tests prove loss/history/confidence cannot increase size or widen stop |
| Account/symbol allow-list | Fingerprint collectors and attribution tests | Sealed deployment config and account/symbol-change disablement tests |
| Single writer/one attempt | CAS/duplicate-claim/one-attempt fixtures | Durable store concurrency and crash-boundary integration |
| Reconcile before action | Attribution/history/volume tests, exposure preflight | Journal-to-fake-broker reconciliation blocks unknown exposure and uncertain submission |
| Independent stop/resume authority | E1/P1 policy vectors | Operator kill/resume epoch integration; automated resume prohibited |
| Immutable audit | Existing hash-chain/private evidence patterns | Product journal checkpoint, restore and tamper rejection |
| Readiness cannot be self-declared | Final matrix oracle | CI release gate consumes immutable reports/hashes, not status text |
| Execution disabled by default | external-Python-disabled records and deployment specification | Install/config/account/version/health-change smoke tests all restore execution off |
| Authorized immutable data only | acquisition/admission/rights suites | Source allow-list, rights/provenance and artifact-hash enforcement at input boundary |

## 4. Golden, mutation and property plan

### Golden/differential suites

- Preserve and rerun the 52 `RG-*`, 35 `AI-*` and 15 `RA-*` vectors.
- Preserve the setup/execution corpus and all feature/golden/registered/exhaustive lifecycle fixtures, including the 90 fill/cancellation paths.
- Preserve the operational-policy and Analyst runtime suites.
- Preserve Event Guard, session, replay admission, stress, reliability and evidence-integrity suites as dependency oracles.
- Add differential tests from the product outputs to the independent oracles. An oracle is not imported by product code.

### Critical mutations — zero survivors

- `<`/`<=`, threshold direction, conservative rounding and Decimal-to-float changes in risk, margin, session, spread, freshness and event locks.
- Transition allow-list, typed event precedence and restart-table changes.
- Removal/change of any safety field in snapshot, setup or idempotency hashes.
- CAS/lease/claim fence removal; duplicate submission; volume-conservation/exit-direction inversion.
- Forming-bar admission, look-ahead access or completed-bar timestamp changes.
- `UNKNOWN`/unhealthy-to-clear promotion in any source gate.
- Analyst extra-key, echo, evidence, price, deadline, tool/refusal or state-change checks.

### Required properties

- Risk, cost and volume monotonicity; lower balance/equity never raises a cap; added exposure never lowers committed risk.
- Cash-flow normalization and boundary invariance.
- Long/short mirror and forming-bar invariance.
- Canonical hash stability and sensitivity to every safety field.
- Byte-equivalent state after replaying the same journal.
- Duplicate-event idempotence; omitted/out-of-order events fail closed.
- Terminal states latch; stale/unknown inputs never promote a state.

## 5. CI and test commands

### Existing authoritative commands

```bash
python -m json.tool phase0/PHASE_0_EVIDENCE_MODEL.json >/dev/null
python scripts/validate_records.py
python tools/readonly-evidence-collector/verify_readonly.py
python -m unittest -v phase0.tests.test_risk_analyst_corpora phase0.tests.test_replay_acceptance
(cd phase0/validation/setup_execution && python -m unittest -v test_corpora.py)
(cd phase0/validation/setup_features && python -m unittest -v test_feature_oracle.py test_family_golden.py test_registered_family_corpus.py test_exhaustive_lifecycle_corpus.py)
python -m unittest -v phase0.validation.operational_policy.test_operational_policy
(cd phase0/validation/analyst_runtime && python -m unittest -v test_runtime_contract.py test_replay_sequence_oracle.py)
```

### Gate 1 CI additions to implement

1. One checked-in test registry runs every controlled group on Python 3.12.
2. Linux and Windows jobs run product and oracle suites; no platform-specific path assumptions.
3. Format/type/static capability checks, coverage, property runner, mutation runner, dependency hash verification, secret scan and package build are required jobs.
4. CI validates the canonical Decision Log plus append-only addendum and cross-record status consistency.
5. The release job emits reports and a manifest but cannot deploy or enable execution.

## 6. Release/versioning procedure

1. Freeze a semantic application version and immutable source commit.
2. Freeze dependency lock/hashes, Python architecture, OS target, database schema/migration, model/profile/prompt/config hashes, and MT5 build compatibility declaration.
3. Build once; hash the artifact, SBOM, configuration schema and migration bundle.
4. Run the complete Gate 1 suite against that exact artifact on Linux and Windows; record all tests, mutations, properties, exclusions and tool versions.
5. Generate the release manifest and sanitized validation report; append the decision record without rewriting history.
6. Obtain the required publication/release approval; fast-forward private `main`; verify remote byte hashes and CI.
7. A tag is a documentation/release checkpoint only. It confers no trading authority.

## 7. Deployment checklist — execution off

- Verify byte-exact artifact/manifest, dependency lock, schema, prompt/config and target account/symbol allow-list.
- Install with `execution_enabled=false`; external Python trading remains disabled.
- Apply migrations against a disposable/backup-verified store; verify append-only audit and UTC/clock health.
- Use null/fake broker and null Analyst transports; confirm no credential or network requirement.
- Run startup, config-change, account-change, version-change and failed-health checks; every case must keep execution off.
- Verify supervisor bounded restart/quarantine behavior and log/disk/backup/restore health.
- Record a sanitized deployment-off smoke-test receipt. Do not connect an order-capable adapter.

## 8. Rollback procedure

1. Latch `execution_enabled=false`; do not rely on process shutdown alone.
2. Stop the new service and preserve its immutable journal, logs, artifact and failure report.
3. Verify the prior artifact/config/schema hashes and restore from the versioned backup only through a tested migration/restore path.
4. Rebuild state from the append-only journal and reconcile against the fake/null broker boundary; ambiguity remains quarantined.
5. Start the prior release with execution off and rerun health/identity/audit checks.
6. Append a supersession/incident decision and hash both releases. Never delete or rewrite accepted history.

## 9. Gate 1 acceptance packet

Required outputs are the byte-exact release artifact, manifest/SBOM, requirement-test matrix, full cross-platform test report, golden/differential report, property report, mutation report, coverage/exclusion report, execution-off deployment result and rollback result. Gate 1 cannot pass from the existing 358-test specification baseline alone.

