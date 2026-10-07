# Gate 0 setup/execution validation report

**Scope:** local deterministic validation only  
**Broker calls:** none; structurally absent  
**Trading authorization:** none

## Objective result

Command:

```text
python -m unittest -v test_corpora.py
```

Result after the 1.0.1 defect correction: **21/21 implemented tests passed**.

Validated behavior:

- all five setup families have registered pass and family-specific rejection cases;
- absent common safety inputs fail closed;
- exact reward/risk and stop-distance boundaries and just-outside values;
- adverse cost cannot improve net reward/risk;
- setup-key stability/change behavior;
- selector precedence and directional-conflict `NO_TRADE`;
- every currently allow-listed execution transition;
- every currently unlisted state transition enters `INCIDENT` in the oracle;
- compare-and-swap conflict, single durable attempt, and duplicate claim prevention;
- uncertainty and terminal-state fail-closed behavior;
- multi-field attribution, closure volume conservation/history completeness;
- exit volume cannot invert or increase exposure;
- source has no broker or network import.

## Acceptance status

**Full P0-SETUPS-001 Section 10 corpus acceptance: FAIL / INCOMPLETE.** The
current oracle consumes precomputed predicates. It does not yet independently
calculate and test every OHLC-derived predicate, every numeric equality/one-tick
edge, look-ahead prevention, all family long/short mirrors, or tick-normalization
effects. Passing the 20 tests must not be represented as verification of the full
setup algorithm.

**Execution specification core tests: PASS.** The single-attempt, fail-closed,
attribution, conservation, transition, total restart, and typed event-precedence
rules tested above pass. Broker-specific behavior remains a later validation dependency.

## Defects revealed by executable modeling

### EXE-DEFECT-001 — CLOSED in specification 1.0.1

Section 8 requires restart from every persisted state to have one deterministic
fail-closed outcome. Section 7 specifies startup reconciliation and explicitly
quarantines uncertain/corrupt/mismatched states, but it does not provide the full
per-state result table (for example `OBSERVED`, `PROPOSED`, `APPROVED`, `READY`,
`ACKNOWLEDGED`, `RECONCILED_OPEN`, `MANAGING`, and terminal states). The harness's
`restart_outcome` is therefore a conservative test-oracle assumption, not a frozen
normative implementation rule.

Closure: a normative per-state restart table now revokes prior `READY`, quarantines
submission/acknowledgement/open/exit uncertainty, preserves terminal/control states,
and grants no broker-call authority. The executable oracle matches every state.

### EXE-DEFECT-002 — CLOSED in specification 1.0.1

Section 3.1 says an unlisted event/state pair enters `INCIDENT`, while it also says
any unexpected account, symbol, ownership, ledger, lease, or broker-state observation
enters `QUARANTINED`. It does not formally distinguish protocol-invalid transition
requests from safety observations or give evaluation precedence. Two conforming
implementations could classify the same composite event differently.

Closure: event classes and precedence are total: corruption/protocol-invalid enters
`INCIDENT`; otherwise a safety observation enters `QUARANTINED`; otherwise the
allow-listed normal transition applies. Composite-event precedence is tested.

## Conclusion

No frozen architectural safety invariant failed. The execution-core defect corrections
and implemented subset pass, but Gate 0 setup corpus closure has **not** passed. The
missing independent OHLC feature-level golden corpus remains blocking.
