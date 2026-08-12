# Draft 1.0 Risk/Analyst offline validation

Run from the repository root:

```bash
python -m unittest -v phase0.tests.test_risk_analyst_corpora
```

The suite transcribes all 52 `RG-*` and 35 `AI-*` normative vectors from the
Draft 1.0 specifications. It is deterministic, standard-library-only, and has
no broker, network, OpenAI, credential, order, or trading capability.

Passing this suite means the executable transcription agrees with the written
expected outcomes. It does **not** close the specifications' enumerated open
dependencies, validate a final Analyst JSON Schema, benchmark a model, or
authorize demo/real trading.
