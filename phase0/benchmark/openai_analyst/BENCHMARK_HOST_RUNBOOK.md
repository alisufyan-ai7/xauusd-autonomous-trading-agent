# Completed OpenAI benchmark host runbook

**Budget ceiling:** USD 8 (project alert USD 4)  
**Models:** GPT-5.6 Terra primary, Sol challenger, Luna cost baseline  
**Storage/tools:** `store:false`; `tools:[]`; no retries  
**Trading authorization:** none

**Completion:** The one approved v1.1 rerun completed on 2026-08-23. Do not
rerun it under this authorization. Preserve this file as the exact historical
procedure. Its cost values are stale runner estimates; see
`COST_ACCOUNTING_CORRECTION_2026-08-23.md` for the usage-based correction.

On the separately configured benchmark host, from this directory:

For the one approved v1.1 diagnostic rerun after the preserved v1.0 cost of USD 0.1579348:

```text
git pull --ff-only
python -m unittest -v test_benchmark.py
python benchmark_runner.py --budget 8 --prior-spend 0.1579348
python benchmark_runner.py --live --budget 8 --prior-spend 0.1579348
```

Do not echo, print, export to a file, paste, or pass `OPENAI_API_KEY` on the
command line. The runner reads it only from the environment and terminates
before any call if it is absent.

Expected output artifact: `BENCHMARK_RESULTS_V1_1.json`. Return that JSON for
independent verification. It contains no API key, prompt, response text,
broker/account identifier, or trading authority. Before accepting it, verify:

- all 48 live-eligible model/case calls are present and both prohibited-data
  cases are local blocks with zero cost;
- every request/result row maps to Terra, Sol, or Luna only;
- `prior_spend_usd` is USD 0.1579348 and cumulative estimated cost is at most USD 8;
- zero unsafe expected/observed mismatches;
- every component in each live row's `checks` object is `true`;
- response hashes, token usage and latency are populated;
- the report says `store:false` and `tools:[]`.

If the command stops for budget reservation, network error, refusal, invalid
schema, missing usage, or any failed case, preserve the partial console output
without rerunning automatically. A pass is advisory evidence only and cannot
enable external Python trading.

Observed result: report SHA-256
`73ade0c581a52e64ebd60c66fd2307ca3650aba48df1d82fabeb4732c8e840bc`,
historical runner-estimated cost USD 0.1659360 and cumulative estimate USD
0.3238708. The corrected current-list estimates are USD 0.244910 and USD
0.478069 respectively. Sol passed
16/16 and was selected for later non-trading Analyst integration tests. The raw
report is excluded from the repository.
