# OpenAI Analyst Monthly Cost Model

**Date:** 2026-08-12  
**Status:** Planning estimate; replace assumptions with measured benchmark usage  
**Trading authorization:** None

## Price basis

Official list prices used for standard API processing, per one million tokens:

| Model | Input | Output | Intended role |
|---|---:|---:|---|
| GPT-5.6 Terra | USD 2.00 | USD 12.00 | Primary |
| GPT-5.6 Sol | USD 4.00 | USD 20.00 | Challenger/evaluation only |
| GPT-5.6 Luna | USD 0.20 | USD 1.20 | Cost baseline |

Sources: [Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), and [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna). Prices can change and must be rechecked before a production budget is frozen.

## Planning assumptions

One Analyst request is modeled as 2,000 input tokens and 300 billed output tokens, including reasoning tokens. A local deterministic gate calls the Analyst only for a nominated candidate setup. It does not poll the model continuously. There are no model-triggered tools or retries.

Monthly cost is:

`calls_per_day * 30 * ((2,000 * input_price) + (300 * output_price)) / 1,000,000`

## Estimated monthly API cost

| Eligible calls/day | Terra primary | Sol if used for every call | Luna if used for every call |
|---:|---:|---:|---:|
| 10 | USD 2.28 | USD 4.20 | USD 0.23 |
| 24 | USD 5.47 | USD 10.08 | USD 0.55 |
| 50 | USD 11.40 | USD 21.00 | USD 1.14 |
| 96 | USD 21.89 | USD 40.32 | USD 2.19 |

Recommended planning envelope for the proposed event-driven design is **USD 3–10/month for Terra** while the local gate averages roughly 10–40 eligible calls/day. Sol should remain a sampled challenger rather than run on every production candidate; a 10% Sol audit sample adds about 18% to Terra-only model spend under equal token usage. Luna is a cost comparator, not an automatic fallback.

These figures exclude any future licensed market/news data, VPS, monitoring, storage, or network costs. No paid data provider has been approved.

## Gate 0 benchmark budget

The frozen corpus has 16 live-eligible cases across three models (48 requests) and two local-block cases. The runner's deliberately conservative reservation is:

| Model | Reserved maximum for 16 requests |
|---|---:|
| Terra | USD 0.3436 |
| Sol | USD 0.5768 |
| Luna | USD 0.0344 |
| **Total** | **USD 0.9548** |

This is below the owner-approved USD 8 ceiling. Actual cost should be lower if responses use fewer than the 1,200-token maximum. The runner stops before a request whose reservation could exceed the cumulative ceiling and performs no retries.

## Budget recommendation

Keep the benchmark project hard limit at USD 8 and the USD 4 alert. After the live run, replace the 2,000/300 planning assumptions with measured p50/p95 tokens and candidate frequency from non-trading replay. Do not approve a production monthly budget until those two measured quantities exist.
