# XAUUSD shock and post-event calibration scaffold

This package is an offline, non-trading scaffold for the independent abnormal-
volatility circuit breaker. It admits minimized derived features only after an
immutable dataset hash, chronological split, documented rights, sample minima,
and uncontaminated training baseline all pass. Missing data or admission
metadata returns `FAIL_CLOSED`.

Run with Python 3.12:

```text
python -m unittest -v test_shock_calibration.py
```

Candidate thresholds are selected from the chronological training partition
only and metrics are calculated on the untouched validation partition. Output
is always `CANDIDATE_ONLY`: minimum hold, sustained normalization and repeated-
trip constants remain zero until empirical selection and controlled review.
Such a candidate cannot construct the replay/runtime gate.

The replay gate proves exact-boundary locking, unavailable-baseline locking,
calendar-independent shock detection, delayed normalization, post-event
normalization blocking, and repeated-trip quarantine. It contains no network,
broker, OpenAI, messaging or order integration.

To close calibration, provide an admitted immutable chronological XAUUSD
derived-feature corpus with documented automated-analysis and retention rights;
frozen train/validation cutoffs; representative sessions, scheduled events and
known shocks; and enough samples to set prospective minima. Then register the
candidate before untouched replay and report false-lock rate, missed-shock rate,
lock duration, session/regime sensitivity and tail cases. Raw ticks and account
identifiers must remain private.
