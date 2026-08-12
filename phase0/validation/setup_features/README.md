# Raw OHLC Feature Oracle

This package independently derives deterministic setup primitives from chronological synthetic OHLC bars. It does not accept precomputed family predicates and contains no MT5, network, model, filesystem-write, or order API.

Run:

```text
python -m unittest -v test_feature_oracle.py
```

Coverage includes completed-bar exclusion, timestamp/OHLC/gap/warm-up validation, Wilder ATR/RSI/ADX and DI, seeded EMA, confirmed pivots, TPB retracement zones and confirmation timing, rejection geometry, BRT breakout/retest geometry, FBR breach/reclaim/hold geometry, RSR boundary location, MOC compression/trigger geometry, tick-conservative normalization, reward/risk threshold crossing, and long/short mirror properties.

This is a material closure increment, not the complete P0-SETUPS-001 golden corpus. Full family state sequences, every normative predicate, RSR window construction, TPB zone lifecycle, cross-timeframe fixture binding, session/news distributions, and the licensed registered replay remain incomplete. No output authorizes trading.
