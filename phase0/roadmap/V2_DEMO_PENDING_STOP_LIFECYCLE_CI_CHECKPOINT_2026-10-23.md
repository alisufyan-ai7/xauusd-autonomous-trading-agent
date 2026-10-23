# V2 continuous Exness Pro DEMO — pending STOP lifecycle and five-workstream checkpoint

**Recorded:** 2026-10-23 UTC. **Active branch:** `implementation/demo-continuous-supervisor-20261023`, **PR:** #38 DRAFT, stacked above PR37. **Native-tested code HEAD:** `a13f66358d003ef89afb6dc2624d36a6975eba0a`.

**Release classification: ENGINEERING_ONLY / FAIL_CLOSED / NOT A TRADING LAUNCH.** This note is not approval to merge, change VPS settings, toggle external Python trading, access Exness trading, upload secrets or send orders. Owner's DEMO-only product intent is already resolved; real-money LIVE remains forbidden.

## Exact five-workstream code produced in this continuation

1. **One existing S2 sender.** `demo_adapter/src/xauusd_demo/envelope.py` and `mt5_demo.py` accept separately validated TPB BUY_STOP/SELL_STOP price/SL/TP/time-expiry, broker tick grid and stops-distance; no second unrestricted sender. Existing hard stop `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` remains intact, before order_check and order_send. Tests prove blocked even for new TPB STOP request. No actual qualified order sender or definitive Exness order acknowledgement exists.
2. **Objective technical TPB.** `src/xauusd_agent/features/v2_tpb_stop_plan.py` compiles bidirectional frozen Zone-A first-touch/rejection/confirmation candidate from completed M15 bars, tick-normalized reference stop/TP and structural risk/reward; `demo_adapter/src/xauusd_demo/tpb_s2_bridge.py` preserves setup-key idempotency, 30s proposal deadline versus 60min pending-order expiry. Pure signal component is NOT independent empirical trading permission, full confluence/session/quote/event source not yet productively wired.
3. **Full monetary Policy A PREVIEW.** `demo_adapter/src/xauusd_demo/full_policy_broker_receipt.py` checks DEMO identity, account/quote/exposure epoch, directional `order_calc_profit` AND tick-loss cash consistency, `order_calc_margin`, stop grid/distance, source cost digest, then existing pure `evaluate_full_policy_a` with frozen 0.01-lot, 0.25% all-cost ceiling, cap/streak/margin. It is **nonexecuting**: calibration provenance and expiry, accounting feeds, and trusted source-based guard admission are NOT complete. Its externally supplied guard flags MUST NOT authorize trading.
4. **Official-source calendar state.** `demo_adapter/src/xauusd_demo/official_calendar_supervisor.py` reuses frozen official agency admission from `src/xauusd_agent/guards/v2_official_source_gate.py`, checks revisions/freshness and preserves moved-event old lock windows; unexplained future-event disappearance permanently quarantines. Existing source collector/normalizer in `phase0/validation/event_guard` remains a separate read-only candidate requiring on-VPS official-source conformance and end-to-end runtime provenance before event-clear is authoritative.
5. **Recovery/alert transports.** `demo_adapter/src/xauusd_demo/ops_safety_watchdog.py` persists killed/active/quarantine, clock rollback/staleness and two-channel durable incident outbox. `alert_delivery.py` implements TLS SMTP and Telegram Bot sendMessage with private VPS runtime credentials, numeric consented Telegram chat ID and sanitized exceptions; only fake transport CI is proven, no real delivery confirmed. No automatic E1 position liquidation or P1 auto-restart.

## Most recent critical S2 pending-order sequencing addition

- `demo_adapter/src/xauusd_demo/continuous_coordinator.py` now keeps `PREPARING` and differentiated `PENDING`, `ACKNOWLEDGED`, `CLOSED`, `UNCERTAIN`. On accepted STOP order it persists `PendingBrokerAck` (order ticket, side, 0.01 lot, entry/SL/TP, expiry and fingerprint) atomically. It does **not** invent `QualifiedBrokerAck` at order placement.
- `demo_adapter/src/xauusd_demo/pending_mt5_reconciliation.py` performs read-only `orders_get`, `history_orders_get(ticket=order_ticket)`, `history_deals_get(ticket=order_ticket)`, `positions_get` broker-source checks. MetaQuotes `history_deals_get(ticket=ORDER)` filters DEAL_ORDER, while `history_deals_get(position=ID)` filters DEAL_POSITION_ID (see <https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py>). A FILLED transition requires exact order/deal/position match with protective SL/TP; terminal expiration requires empty deal/position exposure. Partial/foreign/unknown makes QUARANTINED/no retry.
- A crash before an atomic acknowledgement stores PREPARING, which may never resend automatically; an ambiguous send/reconciliation similarly quarantines. S2 has **no real qualified send path**, and accepted STOP/fill cases are synthetic fakes only. No claims about actual broker fidelity.
- Native CI found and preserved two real defects: source formatting/import and MyPy pending/filled union narrowing; subsequent tests caught referencing a filled receipt variable after committing a pending acknowledgement. They were corrected in commits ending at **`a13f66358d003ef89afb6dc2624d36a6975eba0a`**. Keep failed runs visible; do not relabel failures as passes.

