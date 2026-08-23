# Selected Sol Analyst runtime validation report

**Date:** 2026-08-23 UTC  
**Result:** PASS — 14/14 offline tests  
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
  response-model mismatch;
- current Sol standard price reservation at USD 5/M input and USD 30/M output,
  including the published long-context multiplier boundary; and
- artifact-hash changes requiring revalidation.

The oracle does not validate a production prompt, make an API call, receive a
provider response, reconcile provider billing, contact MT5, size risk or emit an
order. External Python trading remains disabled.
