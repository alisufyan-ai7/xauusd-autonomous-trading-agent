# Gate 0 Corpus Execution Report — 2026-08-12

**Scope:** offline deterministic tests only  
**Broker/network calls:** none  
**Trading authorization:** none

## Objective results

| Suite | Normative coverage | Result |
|---|---:|---:|
| Risk Governor | RG-001 through RG-052 | PASS — 52/52 vectors |
| Analyst contract | AI-001 through AI-035 | PASS — 35/35 vectors |
| Replay acceptance oracle | RA-001 through RA-015 | PASS — 15/15 vectors |
| Setup/execution implemented suite | 21 test methods | PASS — 21/21 |
| Raw-OHLC setup-feature oracle | 21 test methods | PASS — 21/21 |
| VPS diagnostic package tests | 3 test methods in intended package directory | PASS — 3/3 |

The Risk Governor and Analyst suite also passed duplicate-key rejection, canonical-decimal boundaries, and the rule that model confidence has no deterministic authority. The replay suite checked exact failure reasons and boundary behavior. The setup/execution suite exercised all five registered families, common fail-closed locks, R:R and stop boundaries, adverse-cost monotonicity, selector behavior, setup-key behavior, allowed/unlisted state transitions, single-attempt fencing, uncertainty quarantine, restart behavior, attribution, closure conservation, and exit-volume bounds. The separate raw-OHLC oracle independently derived completed-bar selection, data integrity, Wilder ATR/RSI/ADX and directional indices, seeded EMA, confirmed pivots, rejection/breakout/reclaim/momentum geometry, conservative tick normalization and long/short mirror properties.

## Non-passing acceptance areas

Green unit tests do not complete Gate 0:

1. The original setup oracle accepts precomputed predicates. A new independent raw-OHLC oracle closes core feature, timestamp/look-ahead, mirror and tick-normalization coverage, but does not yet bind every cross-timeframe feature into every TPB/BRT/FBR/RSR/MOC lifecycle predicate. Full P0-SETUPS-001 golden-corpus acceptance remains **INCOMPLETE**.
2. Execution modeling exposed two specification defects. Version 1.0.1 corrected them with a total restart table and typed precedence; the exhaustive transition/restart/precedence suite then passed 21/21. Broker-specific MT5 mappings, timing, partial-fill behavior, and emergency runbooks remain later validation dependencies.
3. Replay acceptance logic is verified, but no licensed immutable historical dataset, pre-registered split map, actual strategy ledger, or unopened holdout exists. Strategy replay remains **INSUFFICIENT_EVIDENCE**.
4. Analyst contract logic is verified offline. No live model benchmark has run; there is no owner-approved API project/privacy configuration/spend ceiling or pinned model snapshot.

## Conclusion

No frozen safety invariant failed in the implemented corpora. The two execution-specification defects are closed without weakening fail-closed behavior. Gate 0 remains incomplete because required evidence and full setup golden-corpus coverage are absent. No result in this report authorizes external model calls, broker calls, demo trading, or real trading.
