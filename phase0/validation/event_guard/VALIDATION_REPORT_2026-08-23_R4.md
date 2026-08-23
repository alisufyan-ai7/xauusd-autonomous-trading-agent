# Official-source Event Guard validation report R4

**Date:** 2026-08-23 UTC  
**Result:** PASS — 32/32 offline tests; operational admission fail-closed  
**Trading authorization:** none

The first owner VPS execution of R3 exposed a Windows packaging defect before
private capture: Python 3.12 could not resolve `America/New_York` because the
host did not provide an IANA timezone database. Four DST-dependent tests failed
for this single environmental reason; 26 other tests passed.

R4 pins the Python Software Foundation `tzdata==2026.3` pure-Python wheel by its
PyPI SHA-256 and adds a PowerShell runner that performs, in order:

1. hash-required, binary-only dependency installation;
2. the complete offline test suite; and
3. read-only official-source capture to a required private path outside the
   repository.

The runner refuses to capture after an installation or test failure. The oracle
also reports a deterministic missing-timezone diagnostic. Two regression tests
freeze the dependency pin/hash and the install-test-capture ordering.

No raw owner output, private evidence, identity, account data, screenshot or ZIP
is included. Live acquisition is still pending; the eventual all-source capture
is expected to remain `FAIL_CLOSED` while the DOL forward-schedule requirement
is unresolved. No trading or external-Python enablement follows.
