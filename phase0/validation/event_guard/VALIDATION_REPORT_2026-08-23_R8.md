# Official-source Event Guard validation report R8

**Date:** 2026-08-23 UTC  
**Result:** PASS — 40/40 offline tests; exact BLS live-alias rerun pending  
**Trading authorization:** none

The fourth private VPS acquisition extends the append-only manifest to 21
records. Independent recomputation verifies 21/21 record digests and chain
links and 13/13 conditional-GET cache identities. The chain ends at
`0e701a5ca49b74c71456a6a06a70dd61c9b76eb5d456919719004b0163d61b4b`.
The private manifest SHA-256 is
`f315e1370abc12d9485c0a5adb9170d73125473e8f90e9863bdd0194f26a1166`;
the private normalized-report SHA-256 is
`c3e446f8df0403b0fbf83a9cfb947f43143cde2d49af6ca9c9f5540ed894fa68`.
No private bytes are published.

BEA PCE and the Fed statement, press-conference and minutes horizons remain
healthy and covered, Census remains healthy/watch-only, and reconciliation has
no conflicts. The BLS parser correctly failed closed and disclosed the exact
live DTSTART identifier: `US-Eastern`.

R8 adds only that observed identifier to the frozen BLS alias map, canonicalizes
it to `America/New_York`, and adds a regression test proving winter and summer
UTC conversion and cross-source rejection. Unknown identifiers remain rejected.
The Event Guard suite passes 40/40; all nine controlled offline suite groups
pass 148/148.

One private rerun must now prove BLS CPI and Employment coverage on the actual
cached calendar body. DOL jobless claims remains intentionally blocked because
no authoritative forward schedule with holiday exceptions has been admitted.
External Python trading stays disabled.
