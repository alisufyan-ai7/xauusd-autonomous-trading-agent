# VPS Diagnostic Evidence Validation — 2026-08-12

**Artifact:** `evidence-20260811T202106Z.zip`  
**SHA-256:** `91a1189241521fcc3f0922e4d98b1fdb6c20751f7fed8e60a9c6dac3c5be9928`  
**Diagnostic:** v0.2.2, read-only  
**Trading authorization:** none

## Integrity result

- Supplied sidecar exactly matches the ZIP SHA-256.
- ZIP structural/decompression test: PASS; three expected members only.
- JSON parse: 17,260/17,260 observations PASS.
- Sequence: continuous 0..17,259; zero gaps or duplicates.
- Append-only `prior_record_sha256` chain: PASS; zero errors.
- Computed final record SHA-256 exactly matches summary: `c7fb9f24fc6af45647c48ab2ebbbd34a0208c5c930e140fc3a00ec01de966055`.
- Summary status/stop: `PASS` / `duration_complete`.

## Safety and reliability observations

- Observation interval: 2026-08-11 20:21:06Z through 2026-08-12 20:21:10Z.
- `connected=true`: 17,260/17,260.
- `tradeapi_disabled=true`: 17,260/17,260.
- Sampling gap: median 5.000 s; maximum 5.079 s; zero gaps over 6 s.
- Health: 16,517 `HEALTHY`; 743 `UNHEALTHY` due to stale ticks, never terminal disconnection.
- One continuous stale-tick interval was observed from 20:58:33Z through 22:00:26Z, approximately 61 minutes 53 seconds. It is account-specific observation evidence only and does not establish the complete weekly or holiday schedule.

## Empirical spread observations

The observed symbol used three decimal digits and point/tick size 0.001.

- Samples: 17,260.
- Minimum: 0.168 (168 points).
- Median: 0.182 (182 points).
- Mean: 0.182122.
- 95th and 99th percentile: 0.182.
- Maximum: 0.420 (420 points).
- Immediately after the stale-tick interval, spread was 0.238 for approximately one minute.
- A separate expansion to 0.420 occurred near 12:30Z.

These observations support conservative calibration bounds but do not prove future execution cost, slippage, fill probability, gap behavior, swap charging, or a complete session calendar.

## Defect record

The 24-hour diagnostic itself completed successfully. `run_diagnostic.ps1` then failed while writing the checksum sidecar because positional `Set-Content` binding treated the value as an additional path. The owner generated the sidecar with an explicit literal-path recovery procedure. This post-run packaging defect did not alter the evidence directory or ZIP; matching hashes prove the recovered sidecar refers to the received ZIP. Future package versions must use explicit `-LiteralPath`/`-Value` or `System.IO.File.WriteAllText` and include a packaging regression test.

## Claim limit

This validates one read-only 24-hour observation run. It does not authorize automated demo or live trading and does not close restart, reconnect, network-loss, clock-change, terminal-build-change, weekly-boundary, or holiday-boundary evidence requirements.
