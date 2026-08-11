# XAU/USD Autonomous Trading Agent

Private governance and validation repository for the XAU/USD Autonomous Trading Agent.

## Current status

**Gate 0 is incomplete. Production implementation and trading-capable operations are prohibited.**

The canonical Phase 0 dossier is `phase0/PHASE_0_SPECIFICATION.md`. The append-only decision history is `phase0/DECISION_LOG.md`. Evidence binaries and sensitive account/legal records are not stored here; their approved hashes and provenance are recorded in the evidence model and reviews.

## Repository layout

- `phase0/`: canonical specification, decisions, evidence metadata/reviews, blockers, risk proposal, and verification report.
- `tools/readonly-evidence-collector/`: accepted read-only collector v0.1.1 source, runner, lock, manifest, and tests.
- `policies/`: document and evidence handling rules.
- `.github/workflows/`: automated record and collector validation.

The tag `phase0-v0.6` identifies the initial GitHub migration baseline. It is a documentation/evidence checkpoint, not Gate 0 approval.
