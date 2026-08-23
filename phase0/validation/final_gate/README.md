# Final Gate 0 evidence-matrix oracle

This pure evaluator enforces the fourteen-item inventory and derives `PASS`
only when every frozen claim has exactly one admitted, typed receipt whose
SHA-256 matches a supplied sanitized repository artifact. Editing status text
alone cannot promote an item. Requirements, provenance, safe relative paths,
private hash-only publication, timestamps and safety guards are all checked.

```text
python -m unittest -v test_matrix_oracle.py
```

The oracle does not authorize later demo/live trading even if every Gate 0 item
eventually passes.
