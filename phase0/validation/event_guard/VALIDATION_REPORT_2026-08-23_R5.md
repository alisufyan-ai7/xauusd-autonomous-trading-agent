# Official-source Event Guard validation report R5

**Date:** 2026-08-23 UTC  
**Result:** PASS — 32/32 offline tests; private acquisition rerun pending  
**Trading authorization:** none

The first R10 private VPS capture passed the complete Windows suite and produced
a valid three-record hash chain for BLS, Federal Reserve and Census. Independent
recomputation matched every record digest:

- BLS record `3c4c28e74235c44beed0203e0f605e58cd70425326b625bf94597872a7c23792`;
- Federal Reserve record `61c984b8369b8bcb533c905be7cf49246b6e145b9583b384db40ad0d673106af`;
- Census record `e9daaf43551291dc2a48c2654f3864a62ae9cd19c7eec3ba8fa77622c53c212b`.

DOL rejected for the already registered absence of an admitted authoritative
exception-aware forward schedule. BEA rejected for `SCHEMA_DRIFT`, which review
traced to a false positive in the R10 schema validator: the official JSON root
contains a `file_last_updated` string alongside its release objects. The event
parser already ignored this non-event field safely.

R5 narrowly admits that named metadata field only when it is a string. All
release entries must still be objects with string `release_dates` arrays, the
release map must be non-empty, and any other scalar root field remains rejected.
Existing parser and fingerprint tests now include the observed official shape
and an unknown-scalar negative.

No raw response body, private manifest, identity, account data, screenshot or
ZIP is published. BEA operational acquisition remains pending one controlled
rerun; DOL remains fail-closed. External Python trading remains disabled.
