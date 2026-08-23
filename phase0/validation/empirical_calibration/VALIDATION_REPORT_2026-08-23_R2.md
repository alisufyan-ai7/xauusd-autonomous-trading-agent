# Empirical-calibration workflow validation report — R2

**Date:** 2026-08-23  
**Result:** PASS — 10/10 offline tests  
**Data:** synthetic derived observations only  
**Trading authorization:** none

R2 retains the admitted-bundle, rights, hash, split, session, sealed-holdout and
training-only candidate controls. It now rejects validation observations at or
before the frozen training cutoff and refuses to infer continuous post-event
normalization across an observation gap greater than the preregistered maximum.

Outputs remain `CANDIDATE_ONLY`. No empirical constant or execution-slippage
claim was selected; licensed real observations and independent validation are
still required.
