# Official-source Event Guard validation report R10

**Date:** 2026-08-23 UTC  
**Result:** PASS — 42/42 offline tests; free authoritative DOL capture pending  
**Trading authorization:** none

Official review identified an ETA Office of Unemployment Insurance schedule at
`https://oui.doleta.gov/unemploy/claims_arch.asp`. It explicitly states that the
UI Weekly Claims News Release is published each Thursday morning at 8:30 a.m.
Eastern and that federal-holiday exceptions are listed on the page. The current
page names Wednesday, November 25, 2026 at 8:30 a.m. as the Thanksgiving-week
exception.

R10 replaces the blocked historical DOL candidate with that one exact URL. Body
admission requires the weekly rule, release time, exception contract and table
shape. The offline parser expands Thursdays only from this authoritative rule,
uses `America/New_York` for DST-aware UTC conversion, and replaces the Thursday
in an exception week with the listed date/time. Missing contracts, unexpected
base time, duplicate or invalid exception dates, historical-only bodies and old
DOL endpoints are rejected.

The full synthetic acquisition-to-normalization test now returns `PASS` with
BLS CPI/Employment, BEA PCE, Fed statement/press-conference/minutes and DOL
jobless claims all covered. The Event Guard suite passes 42/42; all nine
controlled offline suite groups pass 150/150.

One private VPS capture must confirm the exact live DOL body, content type,
schema and forward event. No paid provider is recommended or activated. This
revision is specification/read-only testing only; external Python trading stays
disabled.
