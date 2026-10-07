# Deterministic Risk Governor Mathematics — Policy A

**Document status:** Policy constants, V1/M1 controls and core mathematics frozen; enumerated evidence dependencies remain open  
**Scope:** Mathematics and test vectors only; no order submission or trading implementation  
**Policy authority:** D-0045 and D-0075 / owner-approved Policy A plus V1/M1  
**Authorization:** Gate 0 incomplete; external Python trading remains disabled

## 1. Safety invariants

1. All money calculations use exact decimal arithmetic in account currency (USD), never binary floating point.
2. Broker volume, price, tick-value and margin values are read from the current verified account/symbol snapshot; they are not hardcoded.
3. Missing, stale, contradictory, non-finite or unowned state produces `REJECT` or `QUARANTINE`, never a risk-increasing action.
4. Limits are upper bounds. Model confidence cannot increase them.
5. A proposed order is admissible only when every resulting exposure remains **less than or equal to** every applicable limit. If an existing limit is reached or breached, no new risk is allowed.
6. A broker fill worse than planned does not retroactively make an order compliant. It creates a breach, blocks new risk, and requires reconciliation/alerting under the execution specification.
7. Unknown positions/orders cause quarantine of all new risk. They are neither adopted nor automatically closed.

## 2. Constants and controlled inputs

| Symbol | Definition | Policy A value |
|---|---|---:|
| `A` | approved strategy allocation | USD 10,000 |
| `r` | maximum risk fraction per new trade | 0.0025 |
| `C` | maximum concurrent planned risk | USD 50 |
| `D` | daily adjusted-equity loss ceiling | USD 75 |
| `W` | weekly adjusted-equity loss ceiling | USD 150 |
| `M` | total strategy drawdown ceiling | `min(USD 500, 0.05 × A)` = USD 500 |
| `Q` | full-risk-equivalent loss pause threshold | 3.00 |

Controlled runtime inputs include current balance `B(t)`, current equity `E(t)`, verified cash-flow ledger, strategy inception baseline, daily/weekly boundary snapshots, owned open positions, owned pending orders, current symbol specifications, prices, spread, costs, and conservative slippage/gap allowances. Time boundaries use one frozen project timezone (recommended UTC); changing it requires a controlled specification decision.

The seven Policy A constants above are owner-approved and normative. They may not be changed by configuration, a model response, or an implementation default. Runtime inputs and their provenance are not policy constants. Until each open methodology in section 12 is frozen, a value dependent on that methodology is `UNKNOWN` and new risk is rejected; an implementation must not substitute zero.

Owner-approved operational risk constants under D-0075 are:

| Symbol | Definition | Value |
|---|---|---:|
| `V_cap` | absolute strategy volume cap | `0.01 lot` |
| `ML_min` | minimum projected margin level, current and stressed | `1,000%` |
| `FM_min` | minimum projected free margin / projected equity, current and stressed | `90%` |
| `k_margin` | incremental-margin stress multiplier | `2.0x` |

## 3. Per-trade risk cap

Applicable capital:

`K(t) = min(B(t), E(t), A)`

Maximum planned loss for a newly proposed independent trade:

`R_trade_max(t) = round_down_cent(r × K(t))`

Examples: `K=10,000 -> 25.00`; `K=9,000 -> 22.50`; `K=8,000 -> 20.00`; `B=E=15,000` while `A=10,000 -> 25.00`.

Risk scales downward automatically. It never scales upward beyond `A` without a new owner decision.

`B(t)` and `E(t)` must be same-snapshot, broker-reconciled USD decimals. If either is missing, stale, non-positive, in another currency without a frozen conversion rule, or inconsistent with the reconciled account state, no positive cap exists and the result is fail-closed. Cent rounding is toward zero for a non-negative cap (equivalently floor to USD 0.01).

## 4. Planned loss and deterministic sizing

For a candidate volume `v`, define conservative loss-to-protective-stop in USD:

`L_plan(v) = L_price(v) + Commission(v) + Swap_buffer(v) + Slippage_buffer(v) + Gap_buffer(v)`

