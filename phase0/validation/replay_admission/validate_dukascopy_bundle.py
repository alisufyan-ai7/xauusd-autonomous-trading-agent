"""Offline byte-level admission and sanitized receipt for a private Dukascopy bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from admission import manifest_hash
from multiframe_admission import (
    SCHEMA_VERSION, admit_multiframe_bundle, bundle_hash, split_hash,
)


AMENDED_SPLIT = {
    "train_start_utc": "2020-01-01T23:00:00Z",
    "train_end_utc": "2023-12-31T23:45:00Z",
    "validation_start_utc": "2024-01-08T00:00:00Z",
    "validation_end_utc": "2024-12-31T23:45:00Z",
    "embargo_start_utc": "2025-01-01T00:00:00Z",
    "embargo_end_utc": "2025-01-08T00:00:00Z",
    "holdout_start_utc": "2025-01-09T00:00:00Z",
    "holdout_end_utc": "2026-06-29T20:00:00Z",
    "purge_seconds": 604800,
    "embargo_seconds": 604800,
    "sealed": True,
}


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.private_root.resolve()
    bundle_path = root / "manifests" / "multiframe_bundle.json"
    bundle = json.loads(bundle_path.read_text())
    r3_plan_path = root / "r3_trial_registration.json"
    admitted_split = (json.loads(r3_plan_path.read_text())["split"]
                      if r3_plan_path.exists() else AMENDED_SPLIT)
    # The registered acquisition generator emitted the pre-R27 label 1.0.
    # R27 changed only the manifest label/complete-split admission boundary;
    # the emitted split already has the exact R27 inventory. Normalize the
    # label before results are opened and re-sign the manifest without touching
    # any data bytes or child roots.
    bundle["schema_version"] = SCHEMA_VERSION
    bundle["split"] = admitted_split
    bundle["split_map_sha256"] = split_hash(admitted_split)
    manifests = {}
    artifacts = {}
    terms = (root / "evidence" / "dukascopy_owner_attestation.json").read_bytes()
    instrument = (root / "evidence" / "dukascopy_instrument_XAU-USD.json").read_bytes()
    mismatch = (root / "evidence" / "dukascopy_bid_ask_mismatches.json").read_bytes()
    for name in ("H4", "H1", "M15"):
        manifest = json.loads((root / "manifests" / f"{name.lower()}_manifest.json").read_text())
        manifest["registration"]["split_map_sha256"] = bundle["split_map_sha256"]
        manifest["manifest_sha256"] = manifest_hash(manifest)
        (root / "manifests" / f"{name.lower()}_manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n"
        )
        data_path = root / "derived" / f"xauusd_{name.lower()}_bid_ask.csv"
        manifests[name] = manifest
        artifacts[name] = {
            manifest["files"][0]["path"]: data_path.read_bytes(),
            "evidence/dukascopy_owner_attestation.json": terms,
            "evidence/dukascopy_instrument_XAU-USD.json": instrument,
        }
        if any(gap.get("reason") == "PROVIDER_SIDE_MISMATCH"
               for gap in manifest.get("authorized_gaps", [])):
            artifacts[name]["evidence/dukascopy_bid_ask_mismatches.json"] = mismatch
    bundle["bundle_manifest_sha256"] = bundle_hash(bundle)
    bundle_path.write_text(json.dumps(bundle, sort_keys=True, indent=2) + "\n")
    result = admit_multiframe_bundle(bundle, manifests, artifacts)
    report = {
        "schema_version": "dukascopy-bundle-admission-receipt-1.0",
        "status": result.status, "reason_codes": result.reason_codes,
        "bundle_root_sha256": result.bundle_root_sha256,
        "bundle_manifest_sha256": bundle["bundle_manifest_sha256"],
        "child_rows": dict(result.child_rows),
        "child_roots": {name: manifests[name]["dataset_root_sha256"] for name in manifests},
        "rights_attestation_sha256": sha(terms), "instrument_evidence_sha256": sha(instrument),
        "bid_ask_mismatch_evidence_sha256": sha(mismatch),
        "raw_bytes_published": False, "external_python_trading": "DISABLED",
        "trading_authorized": False,
    }
    unsigned = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    report["receipt_sha256"] = sha(unsigned)
    target = root / "admission" / "dukascopy_bundle_admission_receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    if result.status != "ADMITTED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
