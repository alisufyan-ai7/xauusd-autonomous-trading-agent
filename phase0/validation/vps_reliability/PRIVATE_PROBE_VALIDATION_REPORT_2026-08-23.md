# VPS private-probe package validation — 2026-08-23

Result: PASS, 14/14 tests: 7 existing reliability-oracle tests plus 7
private-probe tests. The existing corpus remains PASS for all 25 exact traces.

R20 removes the Linux-only `/tmp` override from private-probe test fixtures and
adds an AST regression check that rejects a hard-coded `/tmp` directory. Python
now selects its platform-native temporary directory on Windows and Linux.

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
