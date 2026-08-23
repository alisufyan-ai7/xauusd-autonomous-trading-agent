# Official-source Event Guard conformance package

The oracle and source-conformance checks are offline and deterministic. The
separate capture utility performs read-only HTTPS `GET` requests only against
the frozen official-source allowlist. None of these files contains broker,
order, OpenAI, credential or messaging integration.

Run:

```text
python -m unittest -v test_event_guard.py test_source_conformance.py
```

The 42 checks exercise UTC/DST normalization, BLS/BEA machine-readable shapes,
monitored Fed/Census/DOL schedule rows, frozen taxonomy filtering, overlapping
FOMC intervals, exact boundaries, source conflicts, cancellation/tentative
behavior, optional FRED date-only cross-checking, submission-latency crossing,
post-event normalization, the independent shock lock, official URL/content-type
allowlists, payload and record hashes, conditional-GET cache identity,
append-only restart verification, forward-coverage limits, source roles and
conservative moved-event windows.

Windows does not normally ship the IANA timezone database used by
`zoneinfo`. The package therefore pins the first-party `tzdata` fallback and
its wheel hash in `requirements-win-py312.txt`. A missing database produces an
explicit fail-closed diagnostic rather than an unexplained timezone lookup.
The BLS calendar is documented as Eastern time but can carry Windows calendar
timezone identifiers. Only the source-scoped `Eastern Standard Time`,
`US Eastern Standard Time` and live-observed `US-Eastern` aliases are mapped to
`America/New_York`; the same identifiers from another source, and every unknown
identifier, are rejected.

Schema fingerprints are derived from captured body content. The capture utility
cannot label a body conforming merely by copying the expected registry value.
The admitted BEA shape permits its documented response-root
`file_last_updated` string in addition to non-empty release objects; no other
scalar root field is admitted.

Federal Reserve locks use the official month-calendar pages under
`/newsevents/YYYY-month.htm`, not the general monetary-policy landing page. The
month pages provide both `Time` and `Release Date(s)` for FOMC statements, press
conferences and minutes. Four consecutive month pages are acquired to cover the
frozen 75-day horizon; the generic landing page is explicitly rejected because
its upcoming-date summary does not provide an authoritative event time.

DOL jobless-claims locks use only ETA's Office of Unemployment Insurance
schedule at `https://oui.doleta.gov/unemploy/claims_arch.asp`. Admission requires
the explicit Thursday 8:30 a.m. Eastern weekly rule and the federal-holiday
exception contract. Listed exception dates replace the Thursday in the same
week; missing/malformed rules, duplicate exceptions, old DOL endpoints and
historical-only pages fail closed. Eastern civil time is converted through the
pinned IANA database so summer and winter UTC times differ correctly.

## Private VPS capture

From this directory, with Python 3.12, use the fail-closed wrapper:

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_private_capture.ps1 -Output C:\Gate0Private\EventGuard
```

The wrapper installs only the hash-pinned binary dependency, runs all offline
tests, and starts capture only if both steps succeed. It then normalizes the
locally hashed BLS, BEA, Fed and DOL bodies, verifies source freshness and forward
coverage, and writes `normalized_event_guard.json` inside the private output
directory. It rejects an output path inside the repository.

The output directory contains raw official-source snapshots and a hash-chained
JSONL acquisition manifest. It is private evidence: do not commit, email or
publish it. The all-source run returns `PASS` only when every lock-authoritative
source is healthy, every frozen taxonomy has a forward event, and reconciliation
has no conflict. A successful HTTP fetch alone cannot clear any source.

A passing result validates the specified transformations and fail-closed
semantics only. A capture result is observation evidence only. Neither result
establishes a full schedule horizon, calibrated shock thresholds or trading
authorization.
