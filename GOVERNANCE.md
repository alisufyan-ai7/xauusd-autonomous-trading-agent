# Repository Governance

1. `main` is the authoritative accepted project record.
2. Decision Log entries are append-only. Corrections and supersessions require a new decision ID.
3. Gate status, authorization boundaries, and artifact hashes must remain consistent across canonical records.
4. Raw sensitive evidence, credentials, account identifiers, identity documents, and unredacted legal/account materials must not be committed.
5. Released artifacts are byte-exact and identified by version, Git commit, and SHA-256.
6. A release or tag is a documentation checkpoint unless an explicit accepted decision says otherwise.
7. No production deployment or trading-capable implementation may originate from this repository while Gate 0 is incomplete.
