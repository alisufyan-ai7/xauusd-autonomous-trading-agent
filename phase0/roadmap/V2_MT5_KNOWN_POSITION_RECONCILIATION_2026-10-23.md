# V2 Exness Pro DEMO — known-position broker reconciliation implementation

**Date:** 2026-10-23 (Asia/Karachi). **Status:** IMPLEMENTED_IN_DRAFT; native CI and independent VPS broker tests required. **Authority:** read-only lifecycle engineering, NEVER order admission.

## Exact change

- Added `demo_adapter/src/xauusd_demo/known_position_reconciliation.py`: `KnownPositionBinding`, `observe_known_mt5_position` and `KnownMT5PositionPort.known_position_state`.
- The bridge implements ONLY the read-only `known_position_state` method expected by `QualifiedDemoBrokerPort` in `continuous_coordinator.py`. It does not implement `submit_qualified`, `one_cycle_proposal` or any order operation.
- Binds Exness Technologies Ltd / Exness-MT5Trial15 / USD / exact hashed account identifier / MT5 DEMO trade mode. Never silently uses a LIVE account.
- The opaque coordinator `ticket` must be the broker's **position identifier** (DEAL_POSITION_ID / POSITION_IDENTIFIER), NOT simply the `order_send.order` or `order_send.deal` ticket. Current S2 returns an order ticket, so it is NOT a qualified source for the new bridge. Durable binding persistence at the ACK boundary is a release blocker.
- Requires the exact opening DEAL_ENTRY_IN (order, deal, side, 0.01 lot, magic) in `history_deals_get(position=...)`. Requires any exits to use the opposite side, matching position ID and completely reconciled volume. Missing position alone is UNKNOWN, never CLOSED.
- For OPEN, checks exactly one globally open known position, remaining lot size, matching symbol, magic, direction, broker-side SL and TP. Unknown/foreign/pending order or multiple positions returns UNKNOWN. For CLOSED, requires full entry + exit history, all volume exited, zero global exposure and zero orders; otherwise UNKNOWN. Broker stop/TP close deals may legitimately carry magic zero, but other mismatches refuse.
- Fake MT5 adversarial tests cover duplicates, missing/future/reversing deals, old order versus position identifier, incomplete fills, foreign exposure, wrong/LIVE account, missing SL/TP and uncertainty. No fake tests prove actual Exness behavior.

**Official MetaQuotes specification:** [history_deals_get(position=...)](https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py); [DEAL_POSITION_ID and DEAL_ENTRY codes](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties). Full read-only verification on the owner's Windows ForexVPS has NOT occurred.

## Honest remaining critical path

1. Durable broker ACK-to-known-position binding from the ONE reused S2 order sender and hardened post-fill order/deal/position proof; existing S2 unconditional full Policy A denial remains intact.
2. Source-bound broker `order_calc_profit/order_calc_margin`, frozen full Policy A cash/cost/boundary accounting, exact quote and session.
3. Completed causal objective TPB trigger and official multiagency live Event Guard; missing calendar health vetoes orders.
4. Lifecycle loss/streak and boundary accounting, E1/P1 recovery, tested alerts and watchdog, native Win/Ubuntu and real broker owner-attended acceptance, then one exact pinned actual launch command.

No VPS modification, broker order, trading-setting change, main merge or real-money LIVE trading. Existing Gate0 failure evidence is untouched.


## Native CI proof (new source)

Source + read-first-state HEAD `5e27aca09a72afc6e29cc71e5d3ace276331d33e`:
- [DEMO first order offline validation 39862179555](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39862179555), native Python3.12 Windows 136 passed, Ubuntu 136 passed; Ruff PASS; MyPy 11 DEMO source files PASS; static `PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED`.
- [DEMO admit 39862179472](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39862179472): both native Windows and Ubuntu PASS.
- [Validate records 39862179475](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39862179475): PASS.

These are **synthetic fake MT5 and static native-CI proof only**. No on-VPS broker journal, no order-check/send, no actual Exness position verified.
