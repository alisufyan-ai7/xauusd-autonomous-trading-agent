# XAUUSD Demo Adapter

This directory is a separately packaged demo-only execution lane. It is not
part of the execution-disabled xauusd-production-candidate wheel.

Current state: implementation and offline validation only.

## Hard envelope

- exact allow-listed MT5 demo account fingerprint;
- MT5 account trade mode must be DEMO;
- exact broker, server and currency binding;
- XAUUSD only;
- volume greater than zero and no more than 0.01 lot;
- zero existing positions and zero pending orders before new risk;
- one concurrent position after a successful submission;
- protective stop required and broker stop-distance checked;
- explicit submission confirmation phrase required;
- a time-bounded owner-gated activation permit is mandatory before any submission;
- a separate durable control database defaults to `KILLED`;
- the control can become `ACTIVE` only when the exact activation permit is
  armed with the explicit arm confirmation phrase;
- operator kill returns the control to `KILLED` and blocks new submissions;
- uncertain broker outcomes, active-binding mismatches, identity/exposure
  failures, unavailable margin calculation, or Risk Governor precondition
  failures deterministically latch `QUARANTINED`;
- `QUARANTINED` cannot re-arm directly: an explicit reset to `KILLED` is
  required before a fresh activation;
- deterministic Policy A Risk Governor approval is mandatory;
- the adverse-cost calibration is bound by the exact calibration-object
  SHA-256 and must carry a source SHA-256 plus the scope
  `DEMO_LIFECYCLE_ONLY`;
- durable request IDs; duplicates rejected;
- configurable but hard-bounded daily submission budget;
- uncertain submission latches the request ledger and blocks all further new
  risk until reconciliation;
- post-submit reconciliation must observe exactly one XAUUSD position, no
  pending orders, volume <= 0.01 and a nonzero stop;
- no live-account routing is permitted.

## Deliberately unresolved

No numeric adverse-cost calibration is admitted merely by this code. Existing
empirical calibration evidence contains fail-closed/nonstationary findings, so
this package will remain unable to pass the Risk Governor for a real demo
submission until a separate, explicitly admitted demo-lifecycle calibration
artifact is created and hash-bound. That artifact cannot be promoted to
real-money evidence.

The current PCR-3 release on the VPS remains sealed and execution-disabled.
Nothing in this package authorizes deployment, enabling MT5 external-Python
trading, or sending a demo/live order. Those remain separately owner-gated.
