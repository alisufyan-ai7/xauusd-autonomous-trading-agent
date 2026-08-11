# Phase 0 Objective Setup-Family Specification

**Document ID:** P0-SETUPS-001  
**Version:** 0.1-draft  
**Status:** Engineering specification candidate; not approved for trading  
**Scope:** XAUUSD research, replay, and deterministic proposal validation only  
**Authorization boundary:** This document does not authorize order submission, automated demo trading, or real trading. External Python trading remains disabled.

## 1. Purpose and normative language

This document converts five named setup families into objective candidate algorithms:

1. Trend Pullback (`TPB`)
2. Breakout + Retest (`BRT`)
3. Failed Break / Reclaim (`FBR`)
4. Range Support/Resistance (`RSR`)
5. Momentum Continuation (`MOC`)

`MUST`, `MUST NOT`, `SHALL`, and `REQUIRED` are normative. Each predicate has exactly three evaluation states: `TRUE`, `FALSE`, or `UNKNOWN`. Any required predicate that is `FALSE` or `UNKNOWN` makes the family ineligible and produces `NO_TRADE` with reason codes. No discretionary visual interpretation may replace a predicate.

This is a pre-optimization baseline. The numerical constants below are candidate values to freeze before the first formal replay. They MUST NOT be tuned after observing out-of-sample results without declaring a new version and counting a new research trial.

## 2. Common data and calculation contract

### 2.1 Timeframes and decision instant

| Role | Timeframe | Symbol |
|---|---:|---|
| Regime | H4 | `TF_R` |
| Structure | H1 | `TF_S` |
| Trigger | M15 | `TF_T` |

An evaluation occurs only immediately after a completed M15 bar is available. Index `0` means the most recently completed bar; forming bars are never inputs. H1 and H4 bars used in an evaluation must also be completed at the decision instant. All timestamps are UTC.

### 2.2 Required market series

For every required timeframe, each bar contains UTC open time, open, high, low, close, and tick volume. Bid/ask snapshots include broker timestamp, local receipt timestamp, bid, ask, and spread. The system requires at least 300 complete H4 bars, 500 H1 bars, and 1,000 M15 bars after gap validation.

Evaluation returns `DATA_INVALID` if any of the following holds:

- the current quote age exceeds 2 seconds;
- the completed M15 bar is unavailable more than 30 seconds after its expected close;
- any duplicate or non-monotonic bar timestamp exists;
- any OHLC identity is invalid (`high < max(open,close)`, `low > min(open,close)`, or `high < low`);
- an unexplained missing bar occurs inside a broker-reported open session within the maximum indicator lookback;
- fewer than the required warm-up bars are present;
- account symbol, price precision, tick size, or trading-session state is unknown.

Known broker session breaks are not data gaps. Session metadata must classify them before feature calculation.

### 2.3 Frozen feature definitions

For timeframe `t` and completed bar `i`:

- `TR_t[i] = max(H[i]-L[i], abs(H[i]-C[i+1]), abs(L[i]-C[i+1]))`.
- `ATR_t(n)` is Wilder's moving average of true range over `n` bars.
- `EMA_t(n)` is the standard exponentially weighted close with `alpha = 2/(n+1)`, seeded by the arithmetic mean of the first `n` chronological observations.
- `ADX_t(14)`, `+DI_t(14)`, and `-DI_t(14)` use Wilder's original smoothing and directional-movement definitions.
- `RSI_t(14)` uses Wilder-smoothed gains and losses; a zero loss denominator yields 100 and zero gain/loss yields 50.
- `body[i] = abs(C[i]-O[i])`.
- `range[i] = H[i]-L[i]`.
- `body_fraction[i] = body[i]/range[i]`; zero range makes the value `UNKNOWN`.
- `close_location_long[i] = (C[i]-L[i])/range[i]`.
- `close_location_short[i] = (H[i]-C[i])/range[i]`.
- `slope(series,n) = (series[0]-series[n])/n`, measured in price per bar.
- A price comparison uses full-precision values. Proposed order prices are tick-normalized only after semantic validation.

### 2.4 Objective pivots, levels, and zones

