# v1.2 Option A owner-final design review handoff — PROSPECTIVE ONLY (2026-10-18)

**Current disposition:** `OWNER_OPTION_A_IN_PRINCIPLE_ACCEPTED`; `V1_2_SUCCESSOR_OWNER_FINAL_APPROVAL_PENDING`; `CALIBRATION_NOT_ADMITTED`; `DEMO_RUNTIME_SUBMISSION_HARD_VETO`.

## Source-of-truth and order of operations

The owner explicitly instructed a GitHub reconciliation and immediate `CURRENT_PROJECT_STATE.md` and `CURRENT_PROJECT_STATE_2026-10-18.json` update **before any further engineering edits**. This was done on a new child branch of unmerged PR #12. Reconciled main: `ccaa8338aecee8bd3afbc358644410dff6c512e5`. PR #8 `8c3b83ba5edf83a8d4e5cc18096070fadf5c52e9`; #9 `6e5f32b771d511c670bbb348f0dd0fb427412fd5`; #10 `81ee6286fd2a3da528bed5c397ed816a103c1566`; #11 `5da628e9410c08467009cff1a8cdfe4440f0f414`; #12 `b03e1ba3ee2434744010ac8bdf37904ba19df730` (all DRAFT UNMERGED).

After recording the decision, this branch added **new, separately versioned v1.2 successor**:
- `phase0/roadmap/DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_2_OPTION_A_SAFETY_2026-10-18.json`
- `phase0/roadmap/DEMO_LIFECYCLE_COST_METHOD_V1_2_OPTION_A_SAFETY_2026-10-18.md`
- `phase0/roadmap/DEMO_V12_OPTION_A_RUN_WINDOW_TEMPLATE_UNREGISTERED_2026-10-18.json`
- `demo_adapter/scripts/v12_option_a_cost_recipe.py` and `tests/test_v12_option_a_cost_recipe.py`
- `demo_adapter/scripts/v12_option_a_flat_lifecycle.py` and `tests/test_v12_option_a_flat_lifecycle.py`
- `demo_adapter/tests/test_v12_option_a_preregistration.py` and expanded PS5.1 offline SHA/test reviewer

**Frozen v1.0/v1.1 registrations are NOT changed.** Original v1.0 Git blob remains `3e6e0d19e70da5a02002615160e3f0c0a0367b77`; not selected initial demo. The PR #12 option-review file remains its original historical `selected_option=null` snapshot (before owner in-principle approval); the new owner decision is recorded in `CURRENT_PROJECT_STATE` and prospective v1.2 files instead.

## Owner refinements applied prospectively

1. **240 contiguous minutes of date-specifically broker-eligible liquid XAUUSD *observation***, even when only a shorter independently verified London–NY overlap lies inside; no demo entries outside **the verified, event-free overlap**. The illustrative `12:30–16:30 UTC` is **not selected/qualified**. Actual Exness XAUUSD sessions, DST, holiday and Event Guard must be independently sourced and SHA-verified BEFORE any exact UTC window can be chosen; run template contains null real times/source IDs/approval.
2. **Current** `C_current`: only verified non-event entry-eligible overlap evidence; strict 1m and genuine source tick-horizon checks and original source sequence. Unknown overlap minute or source proof => `NOT_ADMITTED`. Cannot take convenient lower-risk non-overlap sub-window for baseline.
3. **Stressed** `C_stress`: adverse source evidence spanning the entire four-hour observation **plus distinct relevant event/stress proof** with preserved source/regime tags. Use max(2x current, independently sourced conservative stressed component sum); absence of independent stress evidence => no stress admission. Event-type source proofs do **not** authorize event capture/trading and may be sourced only from separately authorized historical/source evidence.
4. **Pre-demo slippage allowance** is a `CONSERVATIVE QUOTE_PROXY_BASED_USD_FLOOR` with a strictly positive separately pinned external basis, NOT measured execution slippage or a stop-fill tail guarantee. All real USD values/fee/FX/stress and proof hashes are deliberately `null` in registration. Synthetic fixture numbers are demonstrative and **must never** be copied as real calibrated costs. Actual entry+stop-exit execution slippage is a **different later lifecycle measurement** subject to owner demo approval.
5. **Flat BEFORE the earlier of overlap entry/session end and broker session end:** owner-attended planned exit, maximum planned holding and strictly positive early flat/ledger reconciliation buffer preregistered prospectively; broker zero open owned positions AND zero pending orders confirmed with independently verified identity/time/immutable cashflow. Missing or late proof => `QUARANTINE`, alert and human-only E1 emergency; never automatically close unknown positions. Rollover/overnight/weekend holdings forbidden until a separate prospective successor is approved.
6. **Full frozen Policy A remains mandatory** for all future order decisions, including cap of 0.01 lot, monetary stop loss and 0.25% capital-scaled cap, USD50 concurrent, USD75 daily, USD150 weekly, USD500 drawdown, 3R pause, 1000% M1 current/doubled incremental margin and free-margin >=90% equity, E1 and P1, durable control and reconciliation. Existing PR #9 `mt5_demo.py` **HARD QUARANTINE before order_check/order_send** remains intact. No math-only synthetic result is an activation permit.

