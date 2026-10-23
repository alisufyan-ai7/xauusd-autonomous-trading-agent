# Continuous autonomous Exness Pro MT5 DEMO release — implementation checkpoint

Owner explicitly selected **existing Exness Pro MT5 DEMO**, one continuously autonomous trading runtime and a single VPS install/launch command, with frozen Policy A. This is **not** approval for real-money LIVE. Avoid further retrospective candle-gap owner diagnostics.

## Current real engineering

Start from draft PR37 tip `027ac0419528d1a3349fcfad71a4edbb8971b303`. Add `demo_adapter/src/xauusd_demo/prospective_cash_journal.py`: durable SQLite WAL/FULL for a **new prospective, clean account campaign**, admitted only with UTC balance/equity equal, no open positions/orders, full historical deal inventory and **no past trading deals**. All later broker deals must retain immutable id/timestamp/amount/magic; unknown funding or foreign trading, missing history, changed fingerprint, cash mismatch or clock rollback stops entry. Any losing trade pauses further risk until human review. Track daily/week baselines, inception equity/highwater, realized cash and unowned-exposure guard. This strictly rules out silently resetting past account drawdown and cannot place orders.

## Honest open blockers to genuinely autonomous trading

1. An objective complete TPB trade candidate as opposed to explicitly research-only v2 TPB hypothesis; first touch/confirmed candle/stop/target/normalization and costs must be correct.
2. Broker-authoritative monetary `order_calc_profit/margin`, calibrated fees/slippage/commissions and source-bound full Policy A receipt; new pure cash ledger alone is not an executable risk pass.
3. Official live multiagency high-impact Event Guard freshness and a bounded Analyst veto; no event uncertainty may silently pass.
4. Remove the old S2 unconditional cash risk denial **only once** new source-bound full Policy A and native fault tests replace it. No fake Boolean or static gate deletion.
5. Actual continuous runner with supervised daemon/interactive scheduler, one account and position, known-position SL/TP/deal reconciliation, intent-before-send/idempotency, time/session exit, alert delivery and watchdog.
6. Existing VPS terminal external Python trading is disabled and cannot be switched by a normal MT5 Python call; launch command must not falsely claim to toggle a UI-only setting.

This checkpoint is intended for owner-independent native code/test progress, not a release. Do not represent new SQLite tests or a running timer as live autonomous trades. GitHub Actions are not the Windows VPS. Production main, user funds, installed MT5 and scheduled tasks untouched; stacked PRs remain draft.


## 2026-10-23 continuation after original handoff — STOP order state machine and five-workstream draft

**Do not misread the historical SHA at top of this document as current.** Subsequent work on PR38 implemented broker-reconciled pending STOP lifecycle, deterministic TPB Zone-A BUY/SELL STOP/SL/TP candidate, cash-risk nonexecuting MT5 preview, durable source-revision Event Guard, watchdog/outbox and SMTP/Telegram delivery transport fakes. Native-corrected **code** HEAD: `a13f66358d003ef89afb6dc2624d36a6975eba0a`; release-offline Actions **39918014924 SUCCESS** (245 Windows and 245 Ubuntu), demo-admit **39918014935 SUCCESS**, production-candidate **39918014923 SUCCESS**, before subsequent documentation. Exact source and remaining blocks are in [this new checkpoint](V2_DEMO_PENDING_STOP_LIFECYCLE_CI_CHECKPOINT_2026-10-23.md). **S2 unconditional full Policy A real-order hard stop is untouched; no VPS deployment or actual broker order; not production-ready.** PR32–38 remain stacked DRAFT unmerged. All predecessor G0 failures immutable.
