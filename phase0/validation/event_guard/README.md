# Official-source Event Guard conformance package

The oracle and source-conformance checks are offline and deterministic. The
separate capture utility performs read-only HTTPS `GET` requests only against
the frozen official-source allowlist. None of these files contains broker,
order, OpenAI, credential or messaging integration.

Run:

```text
python -m unittest -v test_event_guard.py test_source_conformance.py
```

The 30 checks exercise UTC/DST normalization, BLS/BEA machine-readable shapes,
monitored Fed/Census/DOL schedule rows, frozen taxonomy filtering, overlapping
FOMC intervals, exact boundaries, source conflicts, cancellation/tentative
behavior, optional FRED date-only cross-checking, submission-latency crossing,
post-event normalization, the independent shock lock, official URL/content-type
allowlists, payload and record hashes, conditional-GET cache identity,
append-only restart verification, forward-coverage limits, source roles and
conservative moved-event windows.

Schema fingerprints are derived from captured body content. The capture utility
cannot label a body conforming merely by copying the expected registry value.

## Private VPS capture

From this directory, with Python 3.12:

```text
py -3.12 capture_official_sources.py --output C:\Gate0Private\EventGuard
```

The output directory contains raw official-source snapshots and a hash-chained
JSONL acquisition manifest. It is private evidence: do not commit, email or
publish it. The current all-source run is expected to return `FAIL_CLOSED`
because DOL jobless claims has no admitted first-party forward schedule with
holiday exceptions. A successful HTTP fetch of a historical DOL release page
cannot clear that blocker.

A passing result validates the specified transformations and fail-closed
semantics only. A capture result is observation evidence only. Neither result
establishes a full schedule horizon, calibrated shock thresholds or trading
authorization.
