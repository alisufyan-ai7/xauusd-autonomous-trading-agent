# Empirical calibration workflow validation report — R3

**Date:** 2026-08-23  
**Result:** PASS — 12/12 offline tests  
**Empirical data used:** none  
**Trading authorization:** none

R3 corrects post-event recovery duration to start at exactly one chronological
event marker rather than the first available post-event observation. Missing
or duplicate markers, post-event rows at/before the marker and an initial gap
larger than the prospectively frozen observation maximum fail closed. Later
gaps, training/validation chronology, sealed holdout, rights and hash bindings
remain enforced.

Outputs remain synthetic `CANDIDATE_ONLY`; no runtime constant was admitted.
