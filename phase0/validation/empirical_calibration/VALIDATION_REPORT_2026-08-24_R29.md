# Prospective adaptive-calibration validation R29

**Recorded:** 2026-08-24 UTC  
**Result:** PASS — 9/9 controlled tests  
**Trial status:** `REGISTERED_WAITING_FUTURE_DATA`  
**Trading authorization:** none

The R4 protocol is frozen before the evaluation window. It computes daily
session-stratified 99.5th-percentile spread, gap and round-trip-cost predictions
from the preceding 56 days only. Same-day observations cannot affect that day's
thresholds. Missing history, early opening, weak coverage, partition overlap,
policy mutation or registration/code mutation fails closed.

The future window is 2026-08-25 00:00Z through 2026-09-23 23:45Z and requires
at least 2,500 rows, 300 per session, 99% overall coverage and 98.5% coverage in
each session. The unchanged slippage-proxy, return, range, quote-gap, tick-age
and post-event components must pass jointly. Any failure rejects the whole
trial without retuning.

This registration does not close G0-05, authorize replay, open strategy
performance, authorize an OpenAI call, or authorize trading. External Python
trading remains disabled.
