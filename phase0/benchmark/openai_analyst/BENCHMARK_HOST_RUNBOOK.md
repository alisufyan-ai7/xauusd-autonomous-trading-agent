# Approved OpenAI benchmark host runbook

**Budget ceiling:** USD 8 (project alert USD 4)  
**Models:** GPT-5.6 Terra primary, Sol challenger, Luna cost baseline  
**Storage/tools:** `store:false`; `tools:[]`; no retries  
**Trading authorization:** none

On the separately configured benchmark host, from this directory:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py --live --budget 8
```

Do not echo, print, export to a file, paste, or pass `OPENAI_API_KEY` on the
command line. The runner reads it only from the environment and terminates
before any call if it is absent.

Expected output artifact: `BENCHMARK_RESULTS.json`. Return that JSON for
independent verification. It contains no API key, prompt, response text,
broker/account identifier, or trading authority. Before accepting it, verify:

- all 48 live-eligible model/case calls are present and both prohibited-data
  cases are local blocks with zero cost;
- every request/result row maps to Terra, Sol, or Luna only;
- cumulative estimated cost is at most USD 8;
- zero unsafe expected/observed mismatches;
- response hashes, token usage and latency are populated;
- the report says `store:false` and `tools:[]`.

If the command stops for budget reservation, network error, refusal, invalid
schema, missing usage, or any failed case, preserve the partial console output
without rerunning automatically. A pass is advisory evidence only and cannot
enable external Python trading.
