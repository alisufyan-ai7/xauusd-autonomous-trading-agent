# OpenAI Analyst Gate 0 Benchmark v1.1

This is a synthetic, advisory-only benchmark. It cannot connect to MT5, read account data, use tools, calculate volume, or execute a trade.

Frozen evaluation candidates were GPT-5.6 Terra primary, GPT-5.6 Sol challenger, and GPT-5.6 Luna cost baseline. Every request is synchronous, stateless (`store:false`), tool-free (`tools:[]`), strict Structured Output, low reasoning effort, and capped at 1,200 output tokens. Two prohibited-data fixtures must be rejected locally and never transmitted.

The runner reserves conservative worst-case cost before each request and stops before any call that could exceed the owner-approved cumulative USD 8 ceiling. `--prior-spend` carries earlier benchmark cost into that cumulative check. There are no retries.

Version 1.1 makes the injection rule explicitly fail-closed, requires the expected reason code and exact copied proposal fields, and records separate non-content booleans for decision, identifiers, exact proposal, geometry and reason. This fixes v1.0's opaque composite `pass` flag without storing model response text.

Dry verification:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py
```

## Completed live evaluation

The approved v1.1 run completed on 2026-08-23. Its report SHA-256 is
`73ade0c581a52e64ebd60c66fd2307ca3650aba48df1d82fabeb4732c8e840bc`.
GPT-5.6 Sol passed 16/16 live cases and is the selected Analyst candidate for
later non-trading integration tests. Terra passed 11/16 and Luna 13/16; neither
is selected. The matrix-level report is `FAIL` because it required every
candidate to pass every check, not because Sol failed.

The two runs cost USD 0.3238708 cumulatively. No further live benchmark call is
authorized by the completed-run approval. Preserve both raw reports only in
the owner's controlled evidence location; do not commit them.

Historical operator commands were:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py --live --budget 8 --prior-spend 0.1579348
```

The runner writes only decision metadata, component-check booleans, token usage, latency, estimated cost, and a SHA-256 of each parsed response. It does not persist response text. The API request sets `store:false` and `tools:[]` for every call. The default output is `BENCHMARK_RESULTS_V1_1.json`, so the original v1.0 evidence is not overwritten.

Never print, paste, export, or commit `OPENAI_API_KEY`. Zero unsafe approvals is
necessary but not proof of universal safety. The Sol result permits only later
gated non-trading work and cannot authorize trading.