`L_price(v)` must be calculated using the broker-reported tick size/value or an independently verified order-profit calculation for the exact symbol, side, entry, stop and volume. The calculation must remain valid when tick value differs by profit/loss direction. Every price and volume is normalized conservatively to broker increments; rounding may not increase allowed risk.

All five components are non-negative. A missing or unverified component is not treated as zero. Entry uses the worst executable price allowed by the still-open execution/slippage specification; stop uses the adverse broker-normalized stop. For a range entry, sizing uses the worst loss-producing admissible entry. The method must demonstrate monotonic non-decreasing `L_plan(v)` over the broker volume grid; otherwise sizing fails closed.

Deterministic volume:

`v* = max { v in broker_volume_grid : v <= strategy_volume_cap and L_plan(v) <= R_trade_max }`

If the set is empty, return `REJECT_RISK_BELOW_MIN_VOLUME`. Model-proposed volume is ignored as authority; at most it may be logged as non-authoritative input.

Under V1, `strategy_volume_cap = min(0.01 lot, account_validated_cap)` and never defaults to broker maximum. Grid enumeration starts at the current broker `volume_min`, advances by exact `volume_step`, and never rounds upward. If the broker minimum exceeds the cap, 0.01 lot is invalid, or no grid volume passes every other limit, reject. The selected result must be re-priced and re-tested after normalization rather than inferred solely by division.

An order without a valid protective stop, or whose stop cannot be accepted under current stop/freeze rules, is rejected. No martingale, grid/recovery expansion, failed-trade averaging, or confidence override is permitted.

## 5. Concurrent planned risk

For each owned live position or pending entry `i`, calculate its current conservative committed loss `L_commit_i` to its broker-confirmed protective stop, including remaining costs and buffers. Pending orders count as if fully filled. OCO siblings count conservatively as all fillable unless broker-confirmed atomic cancellation makes simultaneous fill impossible. Partial fills use filled risk plus unfilled pending risk.

Also calculate `L_increment_i`, the non-negative additional adjusted-equity loss from the current reconciled mark/equity to that stop/fill outcome. This is distinct from trade-level committed/planned risk: loss already reflected in current equity must not be counted again in prospective period-loss tests.

`L_concurrent_before = sum_i max(0, L_commit_i)`

Admission requires:

`L_concurrent_before + L_plan(candidate) <= C`

Confirmed stop movement may reduce `L_commit_i`; unconfirmed requested modifications do not. Profits on other positions do not offset planned loss. Unknown/unowned exposure prevents calculation and produces `QUARANTINE_UNKNOWN_EXPOSURE`.

### 5.1 M1 projected margin reserve

Let `E_cur` be projected equity after the candidate under the current
calculation, `U_before` the reconciled used margin before the candidate, and
`DeltaM` the broker-calculated incremental margin for the candidate. Define:

- `U_cur = U_before + DeltaM`
- `F_cur = E_cur - U_cur`
- `E_stress = E_cur - (S_spread + S_slippage + S_gap + S_cost)`
- `U_stress = U_before + 2.0 * DeltaM`
- `F_stress = E_stress - U_stress`

For each state `x` in `{cur, stress}`, require both
`E_x / U_x * 100 >= 1000%` when `U_x > 0`, and
`F_x >= 0.90 * E_x`. When `U_x = 0`, the margin-level ratio is not a blocker,
but the free-margin rule still applies. Non-positive projected equity; negative
margin/stress; missing, stale, non-finite, currency-ambiguous or
fingerprint-inconsistent inputs; or a failed broker margin calculation produce
`UNKNOWN` and reject new risk.

The larger conservative used-margin result and the smaller conservative
free-margin result control if broker and local projections differ. M1 is a
necessary gate only. It cannot relax or override per-trade, concurrent, daily,
weekly, drawdown, pause, ownership, volume, session, event, cost or execution
limits, and an M1 pass never authorizes a trade.

## 6. Cash-flow-normalized adjusted strategy equity

Let `F(t0,t)` be the exact signed sum of external cash flows posted after baseline time `t0` and through `t`: deposits/transfers in are positive; withdrawals/transfers out are negative. Trading P/L, commission, swap and trading charges are not external cash flows.

