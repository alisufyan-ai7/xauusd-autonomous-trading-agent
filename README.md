# XAU/USD Autonomous Trading Agent

## Current product direction — READ FIRST (draft PR38, 2026-10-23)

**Goal:** One genuine continuously autonomous XAUUSD system on the owner's Windows ForexVPS, sending actual MetaTrader5 Python API orders to the **existing Exness Pro DEMO broker server**, receiving real DEMO order/deal/position/SL+TP receipts. Virtual DEMO account funds; **not** hypothetical signals or simulated fills. Do **not** use Standard Cent or manually select BUY/SELL. The intended **later** 0.01-lot Exness Pro LIVE pilot is a separately admitted and expressly approved stage; a 24–48h DEMO performance review never auto-authorizes it.

**LATEST VERIFIED DRAFT TESTS:** 2026-10-23 **M1 durable goal contract** code/test HEAD `f40f1d68e587a22c47869519434077a96cab071f`: [release CI 39933014003](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39933014003) **SUCCESS**, Python3.12 **283 Windows + 283 Ubuntu tests passed**, Ruff PASS, MyPy 19 files PASS, static `PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED`; [DEMO-admit 39933013847](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39933013847) SUCCESS, [production-candidate 39933013955](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39933013955) SUCCESS, [record validation 39933014007](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39933014007) SUCCESS. The new `demo_adapter/tests/test_real_broker_product_milestone.py` enforces REAL Exness DEMO broker order acceptance as the desired product, forbid automatic LIVE after 24–48h, and checks the S2 order denial is still present. All CI is **OFFLINE/SYNTHETIC**; no live Exness DEMO order or VPS modification.

**Current truth:** PR38 is DRAFT, code still **blocks** actual DEMO broker order submission before `order_check/order_send` and has no verified VPS deployment. Most recent native source-verified tests at `ce1e422337a8afdd23d1f18674490f5b79882b62` were 279/279 PASS on Windows/Ubuntu ([CI](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39923675345)); offline fake MT5 tests **are not** broker-server evidence. Actual branch HEAD changes after documentation commits. Main at 2026-10-23: `95875ccf1bddc43491ced1dd4358057b62b7800e`. Keep LIVE, deployment and owner-independent merges disabled.

**New chat reading order:**
1. [Current real broker DEMO → conditional tiny LIVE roadmap](phase0/roadmap/REAL_BROKER_DEMO_TO_TINY_LIVE_CRITICAL_PATH_2026-10-23.md)
2. [Machine milestones](phase0/roadmap/REAL_BROKER_DEMO_LIVE_MILESTONES_2026-10-23.json)
3. [Owner decision ADR-2026-10-23-002](phase0/decisions/ADR-2026-10-23-002-REAL_BROKER_DEMO_THEN_CONDITIONAL_TINY_LIVE.md)
4. [Current human state](phase0/roadmap/CURRENT_PROJECT_STATE.md) and [JSON state](phase0/roadmap/CURRENT_PROJECT_STATE_2026-10-18.json)
5. [Full continuity handoff](phase0/roadmap/NEXT_CHAT_CONTINUITY_HANDOFF_2026-10-23.md); latest PR38 source/CI, parent stacked drafts, `GOVERNANCE.md` and frozen Policy A.

**Unresolved governance conflict:** the ACCEPTED `main` [`GOVERNANCE.md`](GOVERNANCE.md) rule 7 still prohibits trading-capable implementation until Gate 0 completion, while later owner draft ADRs prioritize accelerated DEMO engineering. This branch records the product goal and proposes a controlled, separately accepted reconciliation; it does **not** assert main governance was amended. Keep blocked broker order until exact acceptance and source/VPS proof. Historical Gate0 fail evidence remains immutable.

**Security note:** GitHub API returned repository visibility **public** on 2026-10-23 despite earlier descriptions of a private repository. Do not publish account numbers, credentials or raw private evidence; owner should check repository visibility. This note does not assert settings have been changed.

## Historical accepted Phase 0 baseline

The original Phase 0 README correctly reflected initial restrictions at its earlier revision. In accepted `main`, Gate 0 remains incomplete and production trading release remains prohibited. Frozen specs, append-only decision log, read-only collectors and rejection/validation evidence are preserved in `phase0/`. Subsequent work in draft PR branches is engineering/prospective documentation only until specifically accepted and authorized.

The original canonical Phase 0 dossier is `phase0/PHASE_0_SPECIFICATION.md`. The append-only history is `phase0/DECISION_LOG.md`; sensitive/raw evidence must not be committed.
