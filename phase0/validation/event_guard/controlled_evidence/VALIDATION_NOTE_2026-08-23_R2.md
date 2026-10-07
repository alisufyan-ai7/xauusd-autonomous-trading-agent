# Controlled revision/outage/holiday validation note R2

**Date:** 2026-08-23  
**Result:** PASS — 11/11 controlled-evidence tests  
**Trading authorization:** none

R2 retains the controlled revision, outage, recovery and holiday cases and
closes a transition-admission defect: two independently asserted frame hashes
could previously be presented as one append-only transition. Each transition
now requires exact UTC observation time and a direct acquisition-record hash
link from the prior frame. A broken link locks with
`RECORD_CHAIN_DISCONTINUITY`.

The unchanged parent Event Guard suite also passes 43/43. These synthetic tests
do not supply a real agency revision, natural outage/recovery or holiday update.

