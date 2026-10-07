# Raw-OHLC exhaustive-lifecycle validation report R4

**Date:** 2026-08-23  
**Scope:** Offline synthetic research oracle only  
**Trading authorization:** None

## Result

The combined setup-feature suite passes **56/56 test methods**. The new
full-count layer binds ten deterministic candidates (five families, LONG and
SHORT) into exact **300 H4 / 500 H1 / 1,000 M15** completed histories and
crosses each fixture with `FILLED` plus all eight frozen cancellation reasons.
That yields **90 deterministic lifecycle paths**.

The oracle verifies chronological cadence, exact history counts and digests,
candidate/history binding, completed-bar no-lookahead, terminal-state latching,
rejection of post-terminal reactivation, and exact cancellation identities. It
has no broker, model, network, process, sizing, margin or order capability.

## Claim limit and remaining blocker

This closes the synthetic full-count lifecycle/cancellation implementation item
only. “Exhaustive” means exhaustive over the frozen ten-fixture and
eight-cancellation registry; it does not mean every possible market path and it
does not establish profitability or robustness. Gate 0 still requires a
provider-authorized immutable multiframe XAUUSD corpus, frozen empirical
session/spread/volatility/event/cost distributions, broker-specific
reconciliation and chronological replay. No output authorizes trading.
