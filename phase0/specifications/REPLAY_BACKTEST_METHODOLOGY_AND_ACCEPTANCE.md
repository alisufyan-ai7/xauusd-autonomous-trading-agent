# Replay/Backtest Methodology and Precommitted Acceptance Criteria

**Status:** Phase 0 candidate research specification  
**Version:** 0.1  
**Date:** 2026-08-11  
**Authorization boundary:** Offline research/framework design only. A passing replay cannot authorize automated demo or real trading.

## 1. Research unit and registry

Each setup family/version is a separate hypothesis with frozen features, labels, eligible regimes/sessions, entry/exit rules, parameter domain, cost model, and primary metric before results are viewed. Every trial—including failed, abandoned, manually inspected, or AI-suggested variants—receives a registry ID and immutable config/code/data hashes. Unregistered exploratory results cannot support acceptance.

The five initial families are evaluated separately and only combined under a predeclared portfolio/allocation rule. Zone B after a failed Zone A is a fresh observation and independent trade; it cannot be encoded as averaging or recovery.

## 2. Immutable data and lineage

For every source and partition record vendor/origin, instrument/account semantics, timezone, collection method, terms/rights, raw-file hashes, transformations, adjustment/cleaning rules, excluded intervals with reason, and dataset-manifest hash. Preserve raw broker numerical fields and semantic interpretations separately. Real-account and demo assumptions cannot be mixed silently.

Data-quality reports cover duplicates, ordering, gaps, stale/zero prices, bid/ask consistency, impossible OHLC, session boundaries, DST/holiday behavior, outliers, symbol-property changes, and survivorship/selection effects. Corrections produce a new dataset version; they never overwrite the tested corpus.

## 3. Causal replay rules

At simulated time `t`, code may access only data whose source publication/market timestamp and realistically modeled receipt time are available by `t`. Forming-candle high/low/close, future session outcome, revised economic data, future spread, and later-cleaned labels are unavailable. Features used live and in replay must share the same deterministic implementation and warm-up behavior; a reconciliation test compares replay features against frozen live-shadow fixtures.

Orders use bid/ask, symbol tick/point/volume rules, executable side, latency, slippage, missed fills, partial behavior where supportable, gaps, stop/limit semantics, session closure, freeze/stops constraints, commission, swap/financing, and currency conversion. Mid-price perfect fills are prohibited. When tick order inside a bar is unknowable, use tick data or a conservative declared ambiguity policy; do not choose favorable intrabar ordering.

## 4. Chronological design

Freeze chronological development, validation, and untouched final out-of-sample intervals before optimization. Use walk-forward folds where justified. Apply embargo/purging when label horizons overlap split boundaries. All scalers, thresholds, regimes, support/resistance, feature selection, and model/prompt tuning fit on past/development data only.

The final holdout is opened once for the frozen candidate. A failed holdout cannot be repeatedly tuned against; a material change creates a new research generation with a newly protected later holdout or prospective evidence. Report market-regime, setup, session, year/quarter/month, long/short, event proximity, and volatility breakdowns without selecting only favorable slices.

## 5. Trial accounting and overfitting control

Registry fields include hypothesis, author/tool, timestamp, parent trial, search method, full parameter space, sampled parameters, random seed, compute result, exclusions, and whether the result influenced later choices. Count correlated variants, prompts/models, feature changes, filters, cost assumptions, split choices, and manual restarts as research trials.

Use Probability of Backtest Overfitting and Deflated Sharpe Ratio where their assumptions and sample structure are defensible; otherwise predeclare a justified multiple-testing/selection-bias correction and simulation. Record effective number of trials and uncertainty. Never select PBO/DSR thresholds after results.

## 6. Precommitted candidate acceptance criteria

These conservative criteria are candidates for owner/specification approval before the first strategy search; exact confidence method and concentration constants marked TBD must be frozen first.

### 6.1 Mandatory validity gates

All must pass:

