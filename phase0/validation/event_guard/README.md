# Official-source Event Guard conformance oracle

This is an offline, deterministic evaluation artifact. It contains no broker,
order, OpenAI, credential, or network integration.

Run:

```text
python -m unittest -v test_event_guard.py
```

The oracle exercises UTC/DST normalization, BLS/BEA machine-readable shapes,
monitored Fed/Census/DOL schedule rows, frozen taxonomy filtering, overlapping
FOMC intervals, exact boundaries, source conflicts, cancellation/tentative
behavior, optional FRED date-only cross-checking, submission-latency crossing,
post-event normalization, and the independent shock lock.

A passing result validates the specified transformations and fail-closed
semantics only. It does not establish live acquisition reliability, complete
future-calendar coverage, calibrated shock thresholds, or trading authorization.
