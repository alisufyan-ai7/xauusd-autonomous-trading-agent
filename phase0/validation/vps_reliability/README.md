# Gate 0 VPS reliability fault oracle

The approved R31 packet adds a separate read-only exposure preflight because
this observer intentionally cannot query positions or pending orders. That
bounded helper must report zero for both before disruption and after final
recovery. It cannot mutate or close exposure.

This directory converts the restart/reconnect/network/clock/build failure matrix
into a deterministic, standard-library-only offline oracle. It contains no MT5
adapter, network client, process-control code, credential input, or trading
operation.

The corpus covers 25 scenarios: clean startup, external-Python protection,
package/static verification, durable-write failure, attach/disconnect/reconnect,
stale and future ticks, account/symbol identity drift, multiple terminals,
clock offset and monotonic time, declared and undeclared process/MT5/Windows
restarts, build changes, and explicit observation gaps.

Run from the repository root:

```bash
python -m unittest -v phase0.validation.vps_reliability.test_reliability_oracle
```

The oracle uses injected fixture thresholds to exercise exact boundaries. Those
values are not a production-policy decision. A passing suite proves only that
the offline state oracle produces the frozen expected traces. It does not prove
VPS uptime, broker connectivity, session coverage, restart success, a compatible
MT5 build, or Gate 0 completion, and it does not authorize trading.

All test-only temporary directories are platform-native. The regression suite
rejects a Linux-only `/tmp` override so this package remains runnable on the
Windows VPS.

The synthetic full-matrix fixture uses a deterministic step clock so its result
does not depend on host wall-clock resolution. Production observations retain
real UTC timestamps and strict-increase validation.

## Private observation wrapper

`run_private_probe.ps1` adds a capability-limited, append-only observation
wrapper. It captures a redacted terminal/account identity token, terminal
connection/build state, tick age, MT5 process start time, Windows boot time and a hash of Windows Time
status. The wrapper never causes a restart, outage, reconnect or build change;
those controlled conditions must be performed separately and only when
authorized. It exposes no order, position, history, symbol-selection, login or
process-control API.

The eight-event closure matrix is `BASELINE`, observed `DISCONNECT`, healthy
`RECONNECT`, `PYTHON_RESTART`, `MT5_RESTART`, `WINDOWS_RESTART`, `CLOCK_CHECK`
and `BUILD_CHECK`. A changed build additionally requires a SHA-256-bound
compatibility artifact. Missing events, identity drift, an unchanged Windows
boot timestamp, missing clock evidence, unhealthy reconnect, chain tamper or an
enabled external Python trading API fail closed.

Private output must be outside the repository, for example:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\run_private_probe.ps1 `
  -Output C:\Gate0Private\VpsFaultMatrix `
  -Event BASELINE `
  -ScenarioId VPS-BASELINE-1
```

Run each event only in its genuine observed state. Never label a normal sample
as a fault. Keep `PRIVATE_HMAC_KEY.bin`, Windows Time output and
`vps_probe_records.jsonl` private.
