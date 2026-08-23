# Empirical shock, normalization and cost calibration workflow

This offline workflow consumes minimized derived observations from a separately
admitted immutable XAUUSD bundle. It prospectively freezes training/validation
boundaries and coverage requirements, rejects any holdout exposure, and derives
training-only candidates for:

- abnormal spread, return, range, quote-gap and tick-age thresholds;
- adverse latency-move **slippage proxy**, gap and round-trip cost stresses; and
- sustained post-event normalization duration across complete event recoveries.

R25 requires validation observations to follow the frozen training cutoff and
rejects a claimed consecutive normalization run if its post-event observation
stream contains a gap larger than the prospectively frozen maximum. R26 binds
each recovery to exactly one event-time marker, measures duration from that
marker, and rejects a missing/duplicate marker or an unobserved initial gap.

Run from this directory:

```text
python -m unittest -v test_calibration_workflow.py
```

Outputs remain `CANDIDATE_ONLY`. The slippage value is explicitly a non-trading
adverse latency proxy, not observed execution slippage. Real data, independent
review, untouched validation and a frozen runtime artifact remain required. The
module cannot acquire data, call MT5/OpenAI, send messages, write files or trade.
