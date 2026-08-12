# OpenAI Analyst Gate 0 Benchmark

This is a synthetic, advisory-only benchmark. It cannot connect to MT5, read account data, use tools, calculate volume, or execute a trade.

Frozen candidates: GPT-5.6 Terra primary, GPT-5.6 Sol challenger, GPT-5.6 Luna cost baseline. Every request is synchronous, stateless (`store:false`), tool-free (`tools:[]`), strict Structured Output, low reasoning effort, and capped at 1,200 output tokens. Two prohibited-data fixtures must be rejected locally and never transmitted.

The runner reserves conservative worst-case cost before each request and stops before any call that could exceed the owner-approved cumulative USD 10 ceiling. There are no retries.

Dry verification:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py
```

Live execution is prohibited until a separate OpenAI API project/key is configured through a secure environment mechanism. Never paste a key into chat or commit it. Once configured:

```text
python benchmark_runner.py --live --budget 10
```

Zero unsafe approvals is necessary but not proof of universal safety. A green benchmark cannot authorize trading.
