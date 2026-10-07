# Gate 3 registered historical replay packet

**Status:** implementation-ready plan; registered replay not authorized/open  
**Entry barrier:** Gates 1 and 2 PASS, admitted costs, and a newly registered untouched holdout  
**Current preflight:** `FAIL_CLOSED_NOT_RUN`; R4 remains sealed through 2026-09-23

## 1. Immutable dataset binding

| Binding | Frozen value |
|---|---|
| Provider/instrument/use | Dukascopy XAUUSD; owner-attested personal non-commercial internal replay rights; no redistribution |
| Market range at R28/R3 | `2020-01-01T20:00:00Z` through `2026-08-23T23:30:00Z` |
| Raw inventory | 4,854 files; 128,561,079 bytes; root `759af04439194734a70a0daaa02500ab669fd23a78a54edd25a7f2ba18c24ff5` |
| Derived bundle | root `138749c9c4c89104a115a25ba4854f61dd4baef04694075602e09494b889ea97` |
| Bundle manifest | `d2e41a66ef98c601c9e29e493f0609858e2c06c63c6cb2a921760f62b1b4c5ca` |
| Existing split map | `c103ce427f83423a1e0c7cdd672f8c9d1461930f046d1e7cbe07f59087cd1897` |
| H4 | 10,619 rows; root `99ca8dd2c7aa552c8ca098077e0c7ba6571d36e5ffb6f1a725a64c8b37b22a49` |
| H1 | 39,269 rows; root `c98921fdbb8c1b9e5235b126575fb253673f11c37c76a90a28f3a598370ec7db` |
| M15 | 157,019 rows; root `40e1d46828372927d5af0ff9c1c024104f1668dd45bc9ae02700ce408d7d1c84` |

These bindings prove dataset identity and admission only. The current historical preflight correctly blocks replay because R3 cost stress rejected and its holdout was consumed. After joint R4 PASS, a later extension/new holdout must receive new immutable roots and registration; prior failed holdouts cannot be reclassified.

## 2. Gate 3 build order

1. **Chronological stream:** byte-level bundle admission, split/purge/embargo enforcement, completed-bar clock and authorized-gap handling.
2. **Shared feature/setup runtime:** import the Gate 1 production feature/setup implementation; do not fork replay-only formulas.
3. **Causal decision loop:** only receipt-eligible information at simulated time `t`; record every rejection/no-trade and source outage.
4. **Fill/cost simulator:** bid/ask executable side, frozen first-release 100% final exit, adverse unknown intrabar sequencing, calibrated spread/gap/cost/slippage proxy, missed entry and delayed exit.
5. **Policy/state runner:** shared Risk Governor, Event Guard, session and lifecycle state machine with no broker port.
6. **Immutable trial registry:** every candidate/variant/tool/manual restart, parameter domain, seed, parent, hashes, exclusions and influence declaration.
7. **Decision/trade/rejection ledgers:** canonical records with data/code/config/policy hashes and complete lifecycle.
8. **Statistics:** block-bootstrap confidence, sample/coverage justification, DSR/PBO or predeclared substitute, concentration, drawdown/loss-streak and fold metrics.
9. **Robustness runner:** paired adverse scenarios with fixed decisions/seeds and all predeclared stress/removal/sensitivity cases.
10. **Leakage/determinism/reconciliation:** forming-bar, split, revision, receipt-time and replay/live-feature fixture checks; repeat produces byte-equivalent normalized decisions.
11. **Report/admission:** machine-readable acceptance input, independent evaluator, evidence manifest and sanitized report.

## 3. Required command contract

The Gate 1–3 implementation must provide these stable offline commands. Names below are the required CLI contract to implement; they do not exist at R38 and must not be represented as completed.

```bash
# Re-admit exact H4/H1/M15 bytes and verify the newly registered bundle/split.
python -m xauusd_agent.replay.admit --registration private/gate3/registration.json --bundle private/dukascopy/bundle

# Run development/walk-forward trials only; holdout remains inaccessible.
python -m xauusd_agent.replay.run --registration private/gate3/registration.json --partition development --output private/gate3/runs/development

# Seal the selected candidate and verify no unregistered influencing trial.
python -m xauusd_agent.replay.seal_candidate --registry private/gate3/trials.jsonl --candidate private/gate3/candidate.json --output private/gate3/candidate-seal.json

# One-time holdout opening; command must refuse before every preflight receipt passes.
python -m xauusd_agent.replay.open_holdout --registration private/gate3/registration.json --candidate-seal private/gate3/candidate-seal.json --output private/gate3/runs/holdout

# Run frozen robustness scenarios without changing decisions or acceptance rules.
python -m xauusd_agent.replay.stress --holdout-run private/gate3/runs/holdout --plan private/gate3/stress-plan.json --output private/gate3/runs/stress

# Build machine-readable metrics, independently evaluate, and create sanitized report.
python -m xauusd_agent.replay.report --registration private/gate3/registration.json --runs private/gate3/runs --output private/gate3/report
python phase0/tests/replay_acceptance_evaluator.py private/gate3/report/acceptance-input.json
```

