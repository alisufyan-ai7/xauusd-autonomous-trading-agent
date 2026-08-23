# XAUUSD private session-evidence verifier

This package validates an account-specific broker schedule and a hash-chained
set of read-only observations around declared close/reopen or holiday
boundaries. It handles IANA timezones, DST, overnight intervals and explicit
holiday overrides. Unknown, stale, contradictory or incomplete evidence fails
closed.

The frozen official source-host policy admits the current instrument-hours page
`https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours`
and the holiday-exceptions page
`https://get.exness.help/hc/en-us/articles/17923046759836-Holiday-trading-hours`.
These general official pages are authoritative publications but are not, by
themselves, proof of the selected terminal/account schedule. The schedule JSON
must preserve the fresh rendered account/instrument selection and raw artifact
SHA-256, and observations must independently corroborate it. Do not commit the
raw artifact, account details, screenshots or boundary observations. A broker
marketing page or inferred tick gap is not accepted as authoritative.

Run offline tests from the repository root:

```text
py -3.12 -m unittest -v phase0.validation.session_evidence.test_session_evidence
```

`run_private_boundary.ps1` is the optional capability-limited capture wrapper.
It attaches to the already-open terminal and appends one HMAC-redacted sample;
it cannot issue orders, select a symbol, log in or cause a session transition.
Run it only at a predeclared `BEFORE`, `INSIDE` or `AFTER` checkpoint. A complete
claim requires all three phases for each boundary and independent authoritative
schedule corroboration. The verifier also requires the complete predeclared
boundary-ID inventory, strict UTC chronology, stable redacted identity and
sequence/hash-chain continuity; one conveniently complete boundary cannot stand
in for omitted expected boundaries. External Python trading must remain disabled.
