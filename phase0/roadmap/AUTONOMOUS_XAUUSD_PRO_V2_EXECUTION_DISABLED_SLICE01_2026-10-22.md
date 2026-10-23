# V2 implementation slice 01 — execution-disabled market context and shadow selector

**Status:** REVIEW ONLY / SHADOW-ADVISORY / NOT DEPLOYED. Date: 2026-10-22 (Asia/Karachi).

## Owner authority and provenance

- Owner approved V2 specification scope and said `proceed with next step`. This authorized starting isolated **execution-disabled** engineering; it did **not** approve changed numeric Policy A, strategy profitability, OpenAI paid/live transport, a demo/live order, external Python trading enablement, deployment, or merge of this implementation PR.
- Documentation PR30 and V2 specification PR31 are both merged. Accepted V2 spec baseline main at inception: `95875ccf1bddc43491ced1dd4358057b62b7800e`; [spec source](AUTONOMOUS_XAUUSD_PRO_V2_ARCHITECTURE_AND_ACCEPTANCE_2026-10-22.md).
- Existing production PCR3 `pcr3-execution-disabled-e0383a50e2cc`, S2 PR24/26 and separate speculative PR29 remain physically untouched, open/unmerged, broker execution off.

## What this slice actually implements

1. `src/xauusd_agent/features/v2_market_context.py`: pure frozen `ContextBar`/seven-frame `ContextTimeframe` W1, D1, H4, H1, M15, M5, M1; verifies positive finite OHLC, completed UTC candles, ordered nonoverlapping history, minimum **context-only** warmup, M1/M5/M15 recent contiguous bars, staleness thresholds, <=5s quote freshness, cross-M1 gross price sanity, exact XAUUSD and explicit externally attested `session_clear`, `event_clear`, `shock_clear`, `broker_health_clear`. Missing/unhealthy -> `NO_TRADE` with sorted reasons. It never imports MT5, accesses credentials, invokes a model, sizes positions, requests orders, or performs risk/broker actions.
2. `from_existing_core_bar()` maps the preexisting read-only H4/H1/M15 `Bar` into `ContextBar` without altering values. **W1, D1, M5, M1 are NOT supplied by the existing MT5 adapter**, and are NOT synthesized from other frames. The new context is deliberately `NO_TRADE` until true, independently validated observation and schedule/event guard inputs arrive. The context warmup here **does not** satisfy Phase0 frozen strategy warmup of >=300 H4, >=500 H1, >=1000 M15.
3. `src/xauusd_agent/features/v2_shadow_selector.py`: takes only already independently evaluated `SetupCandidate` records from the existing setup evaluator; requires one research-admitted nominated champion family, an exact decision epoch and exactly one unambiguous proposed setup. Competing/duplicate/unadmitted setup returns `NO_TRADE`; successful output is `SHADOW_CANDIDATE`, exposing identity/direction only. This **does not generate TPB predicates or select a profitable strategy**. `execution_permitted=False` always, and no broker connection exists.
4. `tests/unit/features/test_v2_shadow_context.py`: **13 authored tests, not yet run against exact repo Python3.12/Windows**; covers all seven completed frames, missing, incomplete/future, stale/clock-skew quote, unhealthy session/events, no-lookahead, micro gap, OHLC/type, no strategy admission, candidate and duplicate/conflict selection, NO_TRADE from stale context, immutable execution-denial and adapter preservation.

## Deliberately unsolved in this slice

- **No new live market data retrieval** for W1/D1/M5/M1. These require a read-only verified MT5 data port and provider timestamp/timeframe mapping, separate from existing PCR3 scheduler.
- **No automatic causal TPB predicates / regime classifier** and no independently accepted champion strategy. Existing `evaluate_setup` requires explicit source-backed predicates, stop/TP validity, and must never be fed fabricated `TRUE` flags.
- **No separate official live Event Guard/session/shock health**; boolean inputs are required; missing sources force `NO_TRADE`, not a fabricated clear state.
- **No AI provider transport or OpenAI paid model calls**: current approved live Sol benchmark and future usage are separately gated.
- **No full account-aware cash Policy A broker binding**, execution, persistent dedup/position manager, watchdog, alerts, or DEMO order. Historical Gate0 and Demo-ADMIT failures remain blocking as recorded.
- **No native CI pass claim**. The previous PR29 GitHub Actions runs failed without accessible job steps/logs, cause unknown. This PR needs a new exact-head CI attempt, or independent native Windows Python3.12 results before acceptance; avoid false success claims.

## Next isolated development increment after review

Implement an execution-disabled **read-only seven-timeframe MT5 observation port** with strict cursor, closure and DST/session-gap handling and broker-account allow-list. Build objective setup predicates and a candidate-provenance/strategy-version envelope from frozen Phase0 features. Integrate authoritative Event Guard and audited NO_TRADE reasons behind a null execution sink. Separately solve CI/Windows exact-source tests. Do not attach the order-capable S2 code or alter terminal Python API protection as part of this increment.

## Risk and authorization baseline preserved

Exness Pro only, Standard Cent banned. Current normalized owner approval remains to research/prepare execution-disabled software **only**. Broker DEMO/LIVE `order_send`, `order_check`, `order_modify`, `order_close`, external-Python trading enable and any profile switch are **NOT AUTHORIZED**. Current Policy A fixed 0.25%/0.01 lot/current+stressed M1/period limits remain authoritative, pending a separate versioned owner decision. No self-changing live AI strategy or unknown-exposure closure.

All new reasons, branch SHAs, owner action and exact CI outcomes must be persisted in GitHub under `phase0/DECISION_LOG.md`/dated ADR if substantive and human/machine project state; do not overwrite old failures.
