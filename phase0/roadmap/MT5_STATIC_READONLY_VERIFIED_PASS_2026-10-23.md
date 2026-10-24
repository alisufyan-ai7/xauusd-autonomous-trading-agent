# Real Exness Pro DEMO MT5 static read-only collector — VERIFIED PASS (2026-10-23)

**Distinct new owner-attended VPS run. NOT a four-hour capture, cost-source admission, broker-order test, trading authorization, or reversal of any earlier immutable failed attempt.**

## Exact source / console attestation

- Canonical static-only launcher reviewed at PR #40 `a54bf80a39faf8a44bdeeed078a912d280b811d8`; exact, export-isolated corrected collector source pin `462ac5e94fbeb656f3415603f12e81fdc3c3bd58`.
- Preflight: `PINNED_LOCAL_IMPORT_PREFLIGHT_PASS_NO_MT5`; real collector printed `NO_PROSPECTIVE_4H__NO_ORDER_CHECK_SEND__NO_TRADE_SETTING_CHANGES`.
- Private raw evidence directory, **VPS ONLY**: `%LOCALAPPDATA%\XAUUSD-BrokerEvidence\static-diagnostic-20261023T133714Z-3582e170822143d2a0ead18fb82906f7`. This path is provenance; private detailed tick, order-history, account data and fees must **never** be uploaded to the repository.
- Exact static completion state: `STATIC_COMPLETE_PROSPECTIVE_NOT_COLLECTED`, followed by PowerShell `STATIC_DIAGNOSTIC_DONE_NOT_CALIBRATION_OR_TRADING_ADMISSION`.
- Sanitized shareable summary on VPS: `SANITIZED_SUMMARY_SHA256=794A326E64B9703CF7066471F708C3E830582E9E2B7A616E6E03440AC7B01A2B`; report content `capture_id_sha256=b45dc3ff0e65d42edd62d659873282debb71353c9ce3fe8c7ddd7b0546289203`. Report schema `EXNESS_DEMO_READONLY_SHAREABLE_SUMMARY_V1`.
- No new trade API calls: `order_check_calls=0`, `order_send_calls=0`, and the code binds only the MT5 read-only allowlist.

## Admitted **static acquisition** checks only

| Observed static signal | Result |
|---|---|
| Fingerprint matches exact pinned Exness Technologies Ltd / Exness-MT5Trial15 DEMO | **true** |
| Global MT5 positions / pending orders | **0 / 0** at both read guards |
| `XAUUSD` quote/symbol / 0.01-lot contract checks | **PASS**, through full static collector |
| Real broker `order_calc_profit` and `order_calc_margin` | **6 complete results**, BUY/SELL with 2, 5, 10 price-distance stops |
| Margin at 0.01 lot for either side | **USD 2.01** broker incremental; **USD 4.02** conservative 2× stress |
| BUY stop cash losses at price distances 2/5/10 | **USD 2.00 / 5.00 / 10.00** (*hypothetical*, costs unknown) |
| SELL stop cash losses at price distances 2/5/10 | **USD 2.00 / 5.00 / 10.00** (*hypothetical*, costs unknown) |
| Broker bid/ask in sample | BUY entry (ask) **4024.303**; SELL entry (bid) **4024.135**; quoted spread **0.168 price units** |
| M1, M5, M15, H1, H4, D1, W1 bar availability | **2000, 1200, 1200, 1200, 1200, 370, 110** respectively |
| Past-four-hour broker historical tick acquisition + validation | **PASS** within full static collector; tick *count* not exposed in shareable summary |
| XAUUSD historical fee rows | **0 observed**, which is **NOT proof of zero commission/fees** |
| Four-hour prospective sampling | **NOT RUN** (null quote slots, proxy, tick count) |
| Prospective v1.1 session/event/cost admission | **FALSE / NOT ADMITTED** |
| Real DEMO `order_check`, pending order placement/fill, SL/TP, deal lifecycle | **NOT PERFORMED** |
| Real-money LIVE | **NOT AUTHORIZED** |

**Source-order interpretation:** successful full static collector means MT5 `initialize`, exact account and zero exposure, symbol quote sanity/freshness, both-side dynamic broker cash/margin, legacy read-only guard, history/deal/order retrieval, all seven bar frames, strict broker historical tick validation, final identity/cash/exposure recheck, and private static and complete report writes finished. This is stronger than the 13:20Z static rejection and independent of the earlier failed comprehensive run. No previous FAIL_CLOSED result is erased or reclassified.

## Gate disposition and next engineering action

**M1 source acquisition — static leg: PASS as read-only evidence.** This is *not* M1 first real DEMO broker order acceptance and does not satisfy execution permit. The 4-hour v1.1 prospective quote capture remains uncollected, independent authenticated official agency events/session metadata unadmitted, XAUUSD fee/swap/deal slippage/gap data absent, full chronological cash journal/drawdown/streak risk proof not qualified, real alerts/restart/fill reconciliation not demonstrated. Do not assume first demo order can be sent, or that fee reserve is zero.

**Prepare (not execute)** a new source-pinned comprehensive 4-hour read-only launcher using the successful exact source lineage, with identical trade API exclusions, no account changes, no scheduled tasks, no four-hour timing shortcuts, no admission through partial or synthetic fills. Conduct one **separately owner-confirmed** unattended/attended prospective four-hour window only after native Windows + Ubuntu offline tests and owner schedule/session assent. Collect privately, print sanitized summary and SHA256; never automatically activate demo orders. If session/holiday/news sources cannot be admitted, mark those outputs as NOT ADMITTED even if quote capture completes.

**Governance:** keep single PR #40 DRAFT/UNMERGED and production `main` unchanged; accepted `GOVERNANCE.md` rule7 still binding, proposed Demo-only reconciliation NOT accepted; `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` is the live S2 hard stop. All earlier import, static tick rejection and regression-test failure receipts remain immutable.
