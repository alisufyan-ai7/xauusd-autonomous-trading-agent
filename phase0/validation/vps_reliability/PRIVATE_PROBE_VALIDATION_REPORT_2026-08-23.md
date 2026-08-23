# VPS private-probe package validation — 2026-08-23

Result: PASS, 13/13 tests: 7 existing reliability-oracle tests plus 6 new
private-probe tests. The existing corpus remains PASS for all 25 exact traces.

Covered: append-only record hashing, HMAC-redacted identity, private-path
enforcement, baseline/outage/reconnect/Python/MT5/Windows/clock/build event
inventory, Windows boot change, Windows Time status hash, healthy reconnect,
identity drift, build revalidation and static absence of order/process-control
capability. It also rejects duplicate/unknown events, duplicate scenario IDs,
non-baseline-first chains, invalid or non-increasing timestamps, missing
identity/process tokens, malformed compatibility hashes and an unproven
external-Python barrier during disconnect. The wrapper observes but never
causes a fault or restart.

Operational evidence remains pending: genuine controlled observations for all
eight events. A synthetic full-matrix test does not prove VPS behavior and is
not trading authorization.
