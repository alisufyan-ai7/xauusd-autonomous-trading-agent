# Proposed rule-7 reconciliation — source-qualified real MT5 broker DEMO engineering

**Status: DRAFT PROPOSAL ONLY — NOT AN ACCEPTED GOVERNANCE AMENDMENT, NOT AN EXECUTION PERMIT.** Prepared in draft PR #40 after the owner reaffirmed the goal to build a production-quality broker-connected autonomous XAUUSD agent rapidly. This preserves the accepted `main` `GOVERNANCE.md` and immutable G0 failed evidence.

## Conflict to resolve explicitly

- Accepted `GOVERNANCE.md` rule 7 restricts trading-capable implementation before Gate 0 closes.
- Later owner directions ([ADR-2026-10-21-001](../decisions/ADR-2026-10-21-001-AUTONOMOUS-PRO-TRADING-VISION.md), [ADR-2026-10-22-004](../decisions/ADR-2026-10-22-004-FAST-TRACK-DEMO-PILOT.md), [ADR-2026-10-22-006](../decisions/ADR-2026-10-22-006-EXNESS-DEMO-ACTIVATION-INTENT.md), [ADR-2026-10-23-002](../decisions/ADR-2026-10-23-002-REAL_BROKER_DEMO_THEN_CONDITIONAL_TINY_LIVE.md)) call for accelerated, real broker-side execution specifically through the existing Exness Pro MT5 **DEMO** terminal.
- The project may engineer offline/fail-closed safety features on a **draft** branch without falsely marking Gate0 PASS. Merging or deploying trading-capable code under an explicit prospective exception needs **fresh exact owner approval**. Original failed Gate0 evidence remains immutable.

## Narrow proposed future exception (owner to adopt separately)

A future accepted governance amendment could authorize a **DEMO-only engineering and gated-activation track** without implying all historical Gate0 tests passed. Scope would be exactly one source-pinned Windows ForexVPS attached to the *currently attested* Exness Pro MT5 DEMO fingerprint, symbol XAUUSD, lot ≤0.01, risk per trade ≤0.25% all costs, full current/2× stressed M1 margin ≥1000%, free margin ≥90% equity, daily/week/concurrent/drawdown/streak caps, official Event Guard/session coverage, durable pending/filled broker order/deal/position reconciliation, watchdog and delivered alerts, human E1/P1 restart controls. Approval must be precise for code merge and separately precise for VPS terminal+Python trading enablement and first actual DEMO broker order. Each unresolved source or incident blocks activation; UNKNOWN exposure never automatically closed.

The existence of a draft candidate or simulated MT5 tests **does not automatically authorize real Exness DEMO broker orders**. The actual DEMO server order lifecycle must be observed only after the full source conditions pass; each live broker result is recorded with sensitive data redacted. Owner-requested 24–48h initial DEMO review is not enough to assert profitability and does not trigger LIVE.

**No LIVE exemption:** Future Exness Pro real-money account would require a separately admitted exact LIVE fingerprint, deposit/risk/cost/contract, valid governance and separate owner order activation; neither a DEMO success nor changing MT5 login grants authority. If lot minimum 0.01 violates the all-cost 0.25% bound, NO_TRADE.

## Current disposition / decision needed

- Approved to **prepare draft engineering and synthetic tests** under earlier owner instructions; draft PR40 remains blocked for real orders.
- **Not yet decided:** prospective governance scope (rule 7), exact PR40 code merger and DEMO VPS activation. These are distinct approvals to be requested with exact tested SHA and operator instructions, not inferred from open-ended production urgency.
- **Not needed:** any further debate about broker SIM vs DEMO; the goal is actual MT5 API `order_send` to Exness DEMO broker infrastructure using virtual account funds.
