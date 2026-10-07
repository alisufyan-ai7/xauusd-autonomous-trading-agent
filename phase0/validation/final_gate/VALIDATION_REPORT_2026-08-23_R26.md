# Final Gate 0 matrix validation report — R26

**Date:** 2026-08-23  
**Result:** PASS — 11/11 offline tests  
**Derived matrix:** 5 PASS / 9 PENDING  
**Trading authorization:** none

R26 closes a concrete R25 promotion defect. Artifact hash matching, typed
provenance and a well-formed `ADMITTED` label were still sufficient for a new
self-asserted receipt to promote a pending claim. The oracle now freezes the
exact six previously admitted claim/path/hash/provenance tuples. Any new claim
requires a later controlled evidence review and Decision Log revision before
it can enter the registry.

Status editing, synthetic pending receipts, changed/missing artifacts, unsafe
paths, duplicate claims, invalid times, private-content publication, trading
authorization and external-Python enablement all fail closed.