Adjusted strategy equity relative to a period baseline is:

`AE(t | t0) = E(t) - F(t0,t)`

Period loss is:

`Loss(t | t0) = max(0, E(t0) - AE(t | t0))`

Therefore:

- `L_day(t) = Loss(t | start_of_current_trading_day)`
- `L_week(t) = Loss(t | start_of_current_trading_week)`

The baseline equity includes any open P/L at the boundary. Subsequent realized P/L, unrealized P/L, commission and swap are reconciliation components of the equity change and are **not added again**. An unclassified balance operation, missing cash-flow history, boundary gap or reconciliation mismatch fails closed.

The interval convention is `(t0,t]`: the reconciled boundary snapshot already contains all postings through `t0`, and only later-posted external flows enter `F`. Corrections/reversals retain their signed ledger effect and immutable linkage. A cash-flow event whose effective time straddles an unavailable boundary is unresolved rather than guessed. Day/week rollover requires a reconciled boundary snapshot; a restart may replay the journal but may not synthesize a favorable baseline from the first post-restart observation.

A candidate is admissible only if, with `L_future = sum_i(L_increment_i) + L_plan(candidate)`:

- `L_day(t) < D` and `L_day(t) + L_future <= D`; and
- `L_week(t) < W` and `L_week(t) + L_future <= W`.

This prospective test reserves both the additional loss-to-stop on existing exposure and the candidate’s planned loss. It does not double-count existing unrealized loss, which is already reflected in current equity.

## 7. Total strategy drawdown

Maintain a cash-flow-normalized continuous equity index from strategy inception:

`NE(t) = E(t) - F(inception,t)`

`H(t) = max(NE(s))` over all reconciled observations `s` from inception through `t`.

`DD(t) = max(0, H(t) - NE(t))`

New risk requires `DD(t) < M` and `DD(t) + L_future <= M`. The high-water mark is not increased by deposits and is not decreased by withdrawals. A breach blocks new risk; it does not itself authorize closing positions.

`H(t)` advances only on a reconciled observation. Missing intervals, ledger discontinuity or an inability to reconstruct inception-normalized equity makes drawdown state `UNKNOWN` and blocks new risk. A withdrawal cannot erase a prior drawdown, and a deposit cannot manufacture recovery.

## 8. Full-risk-equivalent loss pause

Each independently completed trade/setup instance `j` stores its immutable admission risk budget `Rj > 0` and final net trading P/L `Pj`, including commission and swap. Sequential pullback zones are independent instances; Zone B can exist only after fresh analysis and never as recovery for Zone A.

An instance is complete only when every linked fill, partial close, commission, swap and residual position/order is reconciled. Multi-leg/partial-exit attribution and the treatment of later broker adjustments must be frozen before this pause can be implemented; until then an ambiguous completion blocks new risk rather than prematurely resetting the streak.

Loss equivalent:

`qj = max(0, -Pj) / Rj`

Maintain `Q_streak` for completed instances since the most recent instance with `Pj > 0`:

- losing instance: `Q_streak := Q_streak + qj`;
- exactly flat instance: no change;
- profitable instance: `Q_streak := 0`.

When `Q_streak >= 3.00`, enter `PAUSED_FULL_RISK_EQUIVALENTS`. No new risk is allowed. Automatic time-based resumption is prohibited in Phase 0; resumption requires the later operational policy and reconciled operator action. Daily, weekly and drawdown controls remain independently authoritative.

## 9. Decision order and result

The Governor evaluates: authorization/kill switch → ownership/reconciliation → freshness → session/news/spread state → proposal semantics → symbol/order constraints → V1/per-trade sizing → concurrent risk → daily loss → weekly loss → drawdown → loss-equivalent pause → M1 margin reserve → execution preconditions. All must pass the same immutable snapshot. Any state change before submission requires re-evaluation.

The output is a typed decision (`APPROVE_SIZED_PROPOSAL`, `REJECT`, or `QUARANTINE`) with reason codes, input snapshot hash, policy version, formula version, computed values and audit timestamp. Approval is not an order and cannot directly call MT5.

