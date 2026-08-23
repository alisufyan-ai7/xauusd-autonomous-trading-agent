# Final Gate 0 evidence-matrix oracle

This pure evaluator enforces the fourteen-item inventory and the rule that every
item must be `PASS` before Gate 0 can pass. Missing, duplicate, unknown,
`PENDING` or `FAIL_CLOSED` items cannot be promoted. It also fixes trading
authorization to false, requires external Python trading to remain disabled and
rejects an unrecorded immediate owner-action request.

```text
python -m unittest -v test_matrix_oracle.py
```

The oracle does not authorize later demo/live trading even if every Gate 0 item
eventually passes.
