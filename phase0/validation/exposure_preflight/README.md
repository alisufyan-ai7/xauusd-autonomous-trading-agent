# G0-07 read-only exposure preflight

This bounded helper closes one operational safety gap in the approved G0-07
packet: confirm that the connected account has zero open positions and zero
pending orders before the disruptive matrix, then reconcile the same condition
after recovery.

The adapter exposes only terminal status plus `positions_get()` and
`orders_get()`. It cannot submit, check, modify, cancel or close an order; log
in; select a symbol; control a process; use the network directly; or send a
message. Any unknown state, connection failure, enabled external-Python API,
open position or pending order fails closed.

Private records are append-only, SHA-256 chained and contain counts only. Keep
them outside the repository.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\phase0\validation\exposure_preflight\run_exposure_preflight.ps1 `
  -Output C:\Gate0Private\VpsFaultMatrix-R19 `
  -Phase PRE_DRILL
```

A zero exit code and `PASS_NO_OPEN_EXPOSURE` are required. The same command
with `-Phase POST_RECOVERY` is required after the matrix.