A confirmed swing high at bar `i` on a timeframe is a high strictly greater than the highs of the two immediately earlier and two immediately later chronological bars. A confirmed swing low is defined symmetrically. Equal highs/lows are consolidated into one level at their median price, with the most recent timestamp, when their maximum separation is at most `0.10 * ATR_H1(14)`.

Only swings already confirmed at the decision instant may be used. The most recent 120 completed H1 bars form the structure window.

A level's tolerance is:

`level_tol = max(3 * tick_size, 0.10 * ATR_H1(14))`.

A level is `tested` when a completed H1 bar's range intersects `[level-level_tol, level+level_tol]`. Tests separated by fewer than four H1 bars count as one test. A level is valid when it has at least two distinct tests, or is the most recent confirmed swing at an otherwise qualifying trend impulse boundary.

### 2.5 Impulse leg

A bullish impulse is the move from a confirmed H1 swing low `L0` to a later confirmed H1 swing high `H0` satisfying all of:

- `H0-L0 >= 1.5 * ATR_H1(14)` measured at `H0`;
- duration is 3 through 24 H1 bars inclusive;
- no completed H1 close during the leg is below `L0-level_tol`;
- net directional efficiency `(H0-L0) / sum(abs(C[j]-C[j+1])) >= 0.45` over the leg.

A bearish impulse is symmetric.

### 2.6 Regime classifier

The regime is calculated locally and returns exactly one of `UP_TREND`, `DOWN_TREND`, `RANGE`, `HIGH_VOLATILITY`, or `UNCLASSIFIED`, in this priority order:

1. `HIGH_VOLATILITY` if `ATR_H1(14) / median(ATR_H1(14) over prior 100 completed H1 bars) >= 1.80`.
2. `UP_TREND` if H4 `EMA20 > EMA50`, `slope(EMA20,5) > 0`, H4 `ADX14 >= 20`, `+DI > -DI`, and the two most recent confirmed H1 swing highs and lows are each rising by more than `level_tol`.
3. `DOWN_TREND` if the exact directional inverse holds.
4. `RANGE` if H4 `ADX14 < 20`, `abs(EMA20-EMA50) <= 0.35*ATR_H4(14)`, and a valid H1 range as defined in Section 7 exists.
5. Otherwise `UNCLASSIFIED`.

`HIGH_VOLATILITY` and `UNCLASSIFIED` admit none of the five families in v0.1.

### 2.7 Common safety filters

Every family requires all of the following at both proposal time and any later execution-validation time:

- broker session is open and sufficient time remains to the scheduled session break for entry expiry plus the intended management buffer;
- current spread is at most both `1.50 * median spread` for the same UTC 15-minute bucket over the prior 20 eligible sessions and `0.10 * ATR_M15(14)`;
- `ATR_M15(14)` is between the 10th and 90th percentile of its trailing 60-session same-time distribution;
- no news lock, calendar-source disagreement, calendar-source failure, or abnormal-volatility circuit breaker is active;
- no unknown exposure, quarantine, stale state, unresolved broker submission, or competing proposal exists;
- proposed initial reward/risk to TP1 is at least 1.5 and to final target is at least 2.0 after spread and configured adverse-slippage allowance;
- stop distance is at least `max(broker minimum stop distance, 3*tick_size, 0.25*ATR_M15(14))` and at most `2.0*ATR_H1(14)`;
- entry has not already been consumed for the same setup identity.

Until the news specification freezes event-specific windows, `news_state != CLEAR` is a hard `NO_TRADE`; no provisional default window may be inferred here.

### 2.8 Setup identity and duplicate control

The immutable setup key is:

`SHA256(strategy_version | account_fingerprint | symbol | family | direction | anchor_swing_times | level_prices | trigger_bar_time)`.

Only one live proposal/order/position may derive from a setup key. Re-evaluation cannot create another entry from the same key. A materially new structure requires new confirmed anchors and therefore a different key.

### 2.9 Common entry, stop, target, and expiry rules

