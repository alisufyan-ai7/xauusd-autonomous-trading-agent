# Replay Acceptance Corpus Execution Report

**Date:** 2026-08-11  
**Authorization:** offline deterministic testing only  
**Architecture:** Draft 1.0 acceptance thresholds preserved unchanged

## Executed scope

An executable acceptance oracle was created for the mandatory validity and quantitative gates in `REPLAY_BACKTEST_METHODOLOGY_AND_ACCEPTANCE.md`. Fifteen frozen vectors cover:

- one exact passing case at permitted boundaries;
- fail-closed missing input;
- insufficient prospective sample evidence;
- non-positive expectancy;
- confidence-bound strictness;
- DSR/PBO boundaries;
- drawdown ceiling;
- month/session concentration;
- best-five-trade and best-fold removal;
- walk-forward fold fraction;
- double-cost sensitivity;
- a policy-invariant violation.

Command:

```text
cd phase0/tests
python -m unittest -v test_replay_acceptance.py
```

Objective result: **PASS — 15/15 vectors; 0 failures; 0 errors.**

## Independent checks and limitation

Vector IDs are required to be continuous from `RA-001` through `RA-015`; expected failure reasons are checked exactly, not only the top-level verdict. Threshold equality behavior matches the frozen prose: DSR `0.95`, PBO `0.20`, drawdown USD `500`, month share `0.50`, session share `0.60`, and fold fraction `0.75` pass; values required to be strictly above `-0.05R` fail at equality.

This validates the acceptance logic, not strategy profitability. No licensed immutable market dataset, empirical execution-cost model, pre-registered split map, completed strategy ledger, or unopened holdout exists yet. Therefore an actual replay candidate cannot currently be evaluated and must remain **INSUFFICIENT_EVIDENCE**. No test here authorizes shadow, demo, or real trading.

