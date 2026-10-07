# OpenAI Analyst Benchmark Verification

**Date:** 2026-08-12  
**Status:** DRY PASS; live benchmark not run  
**Live cost incurred:** USD 0.00

## Frozen configuration

- Models: `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-5.6-luna`.
- Responses API; synchronous; `store:false`; `tools:[]`.
- Strict Structured Outputs; reasoning effort `low`; maximum output 1,200 tokens.
- Cumulative owner ceiling USD 10. The runner conservatively reserves worst-case input/output cost before each call and has no retries.
- 18 continuous fixtures BM-001 through BM-018: five clear synthetic candidates, eleven model safety/no-trade cases, and two prohibited-data local-block cases that must never be transmitted.

## Objective dry result

- Unit tests: 3/3 PASS.
- Schema/case/prompt parse and continuity: PASS.
- Every live-eligible request explicitly has `store:false`, empty tools, and bounded output: PASS.
- Every transmitted synthetic payload is free of the registered broker/account identifier fields: PASS.
- Both prohibited-data fixtures are caught locally: PASS.
- Dry runner: `DRY_PASS`, 18 cases, 2 local blocks, USD 10 maximum.
- Environment credential check: `OPENAI_API_KEY` absent; no request was sent.

## Controlled hashes

```text
af2ef7d853c08248baf6cae0c8558ec249e13fb983425758b7aaf38acf211fad  README.md
0012a25c7c6c683c4e1a7f242c80ec2b8a72234e1ea860401cf380df828f1901  analyst_output_schema.json
cdd6ce6415573c53f4900f0fdc5f0ff5e15f6c693e634700fbd2444e2b3b9dad  benchmark_cases.json
48bd09151d0ca7fadcf0b0b54babd2cc6b05c3c925acd5d8f705fcc6effbbc67  benchmark_runner.py
cf95fe258402c264333fa4ebb3527ded755ee671e29d91e9b76f4863a0192b37  system_prompt.txt
7250685141c737ec2a4918304c228eb17c8dfbbe0fe9a2523e7db65639ca08fb  test_benchmark.py
```

## Gate effect

The machine-readable benchmark package is ready. Gate 0 remains incomplete until the exact frozen candidate is executed through the separate approved API project and achieves zero unsafe approvals plus the required quality, latency, token and cost measurements. A passing finite benchmark cannot authorize trading.
