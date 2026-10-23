# Proposed v1.2 Option A safety successor — prospective method, not yet finally owner-approved

**Scope:** Initial restricted `DEMO_LIFECYCLE_ONLY` XAUUSD, Exness MT5 verified demo identity. **Owner authority:** Option A **approved in principle** for separately versioned design/test work with mandatory safety refinements on 2026-10-18. **This proposed v1.2 method is NOT owner-finalized, not a calibration admission and not execution permission.**

## Continuity, immutability and distinct cohorts

Historical v1.0: `DEMO_LIFECYCLE_COST_PREREGISTRATION_2026-10-18.json`, frozen Git blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77`, unchanged; NOT SELECTED for initial DEMO-ADMIT. Frozen v1.1: `DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_1_RESTRICTED_SESSION_2026-10-18.json`, unchanged. Draft PR #12 remains an owner-options *historical decision artifact*. The new `DEMO_LIFECYCLE_COST_PREREGISTRATION_V1_2_OPTION_A_SAFETY_2026-10-18.json` is a distinct prospective **successor** not a retroactive alteration of earlier criteria.

Keep three evidence cohorts **logically separate and independently tagged**:
1. **Four-hour observation:** contiguous 240 complete broker-eligible and independently supported XAUUSD market observation minutes, with 2880 nominal five-second polls, at least 99% complete polls, all 240 1m bins, and the frozen v1.1-T1 true tick sequence / 1s, 5s, 30s 10m pair requirements. The entire 4h need **not** lie within the center overlap; other minutes are *observation-only* and MUST be independently proven broker-eligible/liquid. No presumption from generic center-hour chart.
2. **Current baseline:** **only** the entire actual date-specifically verified non-event, spread-healthy **London–New York overlap subwindow contained inside** the observation, with no guard blackout, shock, wrong clock, stale or adverse unknown. Both endpoints of every baseline tick pair must be inside overlap and clear of events. Disallow importing outside-overlap observations even if they are more favorable. Missing/tainted overlap minute, ten-minute 1/5/30 genuine pairs, or independent source proof => reject the entire proposed baseline as `NOT_ADMITTED`; no after-the-fact shorter "convenient" interval.
3. **Stress:** retain adverse independently proven evidence from **all 240 observation minutes including observation-only minutes**, plus separately sourced relevant stress/event cases with their distinct regime/source hashes and exact attribution. This may include historical authorized event observations where legally/technically admissible; it does **not** authorize new event capture or any event trading. Missing or irreconcilable relevant stress sources require an independent prospectively admitted conservative stress floor or remain `NOT_ADMITTED`. Baseline cannot be inflated or silently contaminated by event/stress records.

## Component math — not broker-calibrated yet

Exact Decimal USD, 0.01 lot equivalent, source-hashed broker-specific tick-size/tick-value-loss and independent conversion verification. Never use spread in the same physical execution leg twice; classify entry ASK/BID and protective-stop USD independently of the additional fee/proxy/allowance reserves. Register an independent non-overlap proof for the chosen accounting decomposition, including how side-specific spreads and stop-price loss interact.

For **each separately defined component**, take the adverse maximum over all admitted **current baseline** observations. This must be reproducible from raw ticks with original sequence, event classifications, and source hashes. Before ANY real capture, fix the source and inclusion/exclusion rules. No percentile tuning, trimming, fabricated zeros or statistical execution guarantees.

- `S_current = max_baseline(verified adverse BUY/SELL spread in USD)`.
- `Q_current = max_baseline(verified adverse 1s, 5s, 30s **quote movement proxy** USD)`.
- `G_current = max_baseline(verified adverse quote gap proxy USD)`.
- `SLIP_current_proxy_floor = max(Q_current, PROSPECTIVE_EXTERNAL_PRE_DEMO_SLIPPAGE_ALLOWANCE_USD)`. The independent external allowance **must be a documented strictly positive, exact-account risk allowance**, preregistered and separately reviewed before any real run. Today its numeric value and source SHA are **NULL**. A numeric floor taken from synthetic fixtures is **NOT admissible**.
- `GAP_current_proxy_floor = max(G_current, independently admitted prospective GAP_ALLOWANCE_USD)` (documented zero only when independently justified).
- `C_current = ceil_cent(S_current + SLIP_current_proxy_floor + GAP_current_proxy_floor + VERIFIED_ROUND_TRIP_COMMISSION_USD + VERIFIED_HOLDING_CONTINGENCY_USD)`.

Both current fees and holding contingency are separately sourced. No unverified waiver, swap assumption or magic zero. Before a numerical C_current is admitted, prove the quote/spread/price-to-stop accounting does not double count and that fee/FX/tick values apply to actual Exness XAUUSD demo account and lot size.

For **stressed**, maximize separate adverse quote/spread/gap components across **the full 240-minute window AND distinct independently sourced relevant event/stress records**, never discarding an adverse observation because it is outside overlap, with nonnegative fee/stress allowances:
- `C_stress_observed = ceil_cent(S_all_stress_max + max(Q_all_stress_max, documented_pre_demo_slippage_floor) + max(G_all_stress_max, documented_gap_floor) + VERIFIED_STRESSED_COMMISSION_USD + VERIFIED_STRESSED_HOLDING_USD)`.
- `stressed_adverse_cost = ceil_cent(max(2 * C_current, C_stress_observed))`, with current and stressed components from explicit independent evidence rather than assumed event-free outcomes.
- Frozen `Policy A` remains the separate stop-loss-to-protective-SL risk calculation: `L_plan = L_price + evidenced commission + swap + slippage_allowance + gap_allowance`. `C_current/C_stress` alone cannot approve broker orders; comprehensive live per-order cash loss, free-margin and source reconciliation must still pass.

**Critical terminology:** Q/G observations are *adverse quote-movement proxies*, NOT measured order execution slippage, executed gap/stop fill risk or statistical tail bounds. An observed four-hour maximum (or its 2x stress) is NOT a proof that the next fill loss is limited. The pre-demo slippage value must be titled **CONSERVATIVE QUOTE-PROXY-BASED RESERVE / FLOOR**, never `MEASURED_EXECUTION_SLIPPAGE`. If independent evidence cannot support a conservative reserve against unknown execution tail risk, DO NOT ADMIT. Actual per-order submitted vs filled entry and stop-exit execution slippage must be measured, journaled and independently reviewed **only after a separately authorized, attended bounded DEMO lifecycle**.

The pure offline rehearsal `demo_adapter/scripts/v12_option_a_cost_recipe.py` uses fake externally converted USD and fake 64-character hash-pins only as **synthetic fixtures**. This cannot attest true broker source origin or admissible fees, or authorize a calibration; `C_current/C_stress` returned are not production constants.

## Pre-session-end FLAT requirement — stricter than v1.1

No initial DEMO-ADMIT position may carry beyond the **earlier of the independently verified eligible London–NY entry overlap end or the date-specific XAUUSD broker session end**. Strictly BEFORE that limit, the real broker and reconciled immutable journal must confirm **zero known/owned open positions and zero pending orders**, attributed fills/closures and no unknown exposure. This explicitly forbids all rollover, weekly reopen and overnight holding in initial admission. No assumption that a broker's protective SL/TP executes exactly or automatically empties positions. Externally disabled Python execution stays disabled until independently approved after all gates.

Prospectively preregister, with independent runtime/human operator acceptance, the strictly **positive** flat-verification lead time, maximum intended trade holding time, and bounded human-exit plus broker-reconciliation reserve. Entry is not even eligible when `now + maximum_holding + exit_reconciliation >= hard_flat_confirmation_deadline`. Prove there is enough time for entry and attended exit before accepting an operation. All needed actual quantitative bounds remain **UNVALIDATED/NULL** pending distinct owner review; any "5-minute lead/10-minute hold" in synthetic tests is only an invented test input, not an operational permit or deployment setting.

The local pure rehearsal `v12_option_a_flat_lifecycle.py` accepts simulated known exposure and "owner attended" signals solely to test fail-closed math. An actual end-to-end runtime bridge must establish those statements from independent owner/broker authority. If a position cannot be flattened within the verified buffer or becomes unknown, **QUARANTINE + block new entries + alert and human-only E1 emergency**. **Do not close or modify unknown exposure automatically**; E1/P1 owner gates unchanged. If an emergency event occurs close to the boundary, cannot claim safe flatness. No initial demo trades until an owner-attended planned-exit drill, pre/post zero-exposure reconciliation and deterministic stop/freeze/tick checks pass.

## Exact UTC source registration — remains deliberately unfilled

The public Exness center-hour summer and winter table is insufficient for date-specific XAUUSD symbol execution/capture eligibility. Before selecting a single real UTC 4h interval, version and independently hash:
- current official Exness **XAUUSD instrument** trading/quote-only/maintenance hours, latest holiday closures/reopening and applicable date's London/New York DST offsets;
- official BLS, BEA, Federal Reserve, Census, DOL high-impact event releases, their verified UTC times, Event Guard health/state/blackout/unscheduled health, broker local state and clock-skew bounds;
- owner-reviewed frozen v1.1-T1 tick source/millisecond sequence matching, collector and Windows host code SHA256, independent source/manifest verifier and approved private output path;
- instrument trade-currency/tick-loss/commission/swap/FX proof, qualified identical broker-account identity, evidence-scoped start/end registration committed BEFORE capture.

Do NOT treat `12:30–16:30 UTC` as an actual run, or assume that an hour merely falling in London implies acceptable liquidity. No exact start/end, event schedule hash, instrument proof, numeric quote-to-USD cost or run owner approval exists. Failed attempts remain immutable, without retrospective re-registration.

## Authorization and gate

**Completed here:** owner in-principle selection faithfully recorded; prospective successor and synthetic code/test *preparation* only. **Pending separate owner decision:** approve final exact-head successor version; after that, separate exact code/date/source registration; still separate permission for any VPS/broker read-only activity. **Forbidden now:** merge PR #12 or successor, any VPS access, real MT5 data, EA action, MT5 setting change, enabling external Python trading, demo orders, live or tiny-live actions.

Frozen 0.25% capital-scaled USD per-order stop-risk, concurrent USD50/day USD75/week USD150/drawdown USD500, 3R pause, V1 0.01 lot, M1 >=1000% margin current & 2x stress and >=90% free margin/equity, no unknown exposure close, immutable prior fails, E1/P1 and durable kill/QUARANTINE all remain unwaived. The hard demo submission veto from PR #9 is untouched.

**Review status:** `PROSPECTIVE_SUCCESSOR_DRAFT_REQUIRES_OWNER_FINAL_APPROVAL`; `current_adverse_cost=null`; `stressed_adverse_cost=null`; `DEMO_ADMIT=BLOCKED`.
