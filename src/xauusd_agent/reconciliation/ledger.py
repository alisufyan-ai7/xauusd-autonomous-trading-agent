"""Immutable, hash-chained exposure reconciliation ledger."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .exposure import (
    ExpectedExposure,
    ExposureReconciliation,
    ReconciliationDisposition,
    ReconciliationStatus,
)

GENESIS_HASH = "0" * 64


def _exposure_object(item: ExpectedExposure) -> dict[str, str]:
    return {
        "exposure_id": item.exposure_id,
        "kind": item.kind,
        "side": item.side,
        "symbol": item.symbol,
        "volume_lots": str(item.volume_lots),
    }


@dataclass(frozen=True, slots=True)
class ExposureLedgerEntry:
    sequence: int
    observed_at_utc: str
    broker_fingerprint_sha256: str
    status: str
    disposition: str
    reason_codes: tuple[str, ...]
    expected: tuple[ExpectedExposure, ...]
    observed: tuple[ExpectedExposure, ...]
    previous_entry_sha256: str
    entry_sha256: str


@dataclass(frozen=True, slots=True)
class ExposureLedger:
    """Functional ledger: recording produces a new ledger, never edits history."""

    entries: tuple[ExposureLedgerEntry, ...] = ()

    @property
    def head_sha256(self) -> str:
        return self.entries[-1].entry_sha256 if self.entries else GENESIS_HASH

    def record(
        self,
        *,
        observed_at_utc: str,
        broker_fingerprint_sha256: str,
        reconciliation: ExposureReconciliation,
    ) -> ExposureLedger:
        if not observed_at_utc:
            raise ValueError("observed_at_utc is required")
        if len(broker_fingerprint_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in broker_fingerprint_sha256
        ):
            raise ValueError("broker fingerprint must be lowercase SHA-256")

        sequence = len(self.entries) + 1
        previous_hash = self.head_sha256
        payload = {
            "broker_fingerprint_sha256": broker_fingerprint_sha256,
            "disposition": reconciliation.disposition.value,
            "expected": [_exposure_object(item) for item in reconciliation.expected],
            "observed": [_exposure_object(item) for item in reconciliation.observed],
            "observed_at_utc": observed_at_utc,
            "previous_entry_sha256": previous_hash,
            "reason_codes": list(reconciliation.reason_codes),
            "sequence": sequence,
            "status": reconciliation.status.value,
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        entry_hash = hashlib.sha256(canonical).hexdigest()
        entry = ExposureLedgerEntry(
            sequence=sequence,
            observed_at_utc=observed_at_utc,
            broker_fingerprint_sha256=broker_fingerprint_sha256,
            status=reconciliation.status.value,
            disposition=reconciliation.disposition.value,
            reason_codes=reconciliation.reason_codes,
            expected=reconciliation.expected,
            observed=reconciliation.observed,
            previous_entry_sha256=previous_hash,
            entry_sha256=entry_hash,
        )
        return ExposureLedger(entries=(*self.entries, entry))

    def verify(self) -> bool:
        rebuilt = ExposureLedger()
        try:
            for entry in self.entries:
                reconciliation = ExposureReconciliation(
                    status=ReconciliationStatus(entry.status),
                    disposition=ReconciliationDisposition(entry.disposition),
                    reason_codes=entry.reason_codes,
                    expected=entry.expected,
                    observed=entry.observed,
                )
                rebuilt = rebuilt.record(
                    observed_at_utc=entry.observed_at_utc,
                    broker_fingerprint_sha256=entry.broker_fingerprint_sha256,
                    reconciliation=reconciliation,
                )
                if rebuilt.entries[-1] != entry:
                    return False
        except (KeyError, TypeError, ValueError):
            return False
        return True
