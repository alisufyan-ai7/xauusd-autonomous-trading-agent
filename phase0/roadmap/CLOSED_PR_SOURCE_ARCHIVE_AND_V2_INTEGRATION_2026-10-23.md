# 2026-10-23 — Full open-PR retirement and V2 main-based consolidation receipt

**Status: CLOSED historical 26 PRs WITHOUT MERGE; ONE DRAFT SOURCE PR40 OPEN.** This record is staged in [draft PR40](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/40) and is not part of accepted production `main` until explicitly approved and merged.

## Accepted source-of-truth main and exact engineering state

- Accepted documentation-only PR39 previously merged to main `bf6c931fac208ed2b781a2d22734df1124dea1e6`; historic original 26-PR audit is preserved as a time-stamped snapshot at `phase0/roadmap/OPEN_PR_CONSOLIDATION_AUDIT_2026-10-23.md` and `.json`.
- GitHub live API after closure: **exactly 1 OPEN PR, #40**. 26 prior open PRs (#10–26, #28–29, #32–38) now CLOSED UNMERGED with an explanatory source/CI archive link left on EACH closed PR discussion. No branch, account or broker records were deleted; GitHub diff/review comments preserved.
- New main-based branch `integration/real-exness-demo-v2-single-lineage-20261023`, draft PR #40, code/test commit `62248cd6250fde34c7b5989446f2692493cce442` derived directly from accepted main. Diff contains 89 code/workflow/tests/config files imported by exact Git blobs: **77** from cumulative V2 PR32–38 tip `71dfb7869ba691ebe3110451b1fe70987d2531ba`, and **12** selected historical PR28 v1.1 read-only cost/source collector and verification files from `90c3e93330edeee58a0709a41e7393f7818f4ea8`. Old v1.2 read-only preparations and attended canary scripts **not** imported as a second trading system; archived for selective future reuse only.
- Full source tree comparison: every V2 tip path was present in PR40; five intentional changed blobs: `README.md`, `demo_adapter/scripts/v11_quote_coverage.py` (selected PR28 version), `CURRENT_PROJECT_STATE.md`, `CURRENT_PROJECT_STATE_2026-10-18.json`, and `NEXT_CHAT_CONTINUITY_HANDOFF_2026-10-23.md` (main's newer accepted docs). No missing code.
- Historical cumulative ancestry confirmed for all PR10–22 into PR22, all PR23–26 into PR26, and all PR32–38 into PR38 before closing.

## Durable full-source archives

| Historical lineage | Exact immutable archive branch ref (convention: do not move/delete) | Exact tip | Scope |
| --- | --- | --- | --- |
| PR10–22 v1.1/v1.2 | `archive/20261023/pr10-22-v12-readonly-history` | `41a3088a04dd3cef9793148c2a1ed324389d6cd4` | Old read-only cost/session collectors, registrations, tests, failures |
| PR23–26 APC S2 canary | `archive/20261023/pr23-26-s2-attended-canary` | `ab98292dde5c6bda9fc63a85eb36aaac36ed605d` | Historical attended canary, reconciliation, execution-OFF failure |
| PR28 v1.1 read-only host | `archive/20261023/pr28-v11-readonly-source` | `90c3e93330edeee58a0709a41e7393f7818f4ea8` | Selected reusable host/calibration source imported in PR40 |
| PR29 alternative shadow advisory | `archive/20261023/pr29-alt-advisory-ci-fail` | `d90d464528c7e32d28710178f8b3573fc1a10be7` | Failed validation, not chosen TPB champion |
| PR32–38 V2 stack original | `archive/20261023/pr32-38-v2-stacked-original` | `71dfb7869ba691ebe3110451b1fe70987d2531ba` | Full historical V2 source history, original parent stack/CI |

This archive is **versioned Git branch refs** rather than immutable annotated tags. The listed ref names and SHAs were verified at creation. Preserve refs and exact SHA independently; Git branches can be moved by someone with write access. PR closures preserve discussion history and do not confer acceptance.

## Exact native CI of one curated code lineage, PR40 commit 62248cd

- [Release-offline run 39937447739](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447739) SUCCESS; Windows Python3.12 **303 tests PASSED**, Ubuntu **302 PASSED, 1 SKIPPED** (environment-specific), Ruff ALL CHECKS PASS, strict MyPy **19 DEMO sources PASS**, offline package/build and `PASS_STATIC_STOP_PRESENT__FIRST_DEMO_ORDER_NOT_ADMITTED` — no actual order APIs called.
- [DEMO admission run 39937447741](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447741) SUCCESS Windows + Ubuntu.
- [Production candidate run 39937447779](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447779) SUCCESS Windows + Ubuntu.
- [v1.1 source-seal run 39937447795](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447795) SUCCESS.
- [Validate records run 39937447725](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39937447725) SUCCESS.
- These source CI checks were run **before adding this final documentation ledger**. A docs-only PR40 head change triggers another CI run; do not conflate code-tested and docs-tested SHAs.

## What PR40 is, and what it is NOT

PR40 is the **one remaining open, DRAFT** engineering code review. It is main-based and contains one existing S2 MT5 order builder/sender, objective TPB candidate compiler/bridge, source-bound Policy A preflight, known-position and pending-order read-only reconciliation, Event Guard framing and durable watchdog/alert transports, plus v1.1 read-only collector. **It has not been merged into main or deployed to VPS, and its S2 hard trading denial is still present.** No actual Exness DEMO `order_send`, genuine broker fill or automated-trading GUI toggle has been admitted or executed.

The production target is **actual real MT5 Python API broker-side order submission and reconciliation on the attached Exness Pro DEMO server with virtual funds**, never simulated paper fills. Then early 24–48h operational review only. Later 0.01 lot Exness Pro LIVE requires separately accepted live account/risk and explicit owner approval; never an auto-login swap/promotion.

**Next code milestone:** real account/session/news & numerically admitted commission/slippage/gap/swap evidence, full Policy A order-source binding, one source-qualified pending/filled S2 port, live pending-news cancellation, restart/E1/P1, and native VPS release checks. Cannot turn synthetic `ALLOW_MATH_ONLY` into a real broker execution permit. Accepted `GOVERNANCE.md` rule7 still prohibits production trading-capable work until formal prospective reconciliation/approval; owner must resolve this conflict separately before main code merge/trading release. Old Gate0/R4/R34/R35 fails immutable.

**Merge boundary:** No additional merge or closing actions are authorized by this archival receipt. PR40 code merge into main requires separate exact head/main owner approval. If project repo is publicly visible as GitHub API currently reports, avoid committing raw VPS/account evidence/secrets.
