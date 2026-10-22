# V2 DEMO-first: broker-monetary risk consistency preflight

**Date:** 2026-10-22. **Status:** DRAFT / preflight code only / no broker execution permission.

## Why now
The owner has twice approved proceeding with the fastest safe Exness Pro DEMO engineering next step, explicitly prioritizing getting to one autonomous deterministic TPB setup instead of repeating historic gap probes. The authoritative ancestor is PR34 HEAD `6ca2966855ce36e8ddc91dd99b7c22bdf22683e2`. PR32/33/34 are open drafts; production main `95875ccf1bddc43491ced1dd4358057b62b7800e` unchanged.

## Work delivered
New `src/xauusd_agent/risk/v2_demo_pilot_broker_risk.py` joins already-frozen `evaluate_full_policy_a()` cash/margin/period-loss rules to **broker-issued read-only** `order_calc_profit` and `order_calc_margin` result fields (received as data; no MT5 connection or calls in this module). The preflight rejects exact DEMO fingerprint/server/company/trade mode or XAUUSD mismatch, unexpected open positions/orders, stale quote, drift from BUY ask/SELL bid, lot beyond 0.01, stop off tick grid, broker-returned loss not matching conservative tick-value loss, margin inconsistency, missing source reconciliation, unknown active session and unknown/blocked official Event Guard. External Python automated trading must remain DISABLED in this review-only phase. It makes NO assertion that a caller-provided boolean proves source identity: a real broker adapter must establish authoritative evidence at the same epoch.

**Hard negative:** even when all fields and risk math reconcile, the only favorable status is `MATH_RECONCILED_REVIEW_ONLY`; `execution_permitted` is always FALSE. There is no `order_send`, order_check, MT5 initialize, VPS config edit, activation permit or scheduled task in this module. It does NOT prove TPB strategy qualification, live official calendar feed, real order-check rejection handling, paper journal integration, known-position closure, alert delivery or P1/E1 recovery.

## Why this matters
Existing S2 `demo_adapter/src/xauusd_demo/mt5_demo.py` has broker mechanics for an **operator-selected** one-order canary but deliberately raises `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` before `order_send`. The new work supplies a testable broker-cash consistency veto, not that missing adapter, and **does not change S2 release safety**. Next real engineering is a dedicated Exness read-only receipt factory that calls broker `order_calc_profit`/`order_calc_margin` with exact identity and source snapshots, computes period history, persists the intent ledger and safely declines unknown results. Then integrate full objective TPB and AI Event Guard, test Windows native fault recovery, and ask separately for exact scoped first DEMO order authorization.

## Real truth vs test coverage
Unit tests are synthetic: they validate mismatched server/live account, malformed quote, unverified history/event, monetary mismatch, stop/margin and frozen Policy A. They are NOT a measured cash result from Exness or an OOS P/L result, and are not proof 48h trading will be profitable.

All records durable in this branch; no changes on VPS, no broker orders, no Python trade enable, no live account, no Gate0 failure rewrite, no merges or production deployments.
