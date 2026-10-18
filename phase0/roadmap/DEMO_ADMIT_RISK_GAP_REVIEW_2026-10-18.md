# DEMO-ADMIT risk-binding review — fail-closed pre-admission findings

**Date:** 2026-10-18; **examined merged base:** `ccaa8338aecee8bd3afbc358644410dff6c512e5`.  
**Status:** `OPEN_BLOCKING_REVIEW_FINDINGS`; offline static review only. No broker/VPS action and no new test run claimed.

## Evidence from actual code

- `src/xauusd_agent/risk/policy_a.py`: `PolicyAInput` takes volume, account margin/equity and adverse-cost deductions; `evaluate_policy_a` enforces 0.01-lot V1 and projected M1 margin/free-margin floors. It does **not** take protective-stop price or compute `L_price`, planned loss-to-stop, Policy A USD per-trade 0.25%/$25, concurrent $50, daily $75, weekly $150, or drawdown $500. The frozen Phase 0 Policy A specification *does* require these controls.
- `demo_adapter/src/xauusd_demo/risk_binding.py`: `evaluate_bound_demo_risk` maps the calibration and account fields to that M1/V1 evaluator and passes `protective_stop_present=True`, but never prices the supplied `request.stop_loss` or computes a USD stop-loss amount. **A protective stop being present is not proof that its monetary loss is within Policy A.**
- `demo_adapter/src/xauusd_demo/mt5_demo.py`: `_build_request` verifies stop direction/distance and volume but does not test worst executable entry-to-stop monetary loss. It calls `trade_stops_level` with `or 0`, so missing metadata can act like a zero restriction. Quote freshness and a live calibrated spread limit are not checked before submission.
- `demo_adapter/src/xauusd_demo/risk_binding.py`: `DemoRiskCalibration.validate` checks SHA-256 *format*, non-negative Decimals, monotonic stress, and `DEMO_LIFECYCLE_ONLY` scope; the exact object hash is checked against policy. There is not yet an independent source-evidence authenticity or calibration admission verifier. The hash binds supplied bytes, not the truth of their provenance.
- `demo_adapter/src/xauusd_demo/mt5_demo.py`: the `preflight` report defaults a displayed control state to `KILLED` when no control store is configured; submission itself does require a real control. The read-only report should distinguish `NOT_CONFIGURED` from a durable verified `KILLED` state.

## Blocking correction criteria (successor implementation; no approval to merge/deploy/activate)

1. Calculate worst-case loss to real validated protective-stop price for each admissible 0.01-lot order, including verified cost/round-trip and gap allowances and exact broker pricing/symbol specification. Enforce frozen Policy A per-trade USD cap and remaining concurrent/day/week/drawdown budgets from independently reconciled same-snapshot state; no field defaults to zero and no implicit use of fake zero exposure beyond a fresh broker check.
2. Fail closed if stop-distance metadata is absent/invalid, or if tick timestamp, quote validity, runtime spread, symbol calculation or fee/swap data are stale/unknown. Re-evaluate on state change; no broker call capability while building/tests run.
3. Independently verify calibration source artifact SHA-256, component/coverage/fee/swap claims, `DEMO_LIFECYCLE_ONLY` scope and exact five-field object hash before admission. Reject unsupported zero, hash mismatch, stale evidence, identity mismatch.
4. Correct/verify preflight reporting of true durable control existence and state. Keep `KILLED`/quarantine/owner-arm semantics unchanged.
5. Add deterministic adversarial unit tests: very distant stop despite 0.01 lot, missing commission/swap/gap, manipulated source-hash string, stale/widened spread, absent stops-level, mismatched object hash, conflicting snapshot, unexpected exposure and failure after journal reservation. Prove no risk-increasing broker call on all rejected paths.

**Interpretation:** PRs #5 and #6 remain legitimately merged with their previously passed tests. These are uncovered admission-level coverage gaps; they do not retroactively erase the green CI or turn earlier failure evidence into success. Existing R2 is not deployable for demo activation, and DEMO-ADMIT remains **BLOCKED** until source-backed calibration *and* these controls are reviewed and accepted.

**Approval boundaries:** This document registers review findings and proposed future correction tests only. No new code, PR merge, VPS staging, MT5 execution switch, permit, demo action, or real-money authority is granted.
