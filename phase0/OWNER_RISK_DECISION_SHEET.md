# Owner Risk Decision Sheet - USD 10,000 Reference Allocation

**Status:** Proposals only; no option is approved until the owner explicitly selects it.  
**Gate 0:** INCOMPLETE  
**Important:** “planned loss” is the broker-calculated stop loss before gap/slippage stress. A stop is not a loss guarantee.

## 1. Bundled policy alternatives

| Policy | Per-trade planned loss | Concurrent planned risk | Daily realized/equity stop | Weekly stop | Total strategy drawdown stop | Consecutive full-risk losses | Trade-off |
|---|---:|---:|---:|---:|---:|---:|---|
| A - Capital preservation **(recommended start)** | $25 / 0.25% | $50 / 0.50% | $75 / 0.75% (3 losses) | $150 / 1.50% (6 losses) | $500 / 5.00% (20 losses) | Pause after 3 | Slow learning and fewer simultaneous trades; strongest error containment. |
| B - Conservative | $50 / 0.50% | $100 / 1.00% | $150 / 1.50% (3 losses) | $300 / 3.00% (6 losses) | $750 / 7.50% (15 losses) | Pause after 3 | Faster evidence accumulation but doubles loss impact versus A. |
| C - Moderate, not recommended initially | $75 / 0.75% | $150 / 1.50% | $225 / 2.25% (3 losses) | $450 / 4.50% (6 losses) | $1,000 / 10.00% (~13.3 losses) | Pause after 3 | More opportunity and volatility; unsuitable before execution reliability is demonstrated. |

Counts assume full planned-risk losses and ignore gaps, slippage, commissions, swaps, correlations, and prior P/L. Daily, weekly, concurrent, and drawdown limits are independent hard ceilings; the earliest reached ceiling controls.

## 2. Recommended capital-preservation details

| Control | Recommended proposal | Deterministic behavior after breach |
|---|---|---|
| Risk basis | Minimum of current balance, current equity, and $10,000 strategy allocation | Never increase dollar risk because equity has fallen; increasing allocation requires new approval. |
| Per trade | $25 / 0.25% planned; also pass adverse-gap/slippage stress | Reject new order if broker-computed worst case exceeds cap. No “high confidence” override. |
| Concurrent | $50 / 0.50%, including pending orders and correlated/unknown exposures conservatively | Quarantine new risk. Unknown exposure is counted at a conservative bound until reconciled. |
| Daily | $75 / 0.75%, measured on realized P/L plus adverse open-equity movement from UTC day baseline | Cancel only agent-owned risk-increasing pending orders if later authorized; no new risk until next approved trading day and incident review. |
| Weekly | $150 / 1.50%, same equity-aware method from Monday 00:00 UTC baseline unless broker session boundary is later approved | Pause through the next weekly boundary; operator acknowledgement required. |
| Total drawdown | $500 / 5.00% from high-water strategy equity | Indefinite halt; formal review and explicit reauthorization. Automatic reset is prohibited. |
| Consecutive losses | 3 closed full-risk-equivalent losses; partial losses accumulated in R | Pause at least through the next full broker session and require diagnostics; exact cool-down remains to approve. |
| Margin/free margin | Project stressed positions using broker `order_calc_margin` plus higher-margin/news stress. Require projected margin level >= 1,000% and projected free margin >= 90% of equity; stricter of risk or margin rule wins. | Reject new risk. Leverage 1:2000 is not a reason to relax cash-loss caps. Threshold requires demo stress validation. |
| Tiny live | $5 / 0.05% planned loss per trade, one position/pending setup at a time, maximum $10 aggregate open risk; 0.01 lot is only a volume floor, not an entitlement | Halt on first reconciliation/safety incident; performance cannot justify scaling by itself. |
| Unknown exposure | No automatic ownership or closure | `QUARANTINED`: block all new risk and alert. Emergency closure policy remains open. |

## 3. Decisions requested from the owner

Choose A, B, or C, or provide changes to individual rows. The recommended answer is:

> Approve Policy A as the Phase 0 risk specification baseline, subject to later demo validation. Keep automatic closure of unknown exposure unauthorized.

Approval freezes limits for specification/testing only. It does not authorize trading. Any later increase requires a new Decision Log entry and fresh evidence.

