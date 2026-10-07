# Repository Governance

1. `main` is the authoritative accepted project record.
2. Decision Log entries are append-only. Corrections and supersessions require a new decision ID.
3. Gate status, authorization boundaries, and artifact hashes must remain consistent across canonical records.
4. Raw sensitive evidence, credentials, account identifiers, identity documents, and unredacted legal/account materials must not be committed.
5. Released artifacts are byte-exact and identified by version, Git commit, and SHA-256.
6. A release or tag is a documentation checkpoint unless an explicit accepted decision says otherwise.
7. While Gate 0 is incomplete, this repository may contain and validate only the APC-A production candidate authorized by D-0128: it must remain execution-disabled, contain no live order capability, and default to a null broker sink. Publication, external calls, VPS deployment, disruption, demo execution and live execution retain their separate approval gates.
8. No unresolved Gate 0 requirement is waived or reclassified by software construction, shadow operation or demo preparation. Real-money capability and activation remain prohibited until Real-Money Risk Admission passes and TINY-LIVE is explicitly approved.
