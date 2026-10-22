# ADR-2026-10-22-005 — First DEMO order release test: safety PASS, actual order NO_GO

**Date:** 2026-10-22 (UTC). **Type:** release test outcome, not new broker authorization. **Status:** FAIL_CLOSED_FOR_ACTUAL_ORDER.

## User mandate and source baseline

Owner requested: "test first-DEMO-order release". Treat this as testing, not permission to place an Exness DEMO order, toggle MT5 Python trading, deploy a new VPS runtime, merge drafts, or bypass one frozen Policy A requirement. Latest ancestor PR35 at `b3cf0b4732f1b8e8e92f119daaee4073a1da1ec4`; new draft stacked PR36 contains a dedicated offline release test lane without changing the trading adapter.

## Result

Exact tested PR36 code `6e9b1b380c4eaa1a0c76d5c0b58d29b3a5ec1873`:

- [First DEMO release offline CI 39804914839](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39804914839) PASS **49 synthetic/fake-MT5 tests on Windows Python3.12** and **49 on Ubuntu Python3.12**; no skips; Ruff PASS, MyPy six DEMO source files PASS; separate package boundaries PASS; DEMO wheel/source distribution built successfully; core execution-disabled capability PASS.
- [Existing demo-admit CI 39804915037](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39804915037) PASS both Windows/Ubuntu, 49 tests each. Validate records run `39804915061` PASS.
- New `test_first_demo_order_release.py` uses **FakeMT5 only**, with a synthetic activation permit and synthetic Python-trading flag, and verifies the real S2 method unconditionally rejects with `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` *before* the fake broker's `order_check` or `order_send`; exact zero check/send counts; submission ledger remains empty, kill/quarantine state persists across database restart and does not rearm without human reset. No real MT5 terminal accessed by CI. Initial test-import lint failure remained in older CI attempt and was corrected before the passing commit.
- Static no-order sentinel `demo_adapter/scripts/verify_first_order_release_gate.py` reports `PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED`, **not** execution READY. This is a safety-test success and a release-admission NO_GO. The main source package still contains no broker order-sending capability; S2 remains separately packaged.

## Full first-order admission blockers (not waived)

1. No broker-authoritative, *same-epoch* real Exness Demo stop-loss dollar value, margin, symbol specs, spread/cost calibration, period cashflow and day/week/drawdown exposure ledger bound into full frozen Policy A and `order_check`.
2. One complete, objective, frozen TPB signal/stop candidate and current-session/quote quality evidence are not yet integrated as a real broker-eligible setup. A research hypothesis must not be turned into order instructions.
3. Real official-source Event Guard schedule/freshness/shock normalization remains unadmitted; unknown source means NO_TRADE. Live bounded Analyst remains disabled by default.
4. Journal intent-before-send, broker-side fill/deal and known-position stop/close reconciliation, restart ambiguity quarantine, E1/P1 watchdog, alert delivery and recovery drills are not yet proven for a real continuous DEMO executor.
5. Separate exact owner approval is still required for a first attended real DEMO order and later for 48-hour autonomous DEMO activation. Account is Exness **Pro DEMO** only, never Standard Cent or LIVE.

## Decision

**Do not submit a real DEMO order now.** Do not bypass the hard S2 full Policy A stop or assume a green release-test workflow grants permission. Next engineering is a *read-only authenticated broker-calc/source collector* with exact account verification and full Policy A period financial records, then a tested one-strategy objective TPB + official Event Guard + durable real broker lifecycle release. Avoid duplicate historical gap diagnostics and strategy proliferation. Keep 0.01 lots, <=0.25% min(capital), M1 and cumulative period limits, human E1/P1, no auto-close unknown exposure, and all original Gate0 failures unchanged.

**Durability:** source+machine evidence `phase0/evidence/V2_FIRST_DEMO_ORDER_RELEASE_TEST_2026-10-22.json`; read-first human/machine state updated on PR36. PR32/33/34/35/36 remain unmerged drafts; production `main` unchanged, no VPS deploy, real order check/send or MT5 settings change.
