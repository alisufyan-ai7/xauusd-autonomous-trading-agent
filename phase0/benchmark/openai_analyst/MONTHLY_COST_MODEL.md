# OpenAI Analyst Monthly Cost Model

**Date:** 2026-08-23  
**Status:** Corrected planning estimate; replace assumptions with chronological non-trading replay usage  
**Trading authorization:** None

## Price basis

Official list prices used for standard API processing, per one million tokens:

| Model | Input | Output | Intended role |
|---|---:|---:|---|
| GPT-5.6 Terra | USD 2.50 | USD 15.00 | Non-selected comparator |
| GPT-5.6 Sol | USD 5.00 | USD 30.00 | Selected candidate |
| GPT-5.6 Luna | USD 1.00 | USD 6.00 | Non-selected cost comparator |

Source: [official OpenAI API pricing](https://platform.openai.com/pricing).
Prices can change and must be rechecked before a production budget is frozen.
Requests above 272,000 input tokens have separate long-context multipliers; the
minimized planning payload is intentionally far below that boundary.

## Planning assumptions

One Analyst request is modeled as 2,000 input tokens and 300 billed output tokens, including reasoning tokens. A local deterministic gate calls the Analyst only for a nominated candidate setup. It does not poll the model continuously. There are no model-triggered tools or retries.

Monthly cost is:

`calls_per_day * 30 * ((2,000 * input_price) + (300 * output_price)) / 1,000,000`

## Estimated monthly API cost

| Eligible calls/day | Terra comparator | Sol selected candidate | Luna comparator |
|---:|---:|---:|---:|
| 10 | USD 2.85 | USD 5.70 | USD 1.14 |
| 24 | USD 6.84 | USD 13.68 | USD 2.74 |
| 50 | USD 14.25 | USD 28.50 | USD 5.70 |
| 96 | USD 27.36 | USD 54.72 | USD 10.94 |

For the selected Sol candidate, the illustrative planning envelope is **USD
5.70–22.80/month** at 10–40 eligible calls/day under the 2,000-input/300-output
assumption. This is not a budget recommendation: non-trading replay must first
measure eligible-call frequency and token p50/p95. Terra and Luna are not
automatic fallbacks.

These figures exclude any future licensed market/news data, VPS, monitoring, storage, or network costs. No paid data provider has been approved.

## Gate 0 benchmark budget

The frozen corpus has 16 live-eligible cases across three models (48 requests) and two local-block cases. The runner's deliberately conservative reservation is:

| Model | Reserved maximum for 16 requests |
|---|---:|
| Terra | USD 0.3680 |
| Sol | USD 0.7360 |
| Luna | USD 0.1472 |
| **Total** | **USD 1.2512** |

This is below the owner-approved USD 8 ceiling. Actual cost should be lower if responses use fewer than the 1,200-token maximum. The runner stops before a request whose reservation could exceed the cumulative ceiling and performs no retries.

## Budget recommendation

The benchmark is complete and no additional call is authorized. The preserved
two-run usage counters recompute to USD 0.478069 at the 2026-08-23 list-price
basis; provider billing is authoritative. Do not approve a production monthly
budget until non-trading replay measures p50/p95 tokens and eligible-call
frequency.
