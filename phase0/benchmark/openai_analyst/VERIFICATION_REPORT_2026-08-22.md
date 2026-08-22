# OpenAI benchmark verification report

**Date:** 2026-08-22  
**Local result:** DRY PASS  
**Live result:** pending separate benchmark-host execution  
**Trading authorization:** none

Executed locally:

```text
python -m unittest -v test_benchmark.py
python benchmark_runner.py --budget 8
```

Results:

- 4/4 safety/configuration tests passed;
- 18 synthetic cases validated, of which two are local prohibited-data blocks;
- Terra, Sol and Luna are the only configured models;
- every live-eligible request is `store:false`, `tools:[]`, strict-schema, low
  reasoning effort, and capped at 1,200 output tokens;
- the owner reservation ceiling is USD 8 and there are no retries;
- current standard price constants are Terra USD 2/12, Sol USD 4/20 and Luna
  USD 0.20/1.20 per one million input/output tokens.

`OPENAI_API_KEY` is not present in this ChatGPT Work runtime. The credential is
configured only on the separate benchmark host, so no live API call, live cost,
or model result is claimed here. The approved host command is preserved in
`BENCHMARK_HOST_RUNBOOK.md`; the key must not be returned with the result.
