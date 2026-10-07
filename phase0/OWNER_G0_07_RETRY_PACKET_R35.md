# G0-07 corrected retry packet — R35

The R34 attempt stopped before the `DISCONNECT` record because MT5 did not
expose `connected:false` inside 60 seconds. The adapter restore path completed,
and none of the seven frozen observations was appended.

R35 makes only evidence-led corrections:

- reject more than one active IPv4 default-route adapter before disruption;
- verify the selected adapter actually enters `Disabled` state;
- allow up to 150 seconds for MT5 to expose the genuine disconnect;
- retain a four-minute independent adapter recovery watchdog; and
- bind the current retry's immutable PRE/POST exposure hashes while preserving
  the earlier failed-attempt record instead of deleting or rewriting it.

If the owner approves one corrected retry, keep VNC available and run from an
elevated PowerShell console at the repository root:

```powershell
git pull --ff-only origin main; if ($LASTEXITCODE -eq 0) { powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\vps_reliability\run_g0_07_fault_drill.ps1 }
```

The frozen event set, zero-exposure requirements, external-Python-disabled
barrier, no-broker-mutation rule, prefix verification, recovery oracles and
final reconciliation are unchanged. Any second failure stops closed and is not
automatically retried.

