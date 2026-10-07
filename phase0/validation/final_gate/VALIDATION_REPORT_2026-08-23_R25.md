# Receipt-bound final Gate 0 matrix validation report

**Date:** 2026-08-23  
**Result:** PASS — 10/10 offline tests  
**Derived matrix:** 5 PASS / 9 PENDING  
**Gate 0:** INCOMPLETE  
**Trading authorization:** none

R25 corrects a concrete R24 defect: changing all declared item statuses to
`PASS` no longer produces a passing verdict. The evaluator derives each status
from a frozen claim registry plus typed receipts bound to matching SHA-256
values of sanitized artifacts. Missing, modified, duplicated, unrequired,
wrong-provenance, unsafe-path or improperly published private receipts fail
closed.

The oracle has no filesystem, network, broker, model, process, messaging or
write capability. External Python trading remains required to be disabled.