- Entry may be `MARKET_AFTER_CLOSE`, `LIMIT`, or `STOP`; the family fixes which are permitted.
- Market entry uses the first valid quote after the confirming bar and expires 30 seconds after proposal creation.
- Pending entry price must be reached within the family expiry and before any cancellation predicate.
- Structural stop is placed beyond the invalidating structure plus `stop_buffer = max(3*tick_size, 0.10*ATR_M15(14))`.
- TP1 is the nearer of the family's first structural target and `1.5R` only if that target is at least `1.5R`; otherwise reject.
- Final TP is the family's declared structural target and must be at least `2.0R`; otherwise reject.
- Partial-exit fraction, break-even behavior, and trailing behavior are intentionally `UNRESOLVED`; no family passes specification freeze until these are separately selected and encoded. Backtests MUST NOT silently invent them.
- No stop may be widened after entry. No target may be moved farther to make a failed reward/risk check pass.

## 3. Family 1 — Trend Pullback (`TPB`)

### 3.1 Eligibility and location

Long requires `UP_TREND`; short requires `DOWN_TREND`. Identify the most recent qualifying H1 impulse in the trend direction.

For a bullish impulse from `L0` to `H0`, define retracement `r(p)=(H0-p)/(H0-L0)` and two non-overlapping zones:

- Zone A: `r in [0.382, 0.500]`.
- Zone B: `r in (0.500, 0.618]`.

For a bearish impulse, mirror the formula upward from `H0`. A zone qualifies only if it intersects at least one independently calculated location: H1 EMA20 within `level_tol`, a prior valid H1 swing level, or the broken boundary of the preceding H1 consolidation. Fibonacci location alone is insufficient.

Before the first zone touch, price must not have closed beyond the impulse origin and must not have printed a new trend-direction impulse of at least `1.0*ATR_H1` that supersedes `H0/L0`.

### 3.2 Confirmation and entry

After first entering a zone, confirmation must occur within eight completed M15 bars and consists of both:

1. a rejection bar whose wick through/toward the zone is at least its body, whose close is in the trendward top/bottom 35% of its range, and whose close remains inside or trendward beyond the zone; and
2. within the next two M15 bars, a completed close beyond the rejection bar's trendward extreme by at least one tick.

Entry is `STOP` one tick beyond the confirming close/bar extreme, whichever is more trendward. It expires after four M15 bars.

### 3.3 Invalidation, stop, targets, cancellation

- Invalidation before entry: completed H1 close beyond the impulse origin; completed M15 close beyond the far edge of the active zone by more than `0.15*ATR_M15`; trend regime loss; or a newer qualifying impulse replaces the anchors.
- Stop: beyond the lower/higher of the rejection extreme and active-zone far edge, plus `stop_buffer`.
- First structural target: impulse endpoint `H0/L0`.
- Final structural target: the nearest confirmed H1 swing level beyond the impulse endpoint; if absent, the measured extension at `1.272` of the impulse.
- Cancel pending entry on any common safety-filter failure, opposite M15 structure break, expiry, or news lock.

### 3.4 Sequential Zone A / Zone B rule

Zone A and Zone B are independent opportunities, never layers of one position:

- Zone A may generate at most one setup and one trade.
- Once a Zone A entry fills, no Zone B setup may be created while any Zone A-derived exposure remains.
- A stopped, invalidated, cancelled, or expired Zone A setup is permanently finished; it cannot be reopened from the same Zone A touch.
- A later Zone B touch requires a new evaluation using a new trigger bar, current features, current news/spread/account state, and a new setup key.
- Zone B risk is calculated independently under the current Risk Governor; previous Zone A loss cannot increase size, widen stop, relax confirmation, or change the risk budget.
- Zone B is prohibited if the impulse origin has been breached, the regime is no longer eligible, daily/weekly pause is active, or Zone A exposure still exists.
- The Zone B order MUST NOT share a recovery, averaging, grid, martingale, or combined-cost-basis objective with Zone A.

## 4. Family 2 — Breakout + Retest (`BRT`)

### 4.1 Eligibility and breakout structure

Regime must be `UP_TREND` for long or `DOWN_TREND` for short. The breakout boundary must be a valid H1 level with at least two tests in the prior 120 H1 bars. The pre-break consolidation must contain at least six and at most 30 H1 bars, with total high-low width between `0.5` and `2.0 * ATR_H1(14)`.

A bullish breakout bar is a completed H1 bar satisfying:

