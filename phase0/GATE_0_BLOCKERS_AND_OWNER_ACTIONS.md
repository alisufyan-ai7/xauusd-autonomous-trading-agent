# Gate 0 Blockers and Owner Actions

**Status:** INCOMPLETE; production and trading implementation prohibited  
**Exness/API direction:** sufficiently complete for Phase 0 under D-0043, D-0048 and D-0049

## Remaining blockers by class

| Class | Remaining evidence/work |
|---|---|
| Owner decision | OpenAI model selection is closed under D-0073: Sol passed 16/16 v1.1 cases and is selected for later non-trading integration tests; Terra and Luna are not selected. The two benchmark runs cost USD 0.3238708 cumulatively, and no further call is authorized by that approval. No-purchase provider outreach remains non-binding; purchase, charging/auto-renewing trials and binding terms remain prohibited. Strategy volume cap/margin reserve, emergency handling beyond quarantine, pause resumption and operator alert expectations remain open; `OWNER_OPEN_POLICY_DECISION_PACKET.md` presents the conservative `V1 + M1 + E1 + P1 + A1` bundle for an explicit owner choice. |
| Research | Admit the free official-source Event Guard only after live BLS/BEA/Fed/Census/DOL acquisition, horizon, timezone, revision, holiday, outage and schema-drift tests; freeze empirical fill/slippage/gap/swap and shock/normalization models; complete the full OHLC-derived setup golden corpus and registered replay without outcome-driven rule changes. A paid aggregator is optional only on a demonstrated material gap. |
| Diagnostic | Build and separately verify the read-only v1.0 diagnostic artifact; capture authoritative account-specific XAUUSD weekly/holiday sessions; complete controlled VPS observations for the boundary soak and restart/reconnect/network/clock/build matrix; independently probe any future real account. The new offline reliability oracle passes 25/25 scenario traces and 7/7 tests but is not operational VPS evidence. |
| Engineering specification/validation | Analyst benchmark v1.1 passes 6/6 local tests. Its live report contains 48/48 candidate calls and two zero-cost local blocks; Sol passes all component checks on 16/16. Exact per-family field contract, timeout/freshness bounds and a provider-available snapshot/revalidation policy still must be frozen before an Analyst implementation. The official-source Event Guard oracle passes 14/14, but operational acquisition and calibrated shock evidence remain open. Risk/Analyst/replay oracles and execution-core corpus pass. The independent raw-OHLC feature oracle passes 26/26 and now binds an RSR H1/M15 lifecycle, but full cross-timeframe coverage of all five families remains incomplete. Freeze remaining cost/margin/attribution/incident-runbook dependencies. |

The following are **not** Gate 0 blockers now: generic Exness automation permission, proprietary Exness API availability, API Terms capture, dedicated-account coexistence, Policy A selection, or further Exness support contact about OpenAI processing.

## Exact owner actions now

Keep **Disable automated trading via external Python API** enabled and do not fund, enable or run automated demo/live trading.

Next owner action: select or modify the five options in `OWNER_OPEN_POLICY_DECISION_PACKET.md`. Provider purchase/trial activation remains deferred while the official-source Event Guard undergoes conformance testing. No additional OpenAI benchmark run is required or authorized now.

The next active revision should build and objectively verify the non-trading diagnostic/test artifacts, then return only concrete owner choices that cannot safely be resolved by the frozen policies.

No password, identity document, unredacted account number or funds transfer is required.
