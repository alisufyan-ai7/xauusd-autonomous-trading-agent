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
| Raw-OHLC setup-feature/lifecycle oracle | 35 test methods | PASS — 35/35 |
| VPS reliability fault oracle | 25 exact scenario traces / 7 test methods | PASS — 25/25 and 7/7 |
| VPS diagnostic package tests | 3 test methods in intended package directory | PASS — 3/3 |

The Risk Governor and Analyst suite also passed duplicate-key rejection, canonical-decimal boundaries, and the rule that model confidence has no deterministic authority. The replay suite checked exact failure reasons and boundary behavior. The setup/execution suite exercised all five registered families, common fail-closed locks, R:R and stop boundaries, adverse-cost monotonicity, selector behavior, setup-key behavior, allowed/unlisted state transitions, single-attempt fencing, uncertainty quarantine, restart behavior, attribution, closure conservation, and exit-volume bounds. The separate raw-OHLC oracle independently derives completed-bar selection, data integrity, Wilder ATR/RSI/ADX and directional indices, seeded EMA, confirmed pivots, rejection/breakout/reclaim/momentum geometry, conservative tick normalization and long/short mirror properties. It now also covers completed H1/M15 binding, raw-H1 RSR range construction, a bounded RSR boundary-cluster lifecycle and one raw-bar-to-advisory-candidate lifecycle slice for every family. The offline reliability oracle exercises restart, reconnect, network, clock, build, disk and identity failures but does not replace controlled VPS observations.

## Non-passing acceptance areas

Green unit tests do not complete Gate 0:

1. The original setup oracle accepts precomputed predicates. The independent raw-OHLC suite now closes core feature, timestamp/look-ahead, mirror, tick-normalization, RSR cluster and one end-to-end lifecycle slice for every family, but it is not exhaustive across every invalidation/cancellation predicate, Zone A/B history, warm-up, session/news/cost distribution or mirror lifecycle. Full P0-SETUPS-001 golden-corpus acceptance remains **INCOMPLETE**.
2. Execution modeling exposed two specification defects. Version 1.0.1 corrected them with a total restart table and typed precedence; the exhaustive transition/restart/precedence suite then passed 21/21. Broker-specific MT5 mappings, timing, partial-fill behavior, and emergency runbooks remain later validation dependencies.
3. Replay acceptance logic is verified, but no licensed immutable historical dataset, pre-registered split map, actual strategy ledger, or unopened holdout exists. Strategy replay remains **INSUFFICIENT_EVIDENCE**.
4. Analyst model selection and the exact Sol runtime contract are verified under their separate reports. Production prompt and chronological non-trading integration evidence remain open; no further API call is authorized.
5. The 25-scenario reliability corpus is simulated. Operational restart/reconnect/network/clock/build/durable-recording observations and authoritative weekly/holiday sessions remain missing.

## Conclusion

No frozen safety invariant failed in the implemented corpora. The two execution-specification defects are closed without weakening fail-closed behavior. Gate 0 remains incomplete because required evidence and full setup golden-corpus coverage are absent. No result in this report authorizes external model calls, broker calls, demo trading, or real trading.
