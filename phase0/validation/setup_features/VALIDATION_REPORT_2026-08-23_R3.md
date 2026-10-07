# Raw-OHLC registered-family validation report R3

**Date:** 2026-08-23  
**Scope:** Offline synthetic research oracle only  
**Trading authorization:** None

## Result

The combined setup-feature suite passes **45/45 test methods**. The new registry
contains **35 deterministic raw-family cases**: seven per family, ten exact
long/short pass candidates and 25 family-stage or common-safety negatives.

The new checks cover all-family long/short mirror equivalence, forming-bar
exclusion at the family decision slice, and exact/one-side boundaries for TPB
confirmation, BRT's 12-H1-bar retest window, FBR's 0.10-to-0.60 ATR excursion,
RSR's 15% location band, and MOC RSI trigger bounds. Existing tests retain
completed H1/M15 binding, gap/OHLC/warm-up validation, indicator primitives,
RSR range/cluster lifecycle, tick normalization and one candidate slice per
family. No broker, model, network, process, sizing, margin or order capability is
present.

## Remaining setup blocker

This does not yet satisfy every P0-SETUPS-001 Section 10 vector. Still required
are full 300 H4 / 500 H1 / 1,000 M15 chronological fixtures; TPB Zone A
fill/loss/cancel/expiry followed by fresh Zone B histories; every normative
invalidation/cancellation permutation; account-calibrated session, spread,
volatility, event and cost distributions; and reconciliation against an admitted
licensed immutable replay corpus. Therefore setup-corpus closure remains
**INCOMPLETE** and no replay performance is claimed.