## 10. Normative test vectors

Unless specified, USD values are exact, state is fresh/reconciled, no news/session/spread block exists, and current concurrent risk/loss/drawdown are zero.

| ID | Inputs | Expected result |
|---|---|---|
| RG-001 | `B=10,000; E=10,000` | `K=10,000; R_trade_max=25.00` |
| RG-002 | `B=9,000; E=9,400` | `K=9,000; R_trade_max=22.50` |
| RG-003 | `B=9,500; E=8,000` | `K=8,000; R_trade_max=20.00` |
| RG-004 | `B=15,000; E=15,500; A=10,000` | `R_trade_max=25.00`; no upward scaling |
| RG-005 | raw cap `20.009` | cent-round-down gives `20.00` |
| RG-006 | min volume planned loss `25.01`, cap `25.00` | reject below minimum volume |
| RG-007 | candidate at allowed grid has price loss `22`, commission `1`, swap buffer `0.50`, slippage `1`, gap `0.50` | total `25.00`; per-trade pass |
| RG-008 | same but total `25.01` | reject per-trade risk |
| RG-009 | model proposes `0.50 lot`; deterministic maximum grid volume `0.02 lot` | output may size only `0.02`; model cannot override |
| RG-010 | no valid stop | reject |
| RG-011 | existing committed risk `25`; candidate `25` | concurrent total `50`; pass boundary |
| RG-012 | existing committed risk `25.01`; candidate `25` | concurrent `50.01`; reject |
| RG-013 | pending OCO risks `20` and `20`, no atomic-fill guarantee; candidate `11` | count `40`; total `51`; reject |
| RG-014 | position stop-reduction requested but not broker-confirmed | retain prior committed risk |
| RG-015 | unknown position exists | quarantine; do not size, adopt or close |
| RG-016 | day start equity `10,000`; current equity `9,940`; no flows | daily loss `60` |
| RG-017 | day start `10,000`; deposit `1,000`; current equity `10,940` | adjusted equity `9,940`; daily loss `60` |
| RG-018 | day start `10,000`; withdrawal `1,000`; current equity `8,940` | adjusted equity `9,940`; daily loss `60` |
| RG-019 | day start `10,000`; realized `-40`, current unrealized `-20`, current equity `9,940` | daily loss `60`, not `120` |
| RG-020 | day loss `50`; no remaining exposure; candidate planned loss `25` | prospective daily `75`; pass boundary |
| RG-021 | day loss `50.01`; no remaining exposure; candidate `25` | prospective `75.01`; reject |
| RG-022 | current day loss exactly `75`; candidate `0`/new entry | daily ceiling reached; reject new risk |
| RG-023 | week start `10,000`; normalized current `9,875`; candidate `25` | weekly prospective `150`; pass boundary |
| RG-024 | normalized weekly loss `125.01`; candidate `25` | reject weekly ceiling |
| RG-025 | unclassified balance operation in period | fail closed / quarantine accounting |
| RG-026 | inception normalized high water `10,200`; current normalized equity `9,725` | drawdown `475` |
| RG-027 | drawdown `475`; candidate `25` | prospective `500`; pass boundary |
| RG-028 | drawdown `475.01`; candidate `25` | reject drawdown ceiling |
| RG-029 | deposit raises raw equity by `2,000` with no trading change | normalized equity/high-water unchanged |
| RG-030 | trade admission budgets `25,25,25`; final net P/L `-25,-25,-25` | streak `1,2,3`; pause after third |
| RG-031 | budgets `25,25,25`; P/L `-12.50,-25,-37.50` | equivalents `0.5+1+1.5=3`; pause |
| RG-032 | losses total `2.5R`, then profitable instance `+0.01`, then `1R` loss | reset on profit; streak becomes `1`, no pause |
| RG-033 | losses `1R`, flat, `2R` | flat does not reset; pause at `3R` |
| RG-034 | Zone A loses `1R`; proposed Zone B lacks fresh analysis | reject semantics; never average/recover |
| RG-035 | stale account snapshot or non-finite numeric input | reject/fail closed |
| RG-036 | pre-check passes; account state changes before submission | approval invalidated; full re-evaluation required |
| RG-037 | fill slippage causes actual limit breach | alert + block new risk + reconcile; no retroactive approval and no automatic close authority |
| RG-038 | day loss `60`, week loss `120`, drawdown `470`, candidate `20` | daily prospective `80`, week `140`, DD `490`; reject because daily fails |
| RG-039 | day loss `40` already includes an open unrealized loss; existing additional loss from current mark to stop `20`; candidate `15` | prospective daily `75`; pass without double-counting prior unrealized loss |
| RG-040 | same as RG-039 but candidate `15.01` | prospective daily `75.01`; reject |
| RG-041 | `B=10,000; E=0` | fail closed; no positive trade cap |
| RG-042 | `B=10,000; E=9,999.999` | `K=9,999.999`; raw cap `24.9999975`; cap `24.99` |
| RG-043 | balance and equity are from different snapshots | reject inconsistent state |
| RG-044 | commission, swap, slippage or gap buffer is required but unavailable | reject; missing component is not zero |
| RG-045 | valid volumes `0.01,0.02,0.03`; planned losses `12.40,24.90,37.30`; cap `25` | select `0.02`, then re-price/re-test it |
| RG-046 | range entry can fill at 2,350.00–2,351.00; BUY stop fixed; upper entry has greater loss | size from 2,351.00 worst admissible entry |
| RG-047 | cash flow posts exactly at reconciled boundary and is included in `E(t0)` | exclude it from `(t0,t]`; do not normalize twice |
| RG-048 | restart has no reconstructable day-boundary snapshot | daily state unknown; block new risk |
| RG-049 | deposit raises raw equity above prior high, then is normalized out | `H` does not rise solely from deposit |
| RG-050 | trade has residual `0.01` volume or unreconciled commission | instance not complete; do not reset/update `Q_streak` |
| RG-051 | `Q_streak=2.99`; next `qj=0.01` exact decimal | pause at exactly `3.00` |
| RG-052 | unknown strategy volume cap | no sized approval; fail closed |

