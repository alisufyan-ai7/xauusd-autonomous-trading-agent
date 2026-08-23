# Selected Sol Analyst runtime contract

This package freezes the non-trading `gpt-5.6-sol` request profile, exact
five-family minimized field register, strict output schema, freshness/timeouts,
price reservation and provider-change revalidation policy.

Official OpenAI documentation confirms that Sol supports the Responses API,
Structured Outputs and configurable low reasoning effort:
https://developers.openai.com/api/docs/models/gpt-5.6-sol

The Responses reference defines `store`, `tools`, `max_output_tokens`, strict
JSON Schema output and disabled truncation behavior:
https://developers.openai.com/api/reference/cli/resources/responses/methods/create

Run offline from this directory:

```text
python -m unittest -v test_runtime_contract.py
```

The oracle constructs but never sends a request. It has no broker, order,
credential, network or process capability. A 14/14 pass is specification
evidence only; `live_calls_authorized` and `trading_authorized` remain false.
