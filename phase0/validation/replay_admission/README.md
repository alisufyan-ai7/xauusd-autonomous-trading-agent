# Immutable historical-replay admission

This offline package is a fail-closed gate in front of replay. It validates a
caller-supplied manifest and bytes; it does not acquire data, inspect strategy
performance, open a holdout, or connect to MT5.

Admission requires:

- complete HTTPS provenance and explicit XAUUSD/UTC/instrument semantics;
- documentary approval for automated use, local retention, derived data,
  historical replay, and audit retention, with redistribution denied;
- a sealed, unviewed trial registration and immutable code/config/split hashes;
- exact manifest, dataset-root, file, byte-count, row-count, and documentary
  evidence hashes;
- chronological canonical bid/ask OHLC rows with receipt timestamps, valid
  prices and no duplicates; and
- exact, evidence-hashed official session/holiday authorization for every
  non-cadence gap. Generic, unused, weakly sourced, or unexplained gaps reject.

Run from this directory:

```powershell
py -3.12 -m unittest -v test_admission.py
```

The included fixture is deliberately synthetic and proves only the admission
logic. It is not licensed market evidence and produces no performance result.

The exact remaining external blocker is a provider-authorized immutable XAUUSD
bid/ask or tick history whose terms have been reviewed and recorded as permitting
local automated evaluation, retention, derived outputs and audit retention,
together with authoritative session/holiday evidence, account-compatible symbol
semantics, frozen file hashes and a preregistered chronological split map. No
dataset has been purchased or downloaded by this package.
