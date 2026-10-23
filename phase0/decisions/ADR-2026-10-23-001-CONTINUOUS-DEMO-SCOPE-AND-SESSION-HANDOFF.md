# ADR-2026-10-23-001 — Resolved continuous MT5 DEMO scope and GitHub continuity handoff

**Recorded 2026-10-23. Status:** accepted OWNER PRODUCT INTENT; **implementation and actual broker order release NOT YET ADMITTED**.

## Owner's final resolved choice

The owner explicitly chose **the EXISTING Exness Pro MT5 DEMO** account (XAUUSD, virtual USD 10,000, real broker quote/order API, `Exness-MT5Trial15`) for **continuously autonomous DEMO trading**. The prior ambiguous phrase "real live trading" refers to actual continuous broker DEMO operation on ForexVPS, NOT a real-money LIVE account or any Standard Cent account. **Do not reopen this clarification.**

The requested output is an independently validated autonomous single-strategy TPB runtime, packaged to install and launch via **ONE pinned PowerShell command on the Windows VPS**. No manual buy/sell signal selection, screenshots, artificial restriction to one or two lifetime trades, duplicate research-only probes or repeated per-order approval ceremonies. When multiple new qualified setups occur over time, it should safely cycle orders, at most one known XAUUSD position simultaneously, under frozen Policy A. Zero trades on days without safe setups is a valid outcome. No guaranteed profitability/volume.

## Operational guardrails that owner urgency does NOT waive

- Frozen Policy A 0.01 maximum lots, all-cost stop cash loss at most 0.25% of min(balance, equity, 10k allocation), current and 2x M1 stressed margin >=1000%, free margin >=90% equity, day/week/streak/normalized drawdown rules, broker-side protective stop, known-only exposure.
- Objective completed-bar TPB strategy, source-verified current session/quote and high-impact official Event Guard; unknown -> NO_TRADE. Analyst is advisory only; it cannot authorize risk/order execution.
- Durable intent-before-send, no retries on ambiguous ack, known-ticket fills/closures/deal reconciliation, alerts/watchdog, E1 human-only emergency and P1 human-gated resumption. No auto-close of unknown exposure.
- Require executable and tested concrete MT5 order port; do not bypass the old S2 `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` with a constant or fabricate green release state.
- Production main and old Gate0/read-only FAIL_CLOSED evidence remain immutable; stacked draft PRs require exact review before merge. No LIVE real-money trading permission.
- GitHub API/Actions are not direct RDP/PowerShell access to the owner's Windows VPS. A user-run one-command launcher is still required unless a suitable remote computer connector is actually connected. Never claim installed/running broker orders solely from GitHub CI.

## Actual snapshot at handoff

The code lineage is **DRAFT PR38** (`implementation/demo-continuous-supervisor-20261023`), source-before-handoff HEAD `b408319424a8248bc043fe73bea364be58c2485d` and upstream PR37 `027ac0419528d1a3349fcfad71a4edbb8971b303`. Windows/Ubuntu Python 3.12 CI 100/100 fake adapter tests each PASS in Actions `39858810841`; demo-admit `39858810845` and records `39858811113` PASS. Implemented durable cash journal, read-only broker cash source, broker-neutral `run_forever` continuous coordinator and no-order safety proof. **MISSING**: real source-qualified MT5 order port, complete TPB candidate, operationally verified Event Guard, full broker Policy A + alerts/known-position release, and true VPS install/activation. **No real DEMO broker orders or VPS runtime deployment occurred.** Do not call the current code "ready".

## Handoff source of truth

Full technical and conversation decision transfer is `phase0/roadmap/NEXT_CHAT_CONTINUITY_HANDOFF_2026-10-23.md`. Read-first human and JSON project-state documents point there, with exact PR/CI/authorization context. New chat must read the GitHub files, inspect latest PR38 HEAD, **continue implementing** (not merely discussing) until a safe single-command DEMO launch candidate is actually ready.

This ADR supersedes only the obsolete ambiguity about DEMO vs real-money LIVE. It does not remove older FAIL evidence or override E1/P1 and frozen Policy A.
