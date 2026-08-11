# XAU/USD Autonomous Trading Agent

Private governance and validation repository for the XAU/USD Autonomous Trading Agent.

## Current status

**Gate 0 is incomplete. Production implementation and trading-capable operations are prohibited. External Python trading remains disabled.**

The canonical Phase 0 dossier is `phase0/PHASE_0_SPECIFICATION.md`. The append-only decision history is `phase0/DECISION_LOG.md`. Evidence binaries and sensitive account/legal records are not stored here; their approved hashes and provenance are recorded in the evidence model and reviews.

## Repository layout

- `phase0/`: canonical specification, decisions, evidence metadata/reviews, blockers, approved Policy A record, and verification report.
- `phase0/specifications/`: candidate technical contracts for risk, Analyst minimization, setup families, execution/reconciliation, read-only diagnostics, news protection, and replay research.
- `tools/readonly-evidence-collector/`: accepted read-only collector v0.1.1 source, runner, lock, manifest, and tests.
- `policies/`: document and evidence handling rules.
- `.github/workflows/`: automated record and collector validation.

Current controlled revision: **Phase 0 Draft 0.9**, Decision Log through D-0052. Exness/API investigation is sufficiently complete for Phase 0 under the owner-accepted residual ambiguity and mandatory data-minimization architecture. This does not state that Exness approved external OpenAI processing.