## Independent tests: scope and limitations

The two new pure offline math modules do **not** import MetaTrader5, connect to broker, read VPS, schedule tasks, close a position, create any trading permit or modify demo adapter submission. Tests exercise independent synthetic spread/shock cohort separation, broader stress and explicit 2x floor, proof missing, nonfinite currency values, baseline tick pair gaps, quote slippage NOT measured, deterministic positive flat/exit buffers, earlier broker session end, late or unknown exposures and human-only quarantine.

**Tests can validate only logic over synthetic, caller-pinned inputs.** Reconciliation of real MT5 broker identities, tick conversions, fee proofs, trade cashflow attribution, valid Event Guard and official Exness instrument sessions has **not** been done and cannot be claimed from passing tests. A caller's `sha256` digest is byte integrity, not independent source authenticity. Actual entry/exit slippage and real stop-fill tail costs unmeasured. No numerical calibration admission.

## Exact next genuine owner boundary

After reviewing the exact GitHub PR head and independent CI logs, present **approval of the separately versioned v1.2 method only** (not source acquisition) as a new owner decision. Do not select an exact UTC window, merge any PR, use VPS or MT5, change external Python trading permissions, capture broker data, stage demo operations or place orders. Separate approvals remain necessary for all those actions. Prior Gate failures and PCR3 remain immutable.


## Owner-requested metadata reconciliation — final-design approval still pending (2026-10-18)

**Strict metadata-only correction, no method change:** Prior PR #13 HEAD `1f55d0b3b50fa6448c80b08dbcd518b0446bd64b` was reconciled against current GitHub. `main` remains `ccaa8338aecee8bd3afbc358644410dff6c512e5`; PR #11 actual `5da628e9410c08467009cff1a8cdfe4440f0f414`; PR #12 actual `b03e1ba3ee2434744010ac8bdf37904ba19df730`. PR #8–#13 remain DRAFT UNMERGED. The sole **source correction file** is `phase0/roadmap/CURRENT_PROJECT_STATE_2026-10-18.json`, corrected in commit `546008eb49670276f9202a1cd2f173284d2327cc`. The PR #11 dependency head and PR #12 `head_sha` now match GitHub.

**Unambiguous authorization:** `option_a_in_principle_approved=true`, **`v1_2_successor_final_design_approved=false`**; `merge_authority=false`, `capture_authority=false`, `vps_authority=false`, `demo_trading_authority=false`, `live_trading_authority=false` in the machine state, mirrored in the owner decision metadata. The old `owner_option_adopted=false` was removed as it conflated in-principle scope with final successor/design authority. Historical PR #12 option-review records remain historical; no reclassification or retroactive amendment.

**Validation of exact metadata-correction commit** `546008eb49670276f9202a1cd2f173284d2327cc`:
- [GitHub records workflow #39129219630](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39129219630): **SUCCESS**.
- [GitHub demo-admit offline workflow #39129219623](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/actions/runs/39129219623): **SUCCESS**: Windows Python 3.12 **158 passed**; Ubuntu Python 3.12 **157 passed, 1 Windows-only parser test skipped**. This runs the affected offline suite as well as general offline checks.
- An additional **final exact-head run** occurs when this review-handoff metadata is committed. The authoritative final HEAD and validation links are recorded in [the PR #13 description](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/13) and its immutable final review comment after that run. This file cannot embed its own commit hash; do not misinterpret the correction-commit SHA as the final HEAD.

**Integrity:** The v1.0 preregistration Git blob is still `3e6e0d19e70da5a02002615160e3f0c0a0367b77`, v1.1 preregistration Git blob `5210056f0a07faad9225e24228392f43090c5561`. The v1.2 prospective substantive method, JSON preregistration, run-window template, implementation and tests are unchanged. No order-submission veto, Policy A, E1/P1, risk gate, calendar rule, capture condition or authorizing control was modified. **STOP at the final v1.2 successor DESIGN-ONLY owner approval boundary.** No merges, VPS access, MT5 actions, broker capture or demo/live trading were performed.
