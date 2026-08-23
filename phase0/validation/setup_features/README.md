# Raw OHLC Feature Oracle

This package independently derives deterministic setup primitives from chronological synthetic OHLC bars. It does not accept precomputed family predicates and contains no MT5, network, model, filesystem-write, or order API.

Run:

```text
python -m unittest -v test_feature_oracle.py test_family_golden.py test_registered_family_corpus.py test_exhaustive_lifecycle_corpus.py
```

Coverage includes completed-bar exclusion and H1/M15 decision-time binding,
timestamp/OHLC/gap/warm-up validation, Wilder ATR/RSI/ADX and DI, seeded EMA,
confirmed pivots, TPB retracement zones and confirmation timing, rejection
geometry, BRT breakout/retest geometry, FBR breach/reclaim/hold geometry, raw-H1
RSR range-window construction and boundary-cluster lifecycle, RSR boundary
location, MOC compression/trigger geometry, tick-conservative normalization,
reward/risk threshold crossing, long/short mirror properties, and one bounded
raw-bar-to-advisory-candidate lifecycle slice for each of the five families.

The full-count synthetic layer binds each candidate into exact 300-H4,
500-H1 and 1,000-M15 completed histories. It covers five families in both
directions and crosses each fixture with `FILLED` plus every one of the eight
frozen cancellation reasons, for ten history fixtures and ninety lifecycle
paths. It verifies history identity, chronology, cadence, no-lookahead,
terminal-state latching and non-reactivation.

The suite now includes a 35-case raw-lifecycle registry: seven cases per family,
comprising exact long and mirrored-short passes plus 25 family-stage/safety
negatives. Ten additional test methods enforce registry identity, five-family
mirror equivalence, forming-bar no-lookahead, and exact/one-side TPB confirmation,
BRT retest-window, FBR excursion, RSR location and MOC RSI boundaries.

This remains synthetic specification evidence, not empirical market validation.
The RSR window oracle fails closed
if a single window admits multiple qualifying boundary pairs because the frozen
specification has no boundary-pair tie-break. Account-calibrated session,
spread, volatility, event and cost distributions, broker-specific TPB behavior,
and reconciliation against an admitted licensed immutable replay remain open.
The exhaustive claim is limited to the frozen ten-fixture/eight-cancellation
normative registry; it is not a claim about every possible market path or
performance. No output authorizes trading.
