# G0-07 one-command execution packet — R34

Authority remains the owner's bounded R31 approval. This wrapper automates only
`DISCONNECT`, `RECONNECT`, `PYTHON_RESTART`, `MT5_RESTART`, `WINDOWS_RESTART`,
`CLOCK_CHECK` and `BUILD_CHECK` after the accepted private baseline. It cannot
submit, modify, cancel or close an order and cannot enable external Python
trading.

Keep the ForexVPS VNC console available. In an **elevated PowerShell console**
at the repository root, run this single command:

```powershell
git pull --ff-only origin main; if ($LASTEXITCODE -eq 0) { powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\vps_reliability\run_g0_07_fault_drill.ps1 }
```

The wrapper pins authoritative `main`, reruns offline controls, proves zero
positions and zero pending orders, verifies the disabled barrier and accepted
prefix, then performs only the frozen sequence. A separate SYSTEM watchdog
restores the selected adapter if needed. MT5 receives a graceful close request;
failure to close stops the drill without force-terminating it.

Windows restarts once. If Windows requires sign-in, use VNC to sign back into
the same Windows account; the registered interactive task resumes automatically
and no second command is needed. Any ambiguous adapter, changed identity,
enabled/unknown barrier, unhealthy recovery, stale tick, unexpected build,
chain defect or nonzero/unknown exposure fails closed.

Only a final `PASS` summary hash, matrix hash, pre/post exposure hashes and event
timestamps may be published. All raw evidence remains under
`C:\Gate0Private\VpsFaultMatrix-R19`.
