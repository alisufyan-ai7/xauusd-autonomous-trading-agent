# Gate 0 R19 — first private VPS action packet

**Scope:** non-disruptive read-only baseline only  
**Do not perform:** network disconnect, Python/MT5/Windows restart, alert send,
API call, demo/live trade, or external-Python enablement

Run only after the sanitized R19 commit has been reported on private `main`.
Keep MT5 **Disable automated trading via external Python API** enabled.

From the repository root on the VPS:

```powershell
git pull --ff-only
git rev-parse HEAD

py -3.12 -m unittest -v `
  phase0.validation.session_evidence.test_session_evidence `
  phase0.validation.margin_evidence.test_margin_evidence `
  phase0.validation.alert_evidence.test_alert_evidence `
  phase0.validation.vps_reliability.test_reliability_oracle `
  phase0.validation.vps_reliability.test_private_probe
```

If and only if all tests pass, create three private artifacts outside the
repository. Use fresh directory names; the margin and canary wrappers reject an
existing output directory.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\phase0\validation\margin_evidence\run_private_snapshot.ps1 `
  -Output C:\Gate0Private\Margin-R19-BASELINE

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\phase0\validation\alert_evidence\run_prepare_private_canary.ps1 `
  -Output C:\Gate0Private\Alert-R19-PREPARED-NOT-SENT

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\phase0\validation\vps_reliability\run_private_probe.ps1 `
  -Output C:\Gate0Private\VpsFaultMatrix-R19 `
  -Event BASELINE `
  -ScenarioId VPS-R19-BASELINE-1
```

Expected public-safe outputs are test PASS lines and three short JSON summaries.
Do not paste or upload `PRIVATE_MARGIN_SNAPSHOT.json`, `PRIVATE_HMAC_KEY.bin`,
`PRIVATE_CANARY.json`, `PRIVATE_RECEIPT_TEMPLATE.json`, Windows Time output, or
`vps_probe_records.jsonl`. Preserve them only under `C:\Gate0Private`.

Stop and report only the console output if any command fails closed or reports
that external Python trading is not disabled. Separate action packets will be
issued later for genuine session boundaries, controlled faults and real alert
delivery; none is authorized by this packet.
