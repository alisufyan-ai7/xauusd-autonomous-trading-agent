# Gate 0 Blockers and Owner Actions

**Status:** INCOMPLETE; production and trading implementation prohibited  
**Exness/API direction:** sufficiently complete for Phase 0 under D-0043, D-0048 and D-0049

## Remaining blockers by class

| Class | Remaining evidence/work |
|---|---|
| Owner decision | OpenAI benchmark configuration/spend is approved under D-0059, but a separate-project API key is not securely configured. No-purchase outreach to Trading Economics/Benzinga is approved under D-0064 and awaits sender contact confirmation at submission; purchase and binding terms remain prohibited. Strategy volume cap/margin reserve, emergency handling beyond quarantine, pause resumption and operator alert expectations remain open. |
| Research | Admit licensed data sources after written rights/sample tests; freeze empirical fill/slippage/gap/swap models; complete repeated shock/session calibration; execute the full OHLC-derived setup golden corpus and registered replay without outcome-driven rule changes. |
| Diagnostic | Build and separately verify the read-only v1.0 diagnostic artifact; capture authoritative account-specific XAUUSD weekly/holiday sessions; complete the 24-hour/boundary soak and restart/reconnect/network/clock/build matrix; independently probe any future real account. |
| Engineering specification/validation | Machine-readable Analyst benchmark schema/prompt/corpus is dry-verified; live Terra/Sol/Luna results remain absent. Risk/Analyst/replay oracles and execution-core corpus pass. The independent raw-OHLC feature oracle passes 21/21, but full cross-timeframe family lifecycle coverage remains incomplete. Freeze remaining cost/margin/attribution/incident-runbook dependencies. |

The following are **not** Gate 0 blockers now: generic Exness automation permission, proprietary Exness API availability, API Terms capture, dedicated-account coexistence, Policy A selection, or further Exness support contact about OpenAI processing.

## Exact owner actions now

Keep **Disable automated trading via external Python API** enabled and do not fund, enable or run automated demo/live trading.

Next owner actions: create a separate OpenAI API project with a USD 10 project budget and securely configure its project-scoped API key on the benchmark runner host; do not paste or commit it. For the approved provider outreach, confirm the sender name/email and any optional organization/title/phone immediately before submission. No provider commitment may be accepted.

The next active revision should build and objectively verify the non-trading diagnostic/test artifacts, then return only concrete owner choices that cannot safely be resolved by the frozen policies.

No password, identity document, unredacted account number or funds transfer is required.
