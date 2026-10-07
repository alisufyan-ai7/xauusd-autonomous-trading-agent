# Immutable multiframe replay-admission validation report R2

**Date:** 2026-08-23  
**Scope:** Offline admission logic over synthetic bytes only  
**Trading authorization:** None

## Result

The combined replay-admission suite passes **18/18 test methods**. The original
child-file gate retains its exact provenance, licensing, chronology, bid/ask
OHLC, gap-evidence, split-registration and byte/hash checks. The new bundle gate
admits only an exact H4/H1/M15 inventory with at least 300/500/1,000 rows,
matching provider/instrument/terms semantics, unique child IDs, ordered sealed
splits, verified child roots and one deterministic bundle root.

Negative tests reject missing or duplicate frames, insufficient rows, cadence
errors, semantics or licensing mismatches, altered child roots, split leakage,
unordered periods and a mutated bundle root. Static import checks preserve the
absence of broker, network, model, process and filesystem-write capability.

## Exact remaining licensed-data blocker

This validates synthetic admission behavior only. Gate 0 still lacks an actual
provider-authorized immutable XAUUSD bid/ask or tick bundle with reviewed rights
for automated internal use, local retention, derived outputs, historical replay
and audit retention; authoritative session/holiday evidence; account-compatible
symbol semantics; frozen source hashes; and a preregistered chronological
split/embargo/holdout map. No data was purchased, downloaded or opened here.
