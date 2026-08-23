# Empirical-calibration workflow validation report

**Date:** 2026-08-23  
**Result:** PASS — 8/8 offline tests  
**Data:** synthetic derived observations only  
**Trading authorization:** none

The workflow binds an admitted bundle, derived-data hash, code and split map;
requires a frozen training cutoff, sealed holdout, four-session normal coverage,
post-event samples and multiple complete recoveries; and produces training-only
quantile candidates for shock, normalization, spread, adverse latency-move,
gap and round-trip cost stresses.

Holdout rows, chronology/hash changes, insufficient session/event coverage,
invalid freeze order, unresolved rights and validation-to-training leakage all
fail closed. The adverse latency-move field is explicitly a non-trading
slippage proxy, not execution-slippage evidence.

Real licensed observations, independent review, untouched validation and a
frozen runtime/stress artifact remain required. No numeric runtime threshold was
selected here.
