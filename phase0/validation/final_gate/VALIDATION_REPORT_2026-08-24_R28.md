# Gate 0 controlled validation report R28

**Recorded:** 2026-08-24 UTC  
**Result:** `PASS_319_OF_319_ACROSS_20_GROUPS`  
**Gate 0:** `INCOMPLETE` — 6 `PASS` / 8 `PENDING`  
**Trading authorization:** none

R27 established 312/312 controlled offline tests across nineteen groups. R28
adds six GET-only Dukascopy decoder/acquisition tests and one calibration
chronology regression. All changed and dependent groups were rerun: acquisition
18/18, calibration 13/13, child/multiframe admission 19/19 and frozen-receipt
matrix 11/11.

The byte-level R3 admission receipt closes only G0-11. Three chronological
calibration trials rejected the absolute spread, gap and round-trip-cost tail
model. The registered replay preflight therefore stopped before performance and
no Sol request was made.

No raw/provider market bytes, private correspondence, credential, identity,
account state or endpoint response body is published. No provider outreach,
purchase/trial, VPS disruption, alert delivery, OpenAI API call, broker action
or trade occurred. External Python trading remains disabled.
