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
- explicit confirmation phrase required for every submission call;
- a time-bounded owner-gated activation permit is mandatory before any submission;
- the permit must bind the exact demo account fingerprint, server and daily submission budget;
- deterministic Policy A Risk Governor approval is mandatory and hash-bound to an admitted risk calibration;
- durable request IDs; duplicates rejected;
- configurable but hard-bounded daily submission budget;
- uncertain submission latches the ledger and blocks all further new risk until
  reconciliation;
- post-submit reconciliation must observe exactly one XAUUSD position, no
  pending orders, volume <= 0.01 and a nonzero stop;
- no live-account routing is permitted.

The current PCR-3 release on the VPS remains sealed and execution-disabled.
Nothing in this package authorizes deployment, enabling MT5 external-Python
trading, or sending a demo/live order. Those remain separately owner-gated.