Existing data-admission regression remains:

```bash
(cd phase0/validation/replay_admission && python -m unittest -v test_admission.py test_multiframe_admission.py)
python -m unittest -v phase0.tests.test_replay_acceptance
```

All private data, ledgers, seeds that reveal private evidence, and holdout outputs remain outside the repository. Only sanitized reports and hashes are publication candidates.

## 4. Holdout-opening transaction

The `open_holdout` command is one fail-closed transaction:

1. Confirm Gates 1 and 2 PASS artifact hashes.
2. Confirm R4 and every required cost/normalization component PASS.
3. Verify rights, data/bundle/split/session-gap hashes and exact chronological boundaries.
4. Verify the immutable code/config/policy/feature/setup/fill/statistics/acceptance hashes.
5. Verify purge/embargo durations and that the holdout has never been read by the candidate process/operator workflow.
6. Verify the complete trial registry and selection-adjustment declaration.
7. Append the signed/dated opening receipt before any result is exposed.
8. Permit exactly one candidate run; any preflight mismatch returns `FAIL_CLOSED_NOT_RUN`.

## 5. Frozen statistical acceptance procedure

All mandatory validity gates must pass: lineage, causal/leakage audit, deterministic repeat, complete trial accounting, no replay/live-feature mismatch, zero policy/state violations, and no invalid/silently dropped event.

| Measure | Frozen rule |
|---|---|
| Primary | OOS net expectancy per initial planned risk `R` is positive. |
| Uncertainty | Two-sided 95% interval lower bound is greater than `-0.05R`; point estimate remains positive. Use predeclared dependence-aware bootstrap with at least 10,000 resamples or a preregistered conservative substitute. |
| Sample | Total/setup sample and coverage justified prospectively from effect size, dependence, variance and interval target; sparse result is `INSUFFICIENT_EVIDENCE`. |
| Selection | DSR probability `>= 0.95` and PBO `<= 0.20` where applicable; otherwise the preregistered selection-aware substitute must pass. |
| Policy path | Base and stress drawdown/loss-streak/day/week paths remain inside Policy A; no policy breach. |
| Concentration | No month supplies more than 50% of positive-month profit; no UTC session bucket more than 60%; expectancy excluding best five trades remains `> -0.05R`. |
| Walk-forward | At least 75% of completed OOS folds have non-negative expectancy; aggregate excluding the best fold remains `> -0.05R`. |
| Cost sensitivity | Doubling all modeled variable transaction costs leaves OOS expectancy `> -0.05R`. |
| Robustness | No risk-rule violation, drawdown beyond the approved ceiling or operational inconsistency under the frozen stress suite. Profit under every stress is not required. |

Every family is evaluated separately. Any combined result requires the predeclared portfolio/allocation rule and full multiple-testing accounting. A failed/insufficient holdout is preserved and cannot be retuned into a PASS.

## 6. Required robustness scenarios

- 2x observed median spread plus the calibrated tail-spread schedule.
- Adverse latency/slippage proxy and stop gaps.
- Missed entries and delayed exits.
- Conservative adverse intrabar ordering when tick sequence is unavailable.
- Session/holiday gaps and scheduled/unscheduled shock periods.
- Reasonable neighboring parameters without selecting a new optimum.
- Subperiod, regime, session and setup removal.
- Paired block resampling and data-quality exclusion variants.
- Plausible broker symbol-property variation within the frozen model.
- Replay/live feature fixtures from the same Gate 1 implementation.

## 7. Reporting templates

### Machine-readable acceptance record

```json
{
  "schema_version": "gate3-acceptance-1.0",
  "registration_sha256": "<sha256>",
  "release_manifest_sha256": "<sha256>",
  "bundle_root_sha256": "<sha256>",
  "split_map_sha256": "<sha256>",
  "trial_registry_root_sha256": "<sha256>",
  "holdout_opening_receipt_sha256": "<sha256>",
  "deterministic_repeat": "PASS|FAIL",
  "leakage_audit": "PASS|FAIL",
  "policy_violations": 0,
  "all_trials_reported": true,
  "family_results": [],
  "portfolio_result": null,
  "robustness_result": "PASS|FAIL|INSUFFICIENT_EVIDENCE",
  "verdict": "PASS|FAIL|INSUFFICIENT_EVIDENCE",
  "trading_authorized": false
}
```

### Sanitized report headings

1. Registration and immutable identities
2. Rights/data lineage and split map
3. Trial inventory and selection procedure
4. Causal/leakage/determinism audit
5. Family-by-family OOS results and uncertainty
6. Drawdown, tails, loss streaks and Policy A compliance
7. Month/session/regime/direction/setup concentration
8. PBO/DSR or registered substitute
9. Cost, gap, missed-fill, delay and robustness results
10. Replay/live feature reconciliation
11. Incidents, exclusions, limitations and deviations
12. Machine-derived PASS/FAIL/INSUFFICIENT_EVIDENCE and claim limit

Gate 3 PASS permits Gate 4 shadow consideration only. It restores no execution or trading authority.
