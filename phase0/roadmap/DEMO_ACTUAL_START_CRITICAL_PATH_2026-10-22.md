# Real Exness Pro DEMO launch handoff — current operational truth

**Date:** 2026-10-22. **Owner instruction:** implement, deploy onto the existing ForexVPS Windows MT5 demo terminal and begin real broker-account DEMO autonomous trading as soon as safely possible, no repetitive synthetic/proxy check loops. The user's latest direction explicitly authorizes the DEMO-only objective; it does not approve LIVE trading.

## What is actually connected

- GitHub repo and Actions can be modified/tested. There is **NO DIRECT connected remote PowerShell, RDP, SSH, Windows filesystem or MT5 broker session tool** in this chat. GitHub Actions hosted Windows runner is not the user's Windows VPS. Do not claim VPS code has been deployed or MT5 has received an order.
- The installed ForexVPS MT5 terminal was last attested as the dedicated Exness Pro `XAUUSD` **DEMO** account SHA fingerprint `9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91`, server `Exness-MT5Trial15`, company `Exness Technologies Ltd`, USD currency, with external-Python trading DISABLED. Confirm at action time; do not rely on old snapshot alone.
- Main remains `95875ccf1bddc43491ced1dd4358057b62b7800e`; installed PCR3 remains execution-disabled. PR32 through PR37 are separate stacked drafts. PR24 S2 is a one-human-request canary, NOT the autonomous TPB strategy/continuous broker manager.

## Real source engineering in draft PR37

- `demo_adapter/src/xauusd_demo/broker_money_readonly.py` operates against the user's actual MT5 terminal using only authenticated account/terminal/symbol/quote/flat/history read methods and the MetaQuotes non-ordering `order_calc_profit` and `order_calc_margin` for fixed **0.01-lot BUY and SELL $5 per-oz hypothetical protective-stop references**. Requires account fingerprint, Exness server/company, demo trade mode, exact `XAUUSD` full trading mode, tick value/min volume/grid, fresh quote <=5s, zero positions and pending orders, Python trading DISABLED throughout. No actual order is selected, checked, sent or opened. Output is sanitized aggregate cash/margin and all unclosed Policy A source flags explicitly FALSE.
- `demo_adapter/scripts/real_demo_money_readonly.py` imports MT5 only after explicit `--confirm-readonly` and is a genuine on-VPS broker-observer CLI; exits FAIL_CLOSED with only exception TYPE, never secrets. PowerShell wrapper `phase0/ops/v2_demo_real_broker_money_attended_20261022.ps1` fetches exact frozen source `414f6d1fd339dd6466b793adf2bd87f328804425`, exports to fresh TEMP folder, verifies native Python3.12, executes the new broker observation **without changing installed worktree or scheduled tasks or Python trading settings**. It is OWNER-ATTENDED and has NOT been executed on VPS. This is not another historic candle-gap probe: it supplies genuinely missing live broker stop-loss USD and margin data.
- Native CI Windows/Ubuntu fake broker, account-fingerprint, LIVE rejection, flat checks, terminal-protection, stale quote, actual object return and zero broker send/check tests. Preserve exact current CI status and do not represent synthetic fixtures as live broker evidence.

## What is NOT yet a deployed autonomous DEMO trader

1. S2 `demo_adapter/src/xauusd_demo/mt5_demo.py` intentionally always stops before `order_check/order_send` via `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED`. The new broker_money_readonly module is a real-data receipt source, **not** the full cashflow/stop/risk source required to remove this block.
2. Objective TPB output is still research-only; no strategy has been promoted to a fully source-qualified trade candidate with first-touch and all invalidation/stops. A demo learning pilot may proceed before statistical profitability is proven, but it cannot invent a buy/sell/stop signal.
3. Official real high-impact event-feed health, E1/P1 known-position alerts, post-fill/deal reconciliation and real demo order lifecycle have not passed. The next engineering must join these to the existing S2 executor; **do not clone a competing order-sending lane**.
4. This chat cannot invoke MT5 on the VPS directly, so the owner must execute one exact local installer/launcher or provide an enabled supported remote-computer connection. Current task tools do not include either remote terminal connection or trading.

## Release intent

Owner standing intent: **DEMO_TRADING_APPROVED_IN_PRINCIPLE** with no more separate repetitive per-order approval messages. Effective order execution still **KILLED/NO_GO** until the actual runtime proves frozen 0.01 lot, 0.25% loss and daily/week/drawdown caps, stressed M1 margin, current session/event/quote, SL, no unowned exposure, durable ledger and recovery/alerts; never switch Python trading on before an order-capable tested build. Future 48-hour trial cannot automatically be interpreted as live-money permission.

**Immediate next:** finish the broker-authenticated account/period cashflow+Policy A binding, integrate single TPB and verified Event Guard, run native adverse fault tests, publish one safe isolated VPS installer/launcher that can activate DEMO only after on-device checks, and obtain actual broker order receipt. No more historical W1/rollover probe requests.
