# OpenAI Analyst Gate 0 Benchmark v1.1

This is a synthetic, advisory-only benchmark. It cannot connect to MT5, read account data, use tools, calculate volume, or execute a trade.

Frozen candidates: GPT-5.6 Terra primary, GPT-5.6 Sol challenger, GPT-5.6 Luna cost baseline. Every request is synchronous, stateless (`store:false`), tool-free (`tools:[]`), strict Structured Output, low reasoning effort, and capped at 1,200 output tokens. Two prohibited-data fixtures must be rejected locally and never transmitted.

The runner reserves conservative worst-case cost before each request and stops before any call that could exceed the owner-approved cumulative USD 8 ceiling. `--prior-spend` carries earlier benchmark cost into that cumulative check. There are no retries.

Version 1.1 makes the injection rule explicitly fail-closed, requires the expected reason code and exact copied proposal fields, and records separate non-content booleans for decision, identifiers, exact proposal, geometry and reason. This fixes v1.0's opaque composite `pass` flag without storing model response text.

Dry verification:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py
```

Live execution is authorized only on the separately configured benchmark host, where `OPENAI_API_KEY` is supplied through a secure environment mechanism. Never print it, paste it into chat, pass it as a command-line argument, or commit it. Run from this directory on that host:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py --live --budget 8 --prior-spend 0
```

The runner writes only decision metadata, component-check booleans, token usage, latency, estimated cost, and a SHA-256 of each parsed response. It does not persist response text. The API request sets `store:false` and `tools:[]` for every call. The default output is `BENCHMARK_RESULTS_V1_1.json`, so the original v1.0 evidence is not overwritten.

Zero unsafe approvals is necessary but not proof of universal safety. A green benchmark cannot authorize trading.