## Exact CI evidence at corrected source head

- [demo-first-order-release-offline run 39918014924](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39918014924) **SUCCESS**: native Windows Python3.12 **245 passed**, Ubuntu Python3.12 **245 passed**, Ruff **PASS**, MyPy **17 source files PASS**, package build **PASS** and execution-disabled static `PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED`.
- [demo-admit run 39918014935](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39918014935) **SUCCESS**: Windows and Ubuntu.
- [production-candidate run 39918014923](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39918014923) **SUCCESS**: Windows and Ubuntu.
- [Validate records run 39918014943](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39918014943) **SUCCESS**.
- These are **offline synthetic CI validations**, no native user VPS acceptance or broker order. This documentation commit will be a new PR38 HEAD; do not imply the code CI runs tested subsequent documentation bytes.

## Blocking direct execution and one-command launch

A. Complete independently verified integrated concrete `QualifiedDemoBrokerPort` feeding the single S2 pending STOP order sender, with full issuer/receipt/source authenticity and **no synthetic** `FullPolicyAInput` substitution. Only after actual source+fault proof can S2's unconditional hard stop be replaced by a reviewed source-bound guard.

B. Real Exness broker profit/margin, tick value, broker commissions/fees/swaps/slippage/gap buffers, 100% ledger/history/deal/position/period/high-water provenance, freshness and current + 2× stress M1 binding; separate approved calibration methodology and live dry-run evidence.

C. End-to-end deterministic TPB first-touch campaign persistence, seven-frame live ingestion, shadow replay and quote/sessions/expiration/worst-stop semantics with the legitimate two-phase STOP order send/fill/close and cash journal updates. Document empirical false-signal risks; never claim profitable.

D. Operational agency capture/rights, current official source parsing/admitted revisions, actual session/holiday and Event Guard health, H1/M15 shock normalization, alert channel delivery/drill, watchdog disconnection/restart/unknown-exposure/P1 recovery tests in native Windows and attended VPS.

E. Source-pinned signed/hashed package; one user-run VPS PowerShell install-and-**actual DEMO trading** command ONLY after A–D complete. Never present synthetic coordinator or read-only preflight as the requested trading-launch command. External Python trading is currently disabled; the Python API cannot claim it toggled the MT5 GUI-only setting.

**Immutable constraints:** 0.01 lot maximum; 0.25% per-trade all-cost loss cap; frozen 1000% current/stressed M1 and 90%-of-equity free margin, day/week/concurrent/high-water/streak controls, known-only exposure, E1 human emergency, P1 human-only resumption, no auto-close of unknown exposure; trading LIVE remains disabled. Production main and Gate0 failures unchanged.


## FOLLOW-ON: pending-order news/session lifetime admission (2026-10-23)

Source/test commit `ab1571a0bb2fe526e1cf7e3693a7810220e4e7bc` adds `demo_adapter/src/xauusd_demo/pending_entry_window_guard.py` and `demo_adapter/tests/test_pending_entry_window_guard.py`.

A STOP order may fill at any time before its broker expiry. Passing the official Event Guard only at proposed submission time is **insufficient**. The nonexecuting `screen_pending_entry_window` fails closed unless all five `VerifiedOfficialSnapshot` agencies are fresh, admitted and unconflicted, shock/normalization are known, session coverage extends at least one minute past order expiry, maximum active lifetime is ≤60 minutes, and no Tier-1 (30m) / Tier-2 (15m) pre/post protected release window intersects the broker-active lifetime including one-minute settlement margin. Every unknown clock, source or session returns a DENY. The source authenticity and current session boundary MUST be independently established on the VPS; arbitrary caller timestamps/flags are NOT execution evidence. **The S2 order guard remains unchanged and this lifetime screen has not yet been integrated into an admitted live broker execution port.** Sudden unscheduled events or revisions after an order is placed require independent runtime cancellation logic; that remains blocked and is NOT claimed solved.

Native corrected source CI: [demo-first-order-release-offline run 39918805503](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39918805503) **SUCCESS**, Windows Python3.12 **262 passed**, Ubuntu Python3.12 **262 passed**, Ruff PASS, strict MyPy 18 source files PASS, static trading-disabled `PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED`; [demo-admit 39918805615](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39918805615) PASS, [production candidate 39918805328](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39918805328) PASS.

**Still FAIL-CLOSED for real DEMO orders:** qualified S2 trading port/source-policy binding, live broker risk and costs/cash journal reconciliation, operational official feeds and session snapshots, continual pre-fill Event Guard cancellation, native VPS and two-channel alerts/restart tests, and one source-pinned DEMO launch script. All merge and LIVE restrictions preserved.
