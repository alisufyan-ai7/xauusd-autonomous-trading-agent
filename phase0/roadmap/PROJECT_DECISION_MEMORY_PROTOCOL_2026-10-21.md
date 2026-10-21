# Project decision and cross-chat memory protocol

**Date:** 2026-10-21. **Decision:** owner requires GitHub-persisted, reviewable decision history for all material product, research, strategy, risk, operating and deployment planning. **No automatic broker/trading authority implied.**

## 1. What counts as a decision

Persist in the **private GitHub repo** whenever any of these materially changes: owner objective/account type/balance assumptions; strategy selection or variant; market-data/news provider or legal/retention scope; AI model/prompt/runtime transport or learning/promotion method; risk numbers or overrides; position-management rules; tests and acceptance windows; broker/VPS controls; build/deployment/recovery; adverse outcomes and root-cause investigations; authorizations and revocations; roadmap priorities or blockers.

Record **what, when (UTC), who/authority, status, why, evidence/source, impact, acceptance criteria, follow-up, linked PR/commit/file**. Do not turn a brainstormed human example into an owner-approved trading rule. Distinguish:

- **OWNER-ACCEPTED PRODUCT REQUIREMENT**: product design direction explicitly decided by owner; still not software/testing/trading approval.
- **ASSISTANT-PROPOSED**: recommendation pending explicit owner selection.
- **RESEARCH/HYPOTHESIS**: unverified or experimental idea; no profitability claim.
- **APPROVED TO PREPARE / TEST / DEPLOY**: exact named scope, hash/release and safety preconditions only.
- **OBSERVED PASS / FAIL_CLOSED**: immutable owner-provided or tool-produced evidence with date/context, actual output pointers and hashes; PASS never implied by source-only review.
- **APPROVED TO TRADE DEMO / LIVE**: a **separate** granular broker/account/release/window risk authorization, never inferred from a roadmap or owner aspiration.
- **SUPERSEDED / REJECTED**: preserved historical record; new ADR explicitly cites previous ID rather than modifying it.

## 2. Canonical hierarchy and branch handling

1. `main` is the authoritative **accepted** project baseline (`GOVERNANCE.md`); GitHub drafts and unmerged evidence branches are **prospective** only and never silently called merged/accepted.
2. Decision chronology remains append-only. Original `phase0/DECISION_LOG.md` D-series is preserved. Because historic D-series references also appear in other Gate 0 files, use unique **`ADR-YYYY-MM-DD-NNN`** addenda for modern cross-chat decisions rather than allocating a conflicting D number. Index each new ADR in the decision log. Never renumber historical IDs.
3. For new accepted owner requirements or planning changes, create a docs-only branch and reviewable PR from current `main`, containing a dated ADR, an index pointer and a minimal read-first `CURRENT_PROJECT_STATE.md` note. **Do not merge or deploy without separately explicit approval.** When approved and merged, new chat checks `main` and PR/commit history.
4. If owner-dependent evidence arrives while another long-running evidence branch is unmerged, append only a pointer/status to both `phase0/roadmap/CURRENT_PROJECT_STATE.md` and `phase0/roadmap/CURRENT_PROJECT_STATE_2026-10-18.json` on that evidence branch, cross-linking the dedicated ADR/PR. Do not bring the entire 100+ commit experimental/evidence branch into a documentation PR by accident.
5. Both latest human-readable and machine-readable state must carry an **active-task pointer**, exact reconciled authoritative `main` SHA, relevant draft PR heads, current blockers, and explicit authorization flags. Old state is retained as historical notes, but the freshest read-first header/snapshot says what is current.
6. Record revisions as a new ADR and mark the prior one `superseded_by` through a *new* addendum, not history rewrite. For failures/repeated owner runs, preserve separate original attempts, observed stdout markers/hashes, effect and actual stage reached; never fabricate CI/VPS PASS.
7. The owner has given **general permission to record decisions and plans** in GitHub. This is NOT permission to merge PRs, alter trading runtime, turn on external Python trading, change accounts, run orders, deploy VPS tasks, contact providers, fund LIVE, send OpenAI production calls, or make high-risk broker changes.

## 3. Secret-minimization rule

No raw MT5 account/login number, password, investor password, API token, prompt secret, account screenshot with identifiers, live order identifier or private key goes to GitHub, PR comments, stdout summaries or chat. Store only purpose-limited account SHA256 fingerprint, company/server/currency/DEMO status and sanitized/hardened hashes with private original evidence remaining off-repository. No personal identity docs.

## 4. Required handoff checklist for any fresh ChatGPT chat

Read in order: `GOVERNANCE.md` → `phase0/DECISION_LOG.md` plus current ADR index → `phase0/roadmap/CURRENT_PROJECT_STATE.md` and paired `CURRENT_PROJECT_STATE_2026-10-18.json` → latest ADR(s) and relevant open PR(s) → latest owner VPS evidence/incident register. Reconcile `main` and draft heads via live GitHub; distinguish source-only plans from actual broker evidence and trading authority. Never use the chat conversation as the only durable decision log. Consult relevant frozen Phase0 strategy/risk/event specs before proposing policy changes.

## 5. Execution and learning governance

Production AI output is non-authoritative. All automatic trade actions need a separately admitted Exness **Pro** mode-bound release and deterministic Risk Governor. Learning and AI-generated new strategy/prompt/risk variants are versioned challengers until validated and separately promoted. No AI self-modifying deployed LIVE strategy/risk; no stop widening or loss-chasing by model fiat. The owner can request an alternative policy, but its limits and risks must be specified and approved prospectively.

**Current October-21 decision set:** [ADR-2026-10-21-001](../decisions/ADR-2026-10-21-001-AUTONOMOUS-PRO-TRADING-VISION.md).
