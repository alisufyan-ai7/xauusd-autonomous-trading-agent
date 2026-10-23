# XAU/USD Autonomous Trading Agent

## Latest PR cleanup — one remaining code PR (2026-10-23)

**26 superseded historical/stacked PRs were closed unmerged after preserving their exact source history in five archive branches. Exactly one draft main-based PR remains: [PR40](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/40).** Current accepted main is documentation-only `bf6c931fac208ed2b781a2d22734df1124dea1e6`; all trading code is in that UNMERGED PR40 review. [Exact archive/CI/closed-PR ledger](phase0/roadmap/CLOSED_PR_SOURCE_ARCHIVE_AND_V2_INTEGRATION_2026-10-23.md). The original 26-PR audit is a historical snapshot, not current open count. The objective is genuine Exness DEMO-server order execution through the real MT5 API, but the broker order gate is STILL CLOSED; real-money LIVE is separately prohibited.


## Read first — current GitHub state and production objective (2026-10-23)

**Production target:** Send genuine orders using the real MetaTrader 5 Python API to the owner's connected **Exness Pro DEMO broker account** on Windows ForexVPS. They are genuine broker-side DEMO orders, with virtual account funds; **NOT** mocked fills or paper trading. The agent autonomously selects objective XAUUSD TPB BUY/SELL/NO_TRADE, SL and TP under deterministic full Policy A. A later Exness Pro LIVE account at max 0.01 lot is only a separate, explicitly authorized, fully risk-admitted pilot; the desired 24–48h DEMO review never auto-promotes LIVE.

**IMPORTANT: this documentation-only consolidation does not merge any trading code.** The latest engineering resides in DRAFT [PR #38](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/38) on a 7-PR stacked branch rooted in PR #32. Production main still has **no qualified autonomous order sender**. The S2 broker adapter on the draft branch retains its `FULL_POLICY_A_CASH_RISK_RUNTIME_BINDING_NOT_ADMITTED` execution stop. GitHub CI fakes cannot prove actual VPS trading. No DEMO order/VPS deployment has been verified.

**Read in this order for any new chat:**

1. [Open-PR portfolio audit + exact merge/close disposition](phase0/roadmap/OPEN_PR_CONSOLIDATION_AUDIT_2026-10-23.md) and [machine audit](phase0/roadmap/OPEN_PR_CONSOLIDATION_AUDIT_2026-10-23.json).
2. [Real broker DEMO → separately gated tiny LIVE critical path](phase0/roadmap/REAL_BROKER_DEMO_TO_TINY_LIVE_CRITICAL_PATH_2026-10-23.md) and [machine milestone register](phase0/roadmap/REAL_BROKER_DEMO_LIVE_MILESTONES_2026-10-23.json).
3. [Newest reaffirmed owner decision](phase0/decisions/ADR-2026-10-23-002-REAL_BROKER_DEMO_THEN_CONDITIONAL_TINY_LIVE.md), [canonical current human state](phase0/roadmap/CURRENT_PROJECT_STATE.md) and [machine state](phase0/roadmap/CURRENT_PROJECT_STATE_2026-10-18.json).
4. [Full PR38 continuity handoff](phase0/roadmap/NEXT_CHAT_CONTINUITY_HANDOFF_2026-10-23.md) then reconcile **latest live** open PR38 head, files, all stack bases and Actions against accepted `main`; the old embedded HEADs are historical. Inspect the actual code rather than treating documentation as deployed software.
5. [Accepted governance](GOVERNANCE.md), [append-only decision log](phase0/DECISION_LOG.md) and frozen [Phase 0 specification](phase0/PHASE_0_SPECIFICATION.md).

**Governance/merge boundary:** Accepted `GOVERNANCE.md` rule 7 still forbids trading-capable production implementation before Gate 0 completion. Later draft owner decisions accelerate preparation for broker DEMO but do not silently amend this accepted rule. Owner must approve a versioned prospective reconciliation and exact code merges separately; no PR was merged by this audit. The immutable Gate0 failures remain failures. External Python trading stays disabled and LIVE prohibited.

**Historical context:** This document updates the original Phase 0-only README for navigation, not historical claims. A reviewed set of 74 existing branch-origin roadmaps, ADRs and sanitized evidence metadata is staged in this **documentation-only** consolidation; older v1.1/v1.2 and S2 papers are HISTORICAL and not current activation instructions. Their executable source branches remain unmerged. Do not run historical owner scripts without a new verified specific instruction.

**Privacy:** GitHub reports this repository **PUBLIC** despite older descriptions as private. Verify repository visibility before uploading any private broker, VPS, legal, account or credential evidence. Never commit raw secrets.
