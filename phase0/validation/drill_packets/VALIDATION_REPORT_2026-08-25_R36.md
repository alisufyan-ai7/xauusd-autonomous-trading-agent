# R36 G0-07 corrected-retry evidence record

## Result

- Authoritative R35 revision: `060bddfe68f0b63836e6cd39d8cc3d704f66a5ec`
- VPS G0-07 controls before disruption: PASS, 30/30
- Operational result: FAIL CLOSED before first post-baseline event append
- Exact failure: `DISCONNECTED recovery was not observed within 150 seconds.`
- Selected adapter: entered `Disabled` state
- Adapter recovery: succeeded by wrapper control flow with no reported restore error
- Later frozen events: not started
- R34 failed attempt: preserved unchanged
- Third retry: not authorized
- Gate 0 matrix: unchanged at 6 PASS / 8 PENDING
- External Python trading: disabled

## Claim boundary

The R35 wrapper did not retain the final WAIT reason emitted by its read-only
state probe. The available transcript therefore proves only that the required
`DISCONNECTED` predicate was not observed within the registered bound. It does
not distinguish whether MT5 remained connected or the Python observer was
unavailable while the selected adapter was disabled.

No `DISCONNECT` record or later restart/fault record was appended. No broker
mutation, demo/live order action or trading authorization followed.
