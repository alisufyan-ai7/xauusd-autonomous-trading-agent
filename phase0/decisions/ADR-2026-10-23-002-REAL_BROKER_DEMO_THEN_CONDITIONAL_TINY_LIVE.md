# ADR-2026-10-23-002 — Real broker DEMO first; conditional tiny-live product direction

**Decision status:** OWNER PRODUCT GOAL REAFFIRMED 2026-10-23; **DEMO executable release NOT YET ADMITTED; LIVE NOT APPROVED.** Prospective addition to existing ADR-2026-10-21-001 V-03/V-08/V-09, ADR-2026-10-22-004, ADR-2026-10-22-006 and ADR-2026-10-23-001. Does NOT retrospectively supersede risk limits, release gates or failure evidence.

## Owner's explicit target, no future chat ambiguity

1. Build a genuinely continuous **production-quality** XAUUSD autonomous trader on the existing Windows ForexVPS, attached only to the attested **Exness Pro MT5 DEMO** USD account and its exact server/fingerprint. This is the **real MetaTrader5 Python API**, real `order_check`/`order_send`, real orders accepted/filled/cancelled by Exness's **DEMO server**, authentic server order/deal/position records, broker SL/TP, cash and margin evidence. **Only account funds are virtual.** It is **not** a fake simulator, paper ledger, ChatGPT-planned hypothetical order, or a developer-mocked broker. Synthetic MT5 fakes remain necessary *tests*, never deployment evidence.
2. Objective completed-bar TPB decides BUY/SELL/NO_TRADE, entry, SL and TP, without operator choosing a trade. Deterministic independently validated Risk Governor alone admits bounded orders; model analyst may veto/advice but never confer execution authority. One approved broker order-sending implementation: existing S2 adapter under a qualified durable coordinator. Never introduce a parallel sender.
3. Fastest correct sequence: qualify/bind actual source/calibrations + controls in the draft branch; demonstrate one genuinely broker-acknowledged **DEMO** lifecycle with real receipts under owner-approved local deployment; then continuously run restricted-session autonomous **DEMO** and perform an *early operational and performance review after roughly 24–48h (1–2 days)*. A positive one- or two-day P/L is NOT proof of profitable expectancy; sparse/no trades are possible and do not satisfy a profitability gate. No obligation to force trades or stop at two days if insufficient evidence.
4. Desired **eventual** separate tiny **Exness Pro LIVE** pilot at **0.01 lot maximum** after DEMO review **only if** a new independent live-capital admission is fully PASS and the owner explicitly approves an exact LIVE account fingerprint, deposit/balance and risk envelope and the activation command. **No automatic promotion at 24h/48h, by profitability, by changing an MT5 login, or by using a DEMO receipt.** The actual minimum 0.01 lot may be TOO RISKY for the future account under frozen 0.25%-of-min(balance,equity,$10k) all-cost limit; NO_TRADE then, not raised risk/Standard Cent.
5. Optimization priority: production readiness and genuine DEMO broker integration immediately, without repeating unrelated historical candle-gap audits. Don't substitute endless synthetic-only runs, another no-order preflight or a manually chosen canary for the final objective. Preserve all native CI, source evidence, accepted risk gates, incident provenance and immutable failures.

## Explicit scope/authorization separation

| Stage | Desired outcome | Current authorization/acceptance |
| --- | --- | --- |
| SOFTWARE | Production-quality one-port, broker DEMO-only XAUUSD agent | Engineer/test on existing draft branch; do not merge without owner approval |
| FIRST_REAL_DEMO_ORDER | Actual Exness DEMO server order/position receipt under 0.01 lot and full Policy A | Owner DEMO-only goal approved IN PRINCIPLE; **effective trading NO_GO** until all source, CI, VPS, operator and incident controls PASS |
| DEMO_CONTINUOUS | 24–48h+ bounded observed continuous runtime, honest trading/cost/fault evidence | Future stage only after first real DEMO lifecycle and operator acceptance |
| DEMO_REVIEW | Early operational reliability, returns and costs report after 1–2 days | Review is an **observation**, not a profitable-expectancy declaration or LIVE permit |
| TINY_LIVE | Conditional independent tiny live pilot | **NOT AUTHORIZED**; separate admitted Exness Pro LIVE account, cash/risk economics, Gate0–5 conditions or explicitly approved independent replacement, adversarial/recovery review, and **fresh exact owner approval** |

**Frozen rules unchanged:** only 0.01-lot maximum, ≤0.25% all-cost stop planned loss, current/stressed margin ≥1000%, projected free margin ≥90% equity, day $75/week $150/concurrent $50/drawdown $500/streak 3R unless a new separately approved risk ADR changes them; NO stop widening/grid/averaging/automatic closing of unknown exposure; E1 human-only emergency/P1 human-gated resumption; never reuse DEMO account identity/credentials to select LIVE.

**Standing owner intent is not a running process:** no VPS connection, no actual broker order, no installed launcher and external Python trading is last known disabled. GitHub CI is synthetic/non-VPS. The S2 order sender still has unconditional `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` before `order_check`/`order_send`. Do not remove the block without genuine source admission and reviewed replacement; no manual BUY/SELL is required.

## Governance conflict requiring explicit resolution

`GOVERNANCE.md` rule 7 and the root README's original Phase 0 statements prohibit trading-capable production implementation while Gate0 incomplete. Later owner ADRs and draft work define an accelerated **DEMO engineering/release candidate path**, without claiming unresolved Gate0 failures PASS. This is an unresolved **accepted-baseline conflict**: record and propose narrowly scoped amendment for separate acceptance, rather than pretending an October *draft* ADR silently rewrites accepted `main` governance. No LIVE release exemption follows. Neither PR38 nor this ADR merges/amends accepted main.

## GitHub-first continuity rule

New chat must open [the real broker DEMO-to-tiny-LIVE critical path](../roadmap/REAL_BROKER_DEMO_TO_TINY_LIVE_CRITICAL_PATH_2026-10-23.md), [machine milestone register](../roadmap/REAL_BROKER_DEMO_LIVE_MILESTONES_2026-10-23.json), `CURRENT_PROJECT_STATE.md`, `CURRENT_PROJECT_STATE_2026-10-18.json` and `NEXT_CHAT_CONTINUITY_HANDOFF_2026-10-23.md`; check *latest actual PR38 HEAD/CI* not an old displayed SHA. Do the next code/tests instead of debating DEMO vs LIVE again.
