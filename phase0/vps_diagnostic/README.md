# Gate 0 XAUUSD session/VPS diagnostic v0.2.3

This is an observation-only 24-hour diagnostic. It attaches to an already-open MT5 terminal, accepts no credentials, and aborts unless MT5 reports that automated trading via external Python is disabled. It has no order, login, account-switching, symbol-selection, position/order/history, network, or process-control calls.

## Run boundary

- Demo account only.
- Keep **Disable automated trading via external Python API** checked throughout.
- Do not run an EA, manual trade, trade copier, or unrelated automation on the dedicated account.
- The normal run does not simulate network loss or restart Windows/MT5. Those controlled reliability scenarios require a later operator window.

## What it records

Every five seconds: UTC/monotonic timing, connection state, protection flag, tick timestamp/age, bid, ask, spread, and broker-controlled symbol conditions. It rechecks a redacted account/terminal/symbol identity fingerprint every observation and stops on identity drift. Variable symbol conditions are recorded with hashes and change flags for calibration; they are not treated as identity. Records are append-only and hash chained. Account login and server are HMAC-pseudonymized with a per-run secret that is not saved.

v0.2.3 supersedes v0.2.0 through v0.2.2 for future runs. v0.2.0 and v0.2.1 incorrectly treated variable broker-controlled symbol conditions as stable identity. v0.2.2 corrected collection and produced the accepted 24-hour evidence, but its PowerShell wrapper failed after collection while writing the checksum sidecar. v0.2.3 changes only version metadata and post-run sidecar packaging to use an explicit literal path and value. The accepted v0.2.2 evidence remains valid and does not require a rerun.

MT5 Python 5.0.6090 does not expose the MQL5 `SymbolInfoSessionTrade` function. Therefore this package observes actual tick/session behavior but does not invent a direct weekly session table. A complete close/reopen conclusion requires the run to span a relevant boundary plus broker-calendar corroboration.

## Output

Return only the generated ZIP and matching `.sha256`. Never send credentials, screenshots, account numbers, identity information, or raw MT5 terminal files.
