# OpenAI benchmark verification report

**Date:** 2026-08-22  
**Local result:** v1.1 DRY PASS  
**Live result:** v1.0 FAIL preserved; v1.1 diagnostic rerun pending  
**Trading authorization:** none

Executed locally:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py --budget 8 --prior-spend 0.1579348
```

Results:

- 6/6 safety/configuration/diagnostic tests passed;
- 18 synthetic cases validated, of which two are local prohibited-data blocks;
- Terra, Sol and Luna are the only configured models;
- every live-eligible request is `store:false`, `tools:[]`, strict-schema, low
  reasoning effort, and capped at 1,200 output tokens;
- the owner reservation ceiling is USD 8 and there are no retries;
- the then-frozen price constants were later found stale. They are corrected to
  Terra USD 2.50/15, Sol USD 5/30 and Luna USD 1/6 per million input/output
  tokens in `COST_ACCOUNTING_CORRECTION_2026-08-23.md`.

The first live v1.0 run is independently recorded by SHA-256 and aggregate
metrics in `FIRST_LIVE_BENCHMARK_EVALUATION_2026-08-22.md`. Its raw JSON is not
published. Version 1.1 preserves that evidence, historically carries its USD
0.1579348 runner estimate forward, and adds component diagnostics plus an explicit fail-closed injection
rule. The credential remains only on the separate benchmark host.