- close above resistance by at least `0.10*ATR_H1`;
- body at least `0.60` of bar range;
- body at least `1.20 * median H1 body` over the prior 20 bars;
- close in the top 20% of its range;
- H1 ADX is not declining by more than 3 points over five bars.

Bearish is symmetric.

### 4.2 Retest, confirmation, and entry

The retest must begin within 12 H1 bars after breakout. Price must intersect the boundary band `level +/- level_tol` without an H1 close back through the boundary by more than `0.15*ATR_H1`.

M15 confirmation is a rejection bar followed within two bars by a close beyond its trendward extreme, using the same rejection metrics as TPB. Entry is `STOP` one tick beyond the confirmation extreme and expires after four M15 bars.

### 4.3 Invalidation, stop, targets, cancellation

- Invalidation: H1 close back inside the old consolidation by more than `0.15*ATR_H1`, opposite breakout through the far consolidation boundary, or no qualifying retest within 12 H1 bars.
- Stop: beyond the retest extreme and old boundary by `stop_buffer`.
- First structural target: nearest confirmed H1 level in breakout direction.
- Final target: consolidation measured move (`breakout boundary +/- consolidation width`) or next confirmed H1 level, whichever is nearer while still at least `2R`.
- Cancel if price reaches the final target before entry, retest depth exceeds 50% of the old consolidation, common filter fails, or pending expiry occurs.

## 5. Family 3 — Failed Break / Reclaim (`FBR`)

### 5.1 Eligibility and failed-break event

Regime must be `RANGE`, or `UP_TREND`/`DOWN_TREND` only when trading in the prevailing trend direction after a counter-trend liquidity break. The reference boundary must be a valid range boundary or H1 swing with at least two prior tests.

For a bullish reclaim of support:

1. price trades below support by at least `0.10*ATR_H1` but no more than `0.60*ATR_H1`;
2. within four completed M15 bars of the first breach, an M15 bar closes back above support plus one tick;
3. that reclaim bar closes in its top 35%, and either its lower wick is at least its body or its body is at least `1.20 * median M15 body(20)`;
4. no completed H1 bar has closed below support by more than `0.15*ATR_H1`.

Bearish reclaim of resistance is symmetric.

### 5.2 Confirmation and entry

Within the next three M15 bars, price must hold the reclaimed side: no M15 close through the boundary by more than `0.05*ATR_M15`. A confirming M15 close must exceed the reclaim bar extreme by one tick. Entry is `STOP` one tick beyond that confirming extreme and expires after three M15 bars.

### 5.3 Invalidation, stop, targets, cancellation

- Invalidation: close beyond the failed-break extreme; H1 acceptance outside the boundary; or a second outward excursion exceeding the first failed-break extreme before entry.
- Stop: beyond the failed-break extreme plus `stop_buffer`.
- Range-regime TP1: range midpoint. Trend-regime TP1: nearest H1 opposing swing.
- Final target: opposite valid range boundary in `RANGE`; in trend, the next confirmed H1 level or `2R`, with structural target required at or beyond `2R`.
- Cancel on no follow-through within three M15 bars, price reaching TP1 before entry, or any common filter failure.

This family is a reversal after objective rejection. A simple boundary touch or wick without reclaim/hold/confirmation is not eligible.

## 6. Family 4 — Range Support/Resistance (`RSR`)

### 6.1 Valid range definition

Regime must be `RANGE`. Over a candidate window of 24 to 120 completed H1 bars:

- upper boundary is the median of at least two consolidated swing highs;
- lower boundary is the median of at least two consolidated swing lows;
- each boundary has at least two tests separated by four H1 bars;
- width is between `1.5` and `5.0 * ATR_H1(14)`;
- at least 80% of H1 closes lie within the boundaries expanded by `level_tol`;
- absolute linear-regression slope of H1 closes, converted over the full window, is at most `0.30 * range_width`;
- no completed H1 close beyond a boundary exceeds `0.15*ATR_H1` during the last 12 bars.

If multiple windows qualify, select the shortest; ties select the most recent start.

### 6.2 Location, confirmation, and entry

Longs are eligible only in the bottom 15% of range width; shorts only in the top 15%. Entries are prohibited in the middle 70%.

