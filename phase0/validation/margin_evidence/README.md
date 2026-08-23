# Private account-specific M1 evidence

This directory provides an independent local calculation for a fresh,
read-only account/symbol snapshot. It never calls `order_calc_margin`, any order
API, a network service or a messaging service. Only MT5 calculation mode 0 and
an unambiguous direct account-currency conversion are admitted; everything else
fails closed pending a separately authorized calculation method.

The verifier applies the approved M1 thresholds under current and stressed
states: margin level at least 1,000%, free margin at least 90% of projected
equity, and 2.0x stressed incremental margin. The adverse spread, slippage, gap
and cost inputs must come from a separately frozen calibration artifact.

`stress_artifact.py` is the independent admission gate for that artifact. The
M1 evaluator invokes that gate directly and requires its calculated artifact
hash to equal a separately expected hash; a caller-supplied frozen flag or
unbound stress dictionary is never accepted. It
requires pre-holdout freeze chronology, XAUUSD/0.01/USD scope, contract-spec and
admitted replay-bundle roots, code/config/split hashes, empirical and selected
positive spread/slippage/gap/cost stresses, conservative selection, and a
self-consistent artifact hash. It contains no private account state and cannot
produce an M1 verdict by itself.

```text
py -3.12 -m unittest -v phase0.validation.margin_evidence.test_margin_evidence phase0.validation.margin_evidence.test_stress_artifact
```

Private snapshots may contain exact equity and margin and must remain outside
the repository. A public report may contain only result labels and artifact
hashes. Passing M1 is specification evidence only and never authorizes a trade
or overrides another Risk Governor limit.

`run_private_snapshot.ps1` creates one fresh private snapshot using only
terminal/account/symbol/tick reads. It omits the account number, server and
broker identity and HMAC-tokenizes the account binding. It still contains exact
equity/margin data, so neither the snapshot nor its private HMAC key may be
committed or emailed. The wrapper does not create a verdict until the empirical
stress calibration has been frozen.
