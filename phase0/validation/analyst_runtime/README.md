# Selected Sol Analyst runtime contract

This package freezes the non-trading `gpt-5.6-sol` request profile, exact
five-family minimized field register, strict output schema, freshness/timeouts,
price reservation, production system prompt, chronological acceptance oracle
and provider-change revalidation policy.

The offline replay-sequence layer directly re-runs byte-level H4/H1/M15 bundle
admission and binds synthetic five-family chronological snapshots to its
separately expected root; a caller-supplied `ADMITTED` label is not accepted. It requires expected positive
and fail-closed negative outcomes, carries consumed-snapshot state between cases,
and proves duplicate analysis/snapshot identities cannot be reused.

Official OpenAI documentation confirms that Sol supports the Responses API,
Structured Outputs and configurable low reasoning effort:
https://developers.openai.com/api/docs/models/gpt-5.6-sol

The Responses reference defines `store`, `tools`, `max_output_tokens`, strict
JSON Schema output and disabled truncation behavior:
https://developers.openai.com/api/reference/cli/resources/responses/methods/create

The provider data-controls documentation is the authority for endpoint storage
behavior. The frozen request always sets `store:false`:
https://developers.openai.com/api/docs/guides/your-data#default-usage-policies-by-endpoint

The current Sol model page publishes the temporary USD 4/M input and USD 20/M
output standard price window through 2026-11-21. The profile requires price
revalidation no later than that date. Historical benchmark accounting is not
changed by this runtime reservation update.

Run offline from this directory:

```text
python -m unittest -v test_runtime_contract.py test_replay_sequence_oracle.py
```

The oracle constructs but never sends a request. It has no broker, order,
credential, network or process capability. It rejects duplicate JSON keys,
extra or missing fields, wrong IDs, invented prices/evidence, late responses,
in-flight state changes and snapshot replay. A 27/27 pass is specification
evidence only; every chronological result fixes `trading_authorized` to false,
and `live_calls_authorized` remains false.