Confirmation requires an M15 rejection bar at the boundary (wick at least body; close in directional 35% of range), followed within two bars by a close beyond its directional extreme. Entry is `STOP` one tick beyond confirmation and expires after four M15 bars.

### 6.3 Invalidation, stop, targets, cancellation

- Invalidation: H1 close outside boundary by more than `0.15*ATR_H1`; range classifier loss; or a new boundary changes range width by more than 10%.
- Stop: beyond boundary and rejection extreme plus `stop_buffer`.
- TP1: range midpoint.
- Final TP: opposite boundary minus/plus `level_tol`.
- Cancel if entry would occur after price traverses 35% of range width from the traded boundary, the range breaks, expiry occurs, or a common filter fails.

Only one entry per boundary test cluster is permitted. A second attempt requires price first to move at least 40% of the range away from the boundary and later return as a distinct test, with a new setup key.

## 7. Family 5 — Momentum Continuation (`MOC`)

### 7.1 Eligibility and compression

Regime must be `UP_TREND` for long or `DOWN_TREND` for short. A qualifying directional impulse must have occurred within the prior eight H1 bars and measure at least `1.5*ATR_H1`.

It must be followed by a 3-to-8-bar M15 compression satisfying all of:

- compression total range is at most `0.75*ATR_H1`;
- each M15 close remains above the impulse 50% retracement for long (below for short);
- median M15 range during compression is at most 70% of median range over the preceding 20 M15 bars;
- counter-trend retracement is no more than 38.2% of the impulse;
- compression boundary slope is non-opposing or convergent; specifically, long compression lows have regression slope `>= -0.05*ATR_M15 per bar`, and short compression highs have the symmetric bound.

### 7.2 Momentum trigger and entry

A long trigger is a completed M15 close above the compression high by at least `0.05*ATR_M15`, with body at least `0.60` of range, body at least `1.20*median body(20)`, close in top 20%, and `RSI14` between 55 and 78. Short is symmetric with RSI between 22 and 45.

Entry is `MARKET_AFTER_CLOSE` only. If a valid quote is unavailable within 30 seconds or entry slippage from trigger close exceeds `0.15*ATR_M15`, output `NO_TRADE`; do not chase.

### 7.3 Invalidation, stop, targets, cancellation

- Invalidation before entry: any close through the opposite compression boundary; trend regime loss; trigger quote too late or too far from trigger.
- Stop: beyond the opposite compression boundary plus `stop_buffer`.
- TP1: prior impulse endpoint if still ahead and at least `1.5R`; otherwise nearest confirmed H1 level at least `1.5R`.
- Final target: next confirmed H1 level or impulse measured extension `1.272`, whichever is nearer and at least `2R`.
- No pullback entry is allowed after a missed market trigger under the same setup key. A later consolidation requires a newly formed 3-to-8-bar compression and new key.

## 8. Deterministic family selection and conflicts

At one decision instant, every family is evaluated independently. The selector applies:

1. discard every candidate with any failed/unknown required predicate;
2. discard directionally conflicting candidates;
3. if more than one candidate remains in the same direction, retain the candidate with the greatest net structural reward/risk;
4. if reward/risk differs by less than 0.10, use fixed precedence `FBR > BRT > TPB > RSR > MOC` because rejection/retest evidence is more structurally bounded than immediate momentum;
5. if inputs imply genuinely different anchors rather than the same opportunity, still permit only one new XAUUSD risk-increasing proposal at a time under the conservative baseline;
6. any unresolved tie or semantic conflict yields `NO_TRADE`.

The selector cannot choose based on AI confidence. The Analyst may classify or propose a candidate, but deterministic validation recomputes every predicate.

## 9. Pass/fail output contract

Each family evaluation emits a trace containing:

- strategy/family version and setup key;
- snapshot ID and exact bar/quote timestamps;
- direction and regime;
- anchor swing/level IDs and prices;
- every predicate name, observed value, threshold, and `TRUE/FALSE/UNKNOWN` result;
- proposed entry type/price, invalidation, stop, TP1, final TP, expiry, and cancellation rules;
- gross and cost-adjusted reward/risk;
- news, session, spread, volatility, data-health, duplicate, exposure, and quarantine states;
- terminal result `PASS_CANDIDATE` or `NO_TRADE` plus reason codes.

