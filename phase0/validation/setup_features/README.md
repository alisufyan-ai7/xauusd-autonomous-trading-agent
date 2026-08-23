# Raw OHLC Feature Oracle

This package independently derives deterministic setup primitives from chronological synthetic OHLC bars. It does not accept precomputed family predicates and contains no MT5, network, model, filesystem-write, or order API.

Run:

```text
python -m unittest -v test_feature_oracle.py test_family_golden.py
```

Coverage includes completed-bar exclusion and H1/M15 decision-time binding,
timestamp/OHLC/gap/warm-up validation, Wilder ATR/RSI/ADX and DI, seeded EMA,
confirmed pivots, TPB retracement zones and confirmation timing, rejection
geometry, BRT breakout/retest geometry, FBR breach/reclaim/hold geometry, raw-H1
RSR range-window construction and boundary-cluster lifecycle, RSR boundary
location, MOC compression/trigger geometry, tick-conservative normalization,
reward/risk threshold crossing, long/short mirror properties, and one bounded
raw-bar-to-advisory-candidate lifecycle slice for each of the five families.

The combined suite passes 35/35 tests. This remains a material closure increment,
not the complete P0-SETUPS-001 golden corpus. The RSR window oracle fails closed
if a single window admits multiple qualifying boundary pairs because the frozen
specification has no boundary-pair tie-break. Exhaustive invalidation/cancellation
sequences, every normative predicate, TPB Zone A/Zone B state history,
cross-timeframe warm-up fixtures, session/spread/news distributions, cost-stress
geometry and the licensed registered replay remain incomplete. No output
authorizes trading.
