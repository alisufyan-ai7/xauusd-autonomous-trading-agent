# Setup and execution validation harness

This package is a pure-Python, broker-free executable oracle for:

- `P0-SETUPS-001` v1.0-rc1;
- `EXECUTION_RECONCILIATION_IDEMPOTENCY_SPEC` v1.0.

It has no `MetaTrader5` import, network operation, credential input, or order API.
It cannot submit, modify, cancel, or close an order.

Run from this directory with Python 3.11+:

```powershell
python -m unittest -v test_corpora.py
```

The setup corpus covers all five families with positive and family-specific
negative examples. Generated property cases cover every common fail-closed lock,
reward/risk and stop boundaries, cost monotonicity, key stability, selection
precedence, and directional conflict. The execution corpus machine-enumerates all
allowed and forbidden state transitions and tests durable single-attempt claiming,
CAS conflicts, uncertain restart, attribution, volume conservation, and safe exits.

This validates the decision/state contracts over precomputed features. It does not
claim to validate OHLC feature generation, broker-specific mappings, empirical
latency, MT5 retcodes, or real broker behavior; those remain separate evidence work.
