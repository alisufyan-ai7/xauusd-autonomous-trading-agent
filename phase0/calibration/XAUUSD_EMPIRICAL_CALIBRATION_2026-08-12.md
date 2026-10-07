# XAUUSD Empirical Calibration — Initial 24-Hour Evidence

**Evidence date:** 2026-08-11/12 UTC  
**Status:** initial observation-bound calibration; not a production cost model

## Supported initial values

| Quantity | Evidence-backed observation |
|---|---:|
| Point/tick size | 0.001 |
| Typical spread | 0.182 (182 points) |
| Observed low spread | 0.168 |
| Observed 24-hour maximum | 0.420 |
| Post-pause spread | 0.238 for approximately one minute |
| Observed stale-tick pause | approximately 20:58:33Z–22:00:26Z |
| Connected sampling reliability | 100% of 17,260 samples |
| Maximum observer sampling gap | 5.079 seconds |

## Conservative Gate 0 use

- Replay cost sensitivity must include at least the observed typical spread and a spread-stress case no lower than the observed 0.420 peak.
- The observed pause plus a safety buffer must block new entries until an authoritative weekly schedule and repeated boundary evidence are available. This file does not invent that final buffer.
- The 12:30Z spread expansion is a shock candidate, not proof of a recurring news relationship; event attribution requires a licensed calendar and exact event timestamps.
- No slippage, commission, swap, gap-loss, fill probability, market impact, or latency distribution can be frozen from this read-only quote observer.

## Remaining evidence required

Repeated session-boundary runs, restart/reconnect/network/clock/build tests, a licensed calendar, immutable historical bars/ticks with provenance, and later non-risk-changing/demo-gate execution evidence are required before a production cost or fill model can be claimed.
