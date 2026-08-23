# Selected Sol Analyst runtime validation report

**Date:** 2026-08-23 UTC  
**Result:** PASS — 20/20 offline tests  
**API calls/cost:** zero  
**Trading authorization:** none

The package verifies:

- exact `gpt-5.6-sol`, Responses API, `store:false`, `tools:[]`, low reasoning,
  one attempt, 1,200 output-token cap, disabled truncation and default service tier;
- 5-second connect, 15-second total, 5-second send-age and 30-second accept-age
  boundaries, plus 2,000-ms quote and 30,000-ms completed-M15 limits;
- exact closed field sets for TPB, BRT, FBR, RSR and MOC, with all 65 registered
  fields fully defined by type, purpose, source, unit, precision, age and retention;
- zero free-text market/news fields and no account, ticket, order, position,
  balance, equity, margin, leverage, volume, identity or contact field;
- canonical decimal strings, integer bounds, exact enums, UUIDv4 analysis IDs,
  domain-separated snapshot hashes and exact-key rejection;
- local no-call on any blocked/unknown risk, spread, volatility, session, event,
  exposure or family predicate;
- strict recursive `additionalProperties:false` output objects;
- response rejection for non-completion, refusal, tool/unknown output item or
  response-model mismatch, while allowing the documented non-tool reasoning
  output item produced by reasoning models;
- exact production prompt rules: snapshot-only, untrusted-input handling,
  NO_TRADE default, supplied-facts-only output and no execution authority;
- strict response-body binding for IDs, family, direction, prices, targets,
  evidence references, expiry, cancellation conditions and decision semantics;
- chronological rejection of stale/clock-reversed responses, in-flight local
  state changes and replayed snapshots, while every result fixes trading
  authorization to false;
- current Sol standard price reservation at USD 4/M input and USD 20/M output,
  mandatory revalidation by the published 2026-11-21 price-window end, and the
  published long-context multiplier boundary; and
- artifact-hash changes requiring revalidation.

The oracle does not make an API call, receive a live provider response,
reconcile provider billing, contact MT5, size risk or emit an order. Production
prompt behavior still requires later chronological no-trading validation against
registered immutable historical replay before Gate 0 can close. External Python
trading remains disabled.
