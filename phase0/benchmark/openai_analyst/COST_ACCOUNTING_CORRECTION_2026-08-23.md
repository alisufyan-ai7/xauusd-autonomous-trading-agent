# OpenAI benchmark cost-accounting correction

**Recorded:** 2026-08-23 UTC  
**Scope:** cost estimate only; model-selection findings unchanged  
**Additional API calls:** none

The benchmark runner labeled its locally calculated usage estimate as “actual
cost” and used a stale price table. The raw reports and their SHA-256 hashes are
preserved unchanged. Provider billing remains authoritative.

Using the official standard list-price table verified on 2026-08-23—Terra
USD 2.50/15.00, Sol USD 5.00/30.00 and Luna USD 1.00/6.00 per million
input/output tokens—the preserved usage counters recompute as follows:

| Preserved run | Terra | Sol | Luna | Corrected list-price estimate |
|---|---:|---:|---:|---:|
| v1.0 | USD 0.063305 | USD 0.140140 | USD 0.029714 | **USD 0.233159** |
| v1.1 | USD 0.067010 | USD 0.146020 | USD 0.031880 | **USD 0.244910** |
| Cumulative |  |  |  | **USD 0.478069** |

Token counts used in the recomputation:

| Run/model | Input tokens | Output tokens |
|---|---:|---:|
| v1.0 Terra | 11,882 | 2,240 |
| v1.0 Sol | 11,882 | 2,691 |
| v1.0 Luna | 11,882 | 2,972 |
| v1.1 Terra | 12,908 | 2,316 |
| v1.1 Sol | 12,908 | 2,716 |
| v1.1 Luna | 12,908 | 3,162 |

The corrected cumulative estimate remains far below the owner’s USD 8 ceiling.
It does not authorize another call. Sol’s 16/16 v1.1 conformance result and the
selection decision remain unchanged because pricing does not affect any safety,
geometry, reason, identifier or decision check.
