# Immutable XAUUSD acquisition protocol

This package freezes the procedure that must pass **before** any historical
data is downloaded. It requires explicit internal rights for automated use,
local retention, derived data, replay and audit retention, plus explicit
retention treatment after termination. It also freezes the exact H4/H1/M15
inventory, source semantics, read-only GET acquisition, private output location,
raw-byte preservation, deterministic transforms and a strictly chronological
sealed split/embargo/holdout map.

Run from this directory:

```text
python -m unittest -v test_acquisition_protocol.py
```

The fixture uses synthetic provider and rights bytes. A pass means only that the
procedure is internally consistent. The module has no network, provider,
broker, model, process, filesystem-write or order capability. No current
provider has been admitted and no acquisition is authorized by this package.