1. data/license/lineage and immutable hashes complete;
2. causal/leakage audit passes, including forming-candle, timezone, revision, and split-boundary tests;
3. deterministic repeat of the same replay produces byte-equivalent decisions/trade ledger subject to explicitly normalized metadata;
4. all trials and exclusions registered; no unexplained replay/live-feature mismatch;
5. zero violations of Risk Policy A, news locks, session rules, sizing, no-averaging, and state-machine invariants in replay;
6. no NaN/infinite/invalid price, volume, P/L, or silently dropped event; unresolved ambiguity fails the trade closed.

### 6.2 Economic/statistical gates

- Primary metric: out-of-sample net expectancy per unit of planned initial risk (`R`), after modeled costs. It must be positive.
- A predeclared confidence interval for OOS mean `R` must have lower bound greater than a **material-loss floor** (candidate `-0.05R`; requires approval), and the point estimate must remain positive. Bootstrap must preserve temporal dependence (stationary/moving block or justified alternative).
- Total and setup-level sample size must be justified prospectively from minimum detectable effect, dependence, variance, and desired interval width; no universal count is invented after results. Sparse families are `INSUFFICIENT_EVIDENCE`, not accepted.
- Selection-adjusted evidence must pass a predeclared DSR/PBO or justified alternative threshold. Candidate: DSR probability at least 0.95 and PBO at most 0.20, subject to method-validation and owner approval.
- OOS maximum drawdown, daily/weekly loss paths, and loss streaks under base and stress costs must remain inside Policy A when replayed with the approved allocation and deterministic pause rules. Breach is rejection, not merely a lower score.
- Concentration limits must be frozen before results: no single month, session, event cluster, or small trade subset may provide an unacceptable share of total net profit. Exact limit is TBD after a methodology choice that does not inspect strategy outcomes.

### 6.3 Robustness gates

Candidate must remain non-catastrophic and policy-compliant under, at minimum:

- 2x median observed spread and a separately modeled tail-spread schedule;
- adverse latency/slippage distributions, including stop gaps beyond intended loss;
- missed entries, delayed exits, and conservative ambiguous intrabar sequencing;
- session/holiday gaps and news shock periods;
- reasonable neighboring parameters without reliance on a single isolated optimum;
- subperiod/regime/session/setup removal and block resampling;
- data-quality exclusions and plausible symbol/broker property variation.

“Non-catastrophic” means no risk-rule violation, no loss beyond the approved strategy drawdown ceiling under the base allocation, and no operational inconsistency; positive profit under every stress is not required. Exact stress distributions and severity quantiles must be frozen from empirical evidence before testing.

## 7. Reporting

Publish dataset/code/config hashes; split map; all-trial registry; trade and rejection ledger; gross/net performance; expectancy and uncertainty; drawdown depth/duration; tail losses; loss streaks; exposure/time-in-market; turnover; spread/slippage/swap/commission; regime/session/setup/month breakdowns; parameter stability; PBO/DSR or alternative; stress and sensitivity results; leakage audit; limitations; and deviations from plan. Report rejected/no-trade observations and data/provider outages, not only executed simulations.

No annualized return, Sharpe, win rate, or profitable curve alone constitutes acceptance. Policy compliance and uncertainty dominate headline profit.

## 8. Relationship to later gates

Passing this specification and a later Gate 3 replay only permits consideration of non-executing live shadow validation. Shadow must cover at least the frozen duration/event/regime requirements and reconcile live versus replay features. Demo execution, tiny live, and scaling each require later explicit owner authorization and separate evidence. Risk must never scale automatically beyond the USD 10,000 approved allocation.

## 9. Unresolved research/decisions

- Select licensed historical bid/ask/tick, session, and news sources and retention rights; no purchase is approved.
- Freeze dataset date range, split dates, walk-forward scheme, embargo, and final holdout policy per setup horizon.
- Freeze fill/latency/slippage/gap/swap/commission models using account-specific evidence.
- Approve confidence procedure, material-loss floor, DSR/PBO (or alternative) thresholds, concentration limits, minimum detectable effect, and stress distributions before optimization.
- Define treatment of correlated trades, overlapping setups, partial exits, multiple testing across five families, and strategy-combination allocation.
- Freeze prospective shadow duration, required event/regime coverage, and replay/live feature tolerance.

