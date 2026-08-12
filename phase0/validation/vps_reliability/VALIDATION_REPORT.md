# VPS Reliability Fault-Matrix Validation Report — 2026-08-12

**Scope:** deterministic offline oracle only  
**External calls:** none  
**Broker/trading capability:** none  
**Gate 0 implication:** test-harness coverage advanced; operational evidence remains incomplete

## Result

| Artifact | Coverage | Result |
|---|---:|---:|
| `reliability_corpus.json` | RVM-001 through RVM-025 | PASS — 25/25 exact scenario traces |
| `test_reliability_oracle.py` | 7 test methods | PASS — 7/7 |

The passing corpus confirms fail-closed behavior for disabled-protection breach,
manifest/static-verifier failure, durable-write failure, connection loss, stale
or future tick time, identity drift, terminal ambiguity, clock/monotonic faults,
restart reprobe omissions, build changes, and sequence gaps. Safe-stop findings
remain latched. Reconnect, restart, and build recovery require the corresponding
full reprobe boundary; a changed build additionally requires an explicit
compatibility-validation input.

## Claim limit and remaining evidence

This result validates only the deterministic oracle and its frozen fixture
traces. The threshold values are injected validation fixtures, not selected
production settings. Gate 0 still requires controlled VPS observations for the
24-hour/boundary soak and the approved network, Python, MT5, Windows, clock,
multiple-terminal, build-change, and durable-recording scenarios. External
Python trading must remain disabled throughout those future observations.