## 11. Property and invariant tests required before implementation

- Increasing candidate volume cannot reduce planned loss.
- Reducing `B` or `E` cannot increase per-trade cap.
- Increasing external deposits alone cannot improve normalized P/L or drawdown.
- Adding an owned exposure cannot reduce concurrent committed risk.
- A model field cannot alter policy constants, volume, risk or decision order.
- Boundary tests cover one cent below, exactly at and one cent above every monetary limit.
- Randomized ledgers reconcile `equity change = normalized trading change + external flows` without realized/unrealized double counting.
- Restart/replay of the same event journal produces identical state and decisions.
- Duplicate fills/events are idempotent; omitted/out-of-order events fail closed pending reconciliation.

## 12. Freeze boundary and remaining dependencies

The owner-approved constants, V1/M1 thresholds, applicable-capital formula, adjusted-equity method, drawdown method, prospective-limit inequalities, no-double-counting rule, and fail-closed invariants in this document are frozen for Phase 0 specification/testing. They do not authorize implementation or trading.

The following are genuine dependencies and are **not** silently frozen here:

| Dependency | Decision/evidence class | Effect while open |
|---|---|---|
| Exact trading-day and trading-week boundaries/timezone | engineering specification | daily/weekly state cannot be production-authoritative |
| Commission, swap, slippage and gap-buffer formula/data source | research + engineering specification | no `L_plan` approval |
| Exact multi-leg, partial-close and broker-adjustment P/L attribution | engineering specification | ambiguous instance completion blocks risk |
| Account-specific margin calculation and adverse-stress evidence | diagnostic + research | M1 inputs remain `UNKNOWN`; no final margin pass |
| Account/symbol calculation evidence, including asymmetric tick value | diagnostic | no account-specific sizing approval |
| Canonical reason-code/state enums shared with execution spec | engineering specification | interface not finally hashable |

Any change to Policy A monetary limits, risk fraction, allocation, loss-equivalent threshold, or upward scaling requires a new explicit owner decision and append-only Decision Log entry.
