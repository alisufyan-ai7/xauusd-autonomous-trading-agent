# G0-07 controlled VPS fault drill — R31 action packet

Authority: owner-approved 2026-08-24
Scope: the seven frozen post-baseline events only
Trading: prohibited; external Python trading remains disabled

This packet does not authorize any order submission, modification,
cancellation, exposure closure, broker mutation, extra fault, or scenario
expansion. Use an out-of-band VPS console that remains available while the
network adapter is disconnected. If that control path is unavailable, stop.

## Fixed private paths

- Existing accepted baseline chain: C:\Gate0Private\VpsFaultMatrix-R19
- Private records in that directory must not be pasted, uploaded or committed.
- If the accepted R21 baseline is not sequence zero in that exact chain, stop
  and report the actual private path without sending the file.

## Entry checks

From the repository root on the Windows VPS:

~~~powershell
git pull --ff-only
git rev-parse HEAD
py -3.12 -m unittest -v phase0.validation.exposure_preflight.test_exposure_preflight phase0.validation.vps_reliability.test_reliability_oracle phase0.validation.vps_reliability.test_private_probe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\exposure_preflight\run_exposure_preflight.ps1 -Output C:\Gate0Private\VpsFaultMatrix-R19 -Phase PRE_DRILL
~~~

Continue only if the preflight prints PASS_NO_OPEN_EXPOSURE, both counts are
zero, the terminal is connected, and tradeapi_disabled is true. Any other
result is an immediate fail-closed stop.

## Frozen sequence

After each capture, run the prefix verifier shown below. Continue only when it
prints PASS_PREFIX with no reasons.

~~~powershell
py -3.12 .\phase0\validation\vps_reliability\verify_private_matrix.py --output C:\Gate0Private\VpsFaultMatrix-R19 --allow-incomplete
~~~

1. DISCONNECT — while attached through the out-of-band console, disable only
   the VPS network path. Do not stop MT5. Capture:

   ~~~powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\vps_reliability\run_private_probe.ps1 -Output C:\Gate0Private\VpsFaultMatrix-R19 -Event DISCONNECT -ScenarioId VPS-R31-DISCONNECT-1
   ~~~

   Require connected:false and tradeapi_disabled:true.

2. RECONNECT — restore the same network path, wait for MT5 to reconnect and a
   fresh XAUUSD tick, then capture with -Event RECONNECT and scenario
   VPS-R31-RECONNECT-1. Require connected:true, tradeapi_disabled:true, and the
   frozen tick-age bound.

3. PYTHON_RESTART — launch a fresh non-trading probe invocation and capture
   with -Event PYTHON_RESTART and scenario VPS-R31-PYTHON-RESTART-1. No Python
   trading service may be started or enabled.

4. MT5_RESTART — close and restart only the MT5 terminal. After it is
   connected, confirm the external-Python barrier is still disabled, then
   capture with -Event MT5_RESTART and scenario VPS-R31-MT5-RESTART-1. Require
   a changed terminal start time.

5. WINDOWS_RESTART — restart only the approved VPS. Re-enter through the
   out-of-band console, wait for MT5 health, confirm the barrier remains
   disabled, then capture with -Event WINDOWS_RESTART and scenario
   VPS-R31-WINDOWS-RESTART-1. Require a changed Windows boot timestamp.

6. CLOCK_CHECK — with the recovered system healthy, capture with
   -Event CLOCK_CHECK and scenario VPS-R31-CLOCK-CHECK-1. The wrapper binds the
   private Windows Time status hash.

7. BUILD_CHECK — capture with -Event BUILD_CHECK and scenario
   VPS-R31-BUILD-CHECK-1. If the terminal build changed from baseline, stop
   unless the separately verified compatibility artifact SHA-256 is available;
   pass it only through -CompatibilitySha256.

For steps 2–7, use the same run_private_probe.ps1 command as step 1 with only
the frozen event and scenario values changed. Do not add another event.

## Final reconciliation

~~~powershell
py -3.12 .\phase0\validation\vps_reliability\verify_private_matrix.py --output C:\Gate0Private\VpsFaultMatrix-R19
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\phase0\validation\exposure_preflight\run_exposure_preflight.ps1 -Output C:\Gate0Private\VpsFaultMatrix-R19 -Phase POST_RECOVERY
~~~

Both commands must pass. Preserve only the publication-safe final matrix hash,
pre/post exposure-record hashes, event timestamps and PASS result for Gate 0.
Any unhealthy recovery, identity drift, enabled barrier, unknown/nonzero
exposure, chain failure or unexpected change ends the drill immediately.
