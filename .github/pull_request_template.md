## One coherent feature / production outcome

Describe a single acceptance-ready feature or one inseparable safety-bound release slice. Continue an existing feature's open PR instead of creating an unnecessary stacked successor.

## Branch, code and scope

- Accepted `main` SHA:
- Proposed exact PR HEAD SHA:
- Changed implementation files/tests:
- Explicitly excluded actions or files:
- Why stacking is necessary (normally **not allowed**):

## Governance checks

- [ ] Decision Log history was not rewritten; historic Gate 0 failures remain failures.
- [ ] Gate status and authorization boundary are consistent with accepted `GOVERNANCE.md`.
- [ ] No raw sensitive evidence or secrets are included.
- [ ] JSON, hashes, and collector verification pass where applicable.
- [ ] New or changed artifacts have explicit versions and SHA-256 values.

## Broker trading controls, when applicable

- [ ] No LIVE real-money trading is enabled or automatically promoted.
- [ ] Genuine Exness MT5 DEMO broker orders are distinguished from synthetic/test fills.
- [ ] Frozen full Policy A, exact DEMO fingerprint and admitted cost/source gates are enforced.
- [ ] The sole existing S2 order path stays execution-blocked until separately admitted and reviewed.
- [ ] No ambiguous broker-order result causes a duplicate retry or unknown-position closure.
- [ ] End-to-end native Windows/Ubuntu, real broker VPS and recovery/alert evidence attached as required.

## Merge and documentation

- [ ] Exact current PR HEAD and `main` SHA were reverified before requesting merge.
- [ ] Native CI and historical failure evidence are linked, not overwritten.
- [ ] Existing human and JSON states and canonical handoff updated if their facts changed.
- [ ] Superseded PRs were closed with archive-ref SHA and retained evidence.
- [ ] The owner has expressly approved the exact merge; no broker action or VPS deployment is implied.

See [the proposed PR lifecycle policy](../phase0/governance/PR_LIFECYCLE_POLICY_2026-10-23.md) and [real broker DEMO critical path](../phase0/roadmap/REAL_BROKER_DEMO_TO_TINY_LIVE_CRITICAL_PATH_2026-10-23.md).
