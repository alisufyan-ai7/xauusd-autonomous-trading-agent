# Corrected live OpenAI Analyst benchmark evaluation

**Recorded:** 2026-08-23 UTC  
**Harness:** `analyst-benchmark-1.1`  
**Gate effect:** comparative model selection complete; Gate 0 remains incomplete  
**Trading authorization:** none

## Evidence boundary

The owner-returned `BENCHMARK_RESULTS_V1_1.json` has SHA-256
`73ade0c581a52e64ebd60c66fd2307ca3650aba48df1d82fabeb4732c8e840bc`.
The raw report is not published. This record contains only its hash, aggregate
measurements and non-content validation findings. It contains no prompt or
response text, credential, broker/account identifier, or execution capability.

Independent checks confirmed:

- valid JSON with schema `analyst-benchmark-1.1`;
- 48 live rows covering 16 cases for each of the three frozen candidates;
- two prohibited-data fixtures blocked locally at zero cost;
- `store:false`, `tools:[]`, valid response hashes and complete usage/latency;
- live row costs sum exactly to USD 0.1659360;
- cumulative cost is USD 0.3238708, below the USD 8 ceiling;
- all 16 Sol rows have every component check set to `true`.

## Results

| Candidate | Passed | Failed | Decision mismatches | Run cost | Median latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | 16/16 | 0 | 0 | USD 0.1059520 | 2945.0 ms | 5281.0 ms |
| GPT-5.6 Terra | 11/16 | 5 | 0 | USD 0.0536080 | 1797.0 ms | 3047.0 ms |
| GPT-5.6 Luna | 13/16 | 3 | 0 | USD 0.0063760 | 2265.5 ms | 16109.0 ms |

The matrix-level status is `FAIL` because the harness requires every evaluated
candidate to pass every case. That is appropriate for diagnostics but does not
mean the fully passing Sol candidate failed.

Terra failed exact proposal/geometry checks on BM-001, BM-003, BM-004 and
BM-005 and omitted the required reason on BM-010. Luna failed exact
proposal/geometry checks on BM-001, BM-004 and BM-005. Response content was
intentionally not retained, so no unsupported claim is made about the precise
alternative prices returned. Luna's unsafe event-lock proposal in the preserved
v1.0 run remains disqualifying despite its zero decision mismatches in v1.1.

## Decision

Select `gpt-5.6-sol` for the later, still non-trading Analyst integration stage.
Do not select Terra or Luna. Sol achieved the required zero unsafe approvals
and complete exact-output conformance on this frozen finite corpus. This is
necessary evidence, not proof of universal safety or strategy quality.

The official model page lists Structured Outputs support, Responses API
support and USD 4.00 input / USD 20.00 output per million tokens for Sol. It
does not currently expose a distinct dated Sol snapshot; the listed identifier
is `gpt-5.6-sol`. Freeze that identifier and the exact prompt/schema/config, and
require regression evaluation if OpenAI later exposes a new snapshot or changes
the serving version.

Source: https://developers.openai.com/api/docs/models/gpt-5.6-sol

No further API call is required or authorized by this completed benchmark.
Gate 0 remains incomplete because the Event Guard conformance, market-data
replay, full setup corpus, operational VPS/session evidence, exact Analyst field
contract and owner operational-policy choices remain open. External Python
trading stays disabled.
