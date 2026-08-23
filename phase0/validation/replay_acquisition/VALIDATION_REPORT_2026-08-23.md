# Immutable acquisition-protocol validation report

**Date:** 2026-08-23  
**Result:** PASS — 9/9 offline tests  
**Data acquired:** none  
**Trading authorization:** none

The protocol requires an exact rights-evidence hash, provider/entity and active
entitlement, XAUUSD UTC bid/ask semantics, GET-only read-only acquisition,
private output outside the repository, immutable raw bytes, exact H4/H1/M15
inventory, deterministic transformations, and a preregistered chronological
train/validation/purge/embargo/sealed-holdout map. It separately seals every raw
artifact path, size and SHA-256 into one inventory root.

Negative tests reject unclear rights, non-surviving retention, altered terms,
plan mutation, missing/undersized frames, invalid splits, holdout exposure,
random splitting, unsafe acquisition methods and byte/inventory mutation.

The fixture is synthetic. `READY_FOR_AUTHORIZED_ACQUISITION` is procedural
readiness only; no provider is admitted and no download is authorized.
