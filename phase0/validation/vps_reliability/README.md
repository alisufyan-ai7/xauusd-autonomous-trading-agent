# Gate 0 VPS reliability fault oracle

This directory converts the restart/reconnect/network/clock/build failure matrix
into a deterministic, standard-library-only offline oracle. It contains no MT5
adapter, network client, process-control code, credential input, or trading
operation.

The corpus covers 25 scenarios: clean startup, external-Python protection,
package/static verification, durable-write failure, attach/disconnect/reconnect,
stale and future ticks, account/symbol identity drift, multiple terminals,
clock offset and monotonic time, declared and undeclared process/MT5/Windows
restarts, build changes, and explicit observation gaps.

Run from the repository root:

```bash
python -m unittest -v phase0.validation.vps_reliability.test_reliability_oracle
```

The oracle uses injected fixture thresholds to exercise exact boundaries. Those
values are not a production-policy decision. A passing suite proves only that
the offline state oracle produces the frozen expected traces. It does not prove
VPS uptime, broker connectivity, session coverage, restart success, a compatible
MT5 build, or Gate 0 completion, and it does not authorize trading.
