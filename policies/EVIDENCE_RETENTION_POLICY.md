# Evidence Retention Policy

- Store raw evidence in a restricted encrypted vault with versioning, MFA, and independent backup.
- Store only the evidence ID, classification, provenance, SHA-256, redaction state, storage reference, and accepting decision in Git.
- Verify evidence hashes before review and again when retrieved.
- Never infer legal applicability from storage or possession of a document.
- Retain superseded evidence metadata for audit history; record withdrawals and replacements append-only.