`PASS_CANDIDATE` means only that the setup may be sent through schema/freshness/semantic validation and the deterministic Risk Governor. It is not permission to place an order.

Minimum reason codes include:

`DATA_INVALID`, `REGIME_INELIGIBLE`, `STRUCTURE_MISSING`, `LOCATION_INVALID`, `CONFIRMATION_MISSING`, `RR_INSUFFICIENT`, `SPREAD_LOCK`, `VOLATILITY_LOCK`, `NEWS_LOCK`, `SESSION_LOCK`, `STALE_SNAPSHOT`, `DUPLICATE_SETUP`, `UNKNOWN_EXPOSURE`, `ZONE_SEQUENCE_BLOCK`, `ENTRY_EXPIRED`, `STRUCTURE_INVALIDATED`, and `SPEC_UNRESOLVED`.

## 10. Required pre-implementation test vectors

Before Gate 0 can treat this specification as frozen, a separate golden-vector set must cover at least:

- one exact pass and one failure for every normative predicate in every family;
- long/short symmetry for every formula;
- equality at every numeric boundary and one-tick values on both sides;
- forming-candle exclusion and swing-confirmation look-ahead prevention;
- session gaps versus unexplained data gaps;
- stale quotes/bars, missing warm-up, duplicate timestamps, zero-range bars, and clock disagreement;
- abnormal spread, volatility percentile boundary, news/feed failure, and session-close proximity;
- insufficient reward/risk after costs despite sufficient gross reward/risk;
- duplicate setup and restart re-evaluation;
- simultaneous family conflict and exact selector tie;
- TPB Zone A fill, loss, cancellation, expiry, and Zone B fresh-analysis cases;
- explicit proof that Zone B cannot coexist with Zone A exposure or inherit/expand Zone A risk;
- BRT false breakout, delayed retest, and retest too deep;
- FBR wick without reclaim, reclaim without hold, and H1 acceptance outside;
- RSR middle-of-range rejection and boundary-test cluster reuse;
- MOC missed/chased trigger and newly formed later compression;
- tick-size normalization that changes stop distance or reward/risk across a threshold.

Property tests must demonstrate:

- adding stale or unknown inputs cannot convert `NO_TRADE` to `PASS_CANDIDATE`;
- widening spread or adverse-slippage assumptions cannot improve net reward/risk;
- no setup can produce more than one setup key from identical inputs;
- no stop normalization may reduce structural protection;
- long/short mirror datasets produce mirrored decisions within tick precision;
- no family reads a forming candle or a not-yet-confirmed pivot.

## 11. Unresolved decisions required before freeze

This candidate is not yet a complete frozen strategy contract. The following require explicit engineering/owner disposition before implementation or formal strategy search:

1. partial-exit fraction and whether TP1 is informational or executable;
2. break-even and trailing-stop behavior, including whether either is allowed;
3. precise session-close management buffer;
4. final news-event taxonomy, lock windows, resumption and provider-health contract;
5. spread-history source and behavior before 20 eligible sessions exist;
6. whether tick volume is admitted as a feature (v0.1 does not use it);
7. permitted holding across daily session break/weekend (v0.1 makes no authorization);
8. formal cost/slippage model used for net reward/risk;
9. empirical review of candidate constants followed by a predeclared freeze, without observing out-of-sample outcomes;
10. interaction between one-proposal-at-a-time selection and an owner-approved concurrent-risk policy.

Until these are resolved, an end-to-end evaluator MUST return `SPEC_UNRESOLVED` before any executable intent could be constructed.

## 12. Research governance

Each family is versioned and evaluated separately. Dataset hashes, feature-code hash, parameter set, all trials, chronology, embargo/purge rules, costs, and acceptance thresholds must be declared before optimization. Results must be reported by family, regime, session, volatility bucket, and news proximity. A family that fails is rejected or revised under a new version; its historical trial remains recorded. Combining families cannot conceal a failed family.

`NO_TRADE` is a normal successful outcome. Missing a move, including a profitable one, is not a specification failure when required predicates do not pass.
