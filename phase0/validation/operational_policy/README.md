# Operational Policy Offline Oracle

Pure standard-library validation for the owner-approved
`V1 + M1 + E1 + P1 + A1` specification/testing bundle. It cannot import MT5,
send network/messages, read credentials, or emit broker actions.

Run from the repository root:

```text
python -m unittest -v phase0.validation.operational_policy.test_operational_policy
```

The oracle checks exact volume and margin boundaries, the 2.0x incremental
margin stress, adverse equity stresses, fail-closed invalid inputs, M1
subordination, human-only emergency action, human-gated resumption, dual-path
alert timing, and absence of broker/network/messaging capability.

A passing test suite is specification evidence only. It does not validate an
MT5 implementation, deliver an alert, authorize a trade, or enable external
Python trading.
