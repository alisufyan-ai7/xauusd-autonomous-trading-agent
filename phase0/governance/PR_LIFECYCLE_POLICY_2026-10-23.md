# PR lifecycle and consolidated-feature rule — 2026-10-23

**Status:** prospective engineering-process policy in draft PR #40, requiring explicit owner acceptance before treated as an amendment to accepted `GOVERNANCE.md`. Applies immediately as a *working discipline* for new draft work; it does not authorize trading or merges.

## Objective: keep only useful, reviewable PRs open

- Default: **one coherent feature / one PR**, with a single clearly testable acceptance contract. A multi-component release slice may be one PR only when components share a single safety invariant and their native CI/test integration is reviewed together.
- **Continue development in the existing feature PR and branch.** Fix failures and update tests/docs there, rather than making a correction PR stacked on an unmerged correction PR. Do not open a new PR for a small fix, status document or handoff update to an unmerged feature.
- **PRs should normally target accepted `main`**; avoid chains where every PR targets the previous unmerged PR. If stacked reviews are unavoidable, explicitly mark the dependency graph, coordinate ordered merges/rebases and prune the stack promptly after acceptance. A successor PR does not bypass parent failed checks.
- **New PR required** when the code change has independent ownership, review, security posture or release gates; can be tested/merged independently; or substantially changes accepted functionality. Do not over-aggregate unrelated product capabilities merely to reduce PR count.
- **Review hygiene:** one current read-first roadmap; a short PR description identifying exact code scope, status, frozen risk and order-execution safety; direct links to the authoritative state and precise native CI. Update existing human/JSON state + handoff as milestones genuinely change; don't create multiple competing "latest" documents.
- **No automatic merging**: verify exact HEAD SHA, current `main` SHA, changed file allowlist, native Windows+Ubuntu test results, recorded faults and owner-specific approval. For trading-capable code also require account-authoritative evidence, accepted governance, broker order lifecycle safety, Event Guard and recovery. CI fake-MT5 "PASS" never means real broker acceptance.
- **Supersede/close after preservation:** first ensure no code or durable evidence is lost and attach an exact Git archive SHA, owner decision, failed-incident provenance and successor link. Close unmerged, do not erase or relabel failures, do not delete archive refs. At most one active PR per independent feature; routine weekly audit of open PRs before adding a new one. Archive branches are conventional refs and are mutable unless protected.
- **Preserve older accepted main governance:** rule 7 currently limits trading-capable work before Gate 0 closes, notwithstanding later owner-in-principle accelerated broker-DEMO intent. Prospective reconciliation needs a separate exact approval and must distinguish software engineering from risk-capital admission. No general exception for real-money LIVE.
- **One product target:** genuine Exness Pro MT5 DEMO broker-side XAUUSD orders (virtual account cash), deterministic TPB and full frozen Policy A; later max 0.01-lot LIVE only with separate account/risk evidence and new explicit owner authorization. Do not conflate simulated orders, broker DEMO order execution and real-money capital.
- **Current status:** prior 26 PRs #10–29 and #32–38 closed UNMERGED after source preservation; one OPEN draft main-based PR40 `integration/real-exness-demo-v2-single-lineage-20261023`. Consolidated all cumulative V2 code and the selected v1.1 read-only cost source. No actual Exness DEMO orders or VPS actions; S2 hard block still exists.

## Future owner-checkable PR acceptance checklist

1. PR explains ONE explicit outcome, dependencies, changed components and scope exclusions.
2. Branch based on `main`; no orphaned stacked review without documented compelling reason.
3. Native CI green at exact current HEAD, with failure investigation preserved.
4. Any impacted owner decisions, human state, JSON state and next-chat handoff updated *without* contradictory current claims.
5. For broker-trading changes: source-account fingerprint, all-cost money, official event/session coverage, single durable order sender, known positions and no-retry unknown outcome, remote recovery, alerts, and E1/P1 must pass; no LIVE auto-promotion.
6. Exact-commit approval before merge; close superseded PR promptly with archive locator.
