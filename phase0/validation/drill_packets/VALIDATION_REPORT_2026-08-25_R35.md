# R35 G0-07 fail-closed correction validation

## Result

- Focused G0-07/G0-09 controls: PASS, 51/51 across 7 groups
- New regression beyond R34: 1
- Aggregate controlled registry: PASS, 358/358 across 25 groups
- Python compilation: PASS
- Gate 0 matrix: unchanged at 6 PASS / 8 PENDING
- R34 G0-07 attempt: fail closed before first event append
- G0-09: unchanged, not configured and not executed
- External Python trading: disabled

## Concrete defects corrected

The first real R34 attempt proved that the 60-second wrapper observation bound
could expire before MT5 exposed its disconnected state. It also proved that a
retry would append another valid PRE_DRILL record and later be rejected by the
R34 exact-two-record reconciliation, even though immutable history should be
preserved.

R35 rejects multiple active default-route adapters, verifies the selected
adapter enters `Disabled`, observes for at most 150 seconds under a four-minute
SYSTEM recovery watchdog, and binds the latest contiguous PRE/POST pair by its
immutable hashes without deleting earlier attempts. The frozen R31 scenario
set, health thresholds and acceptance oracle are unchanged.

No R35 restart, disconnect, canary, broker mutation, OpenAI call or trade was
performed during this correction.
