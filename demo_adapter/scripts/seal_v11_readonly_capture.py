"""Reproducibly seal offline-only v1.1 read-only collector sources.

No MT5 import, VPS access, broker action, or run-window approval. Output is
a portable source ZIP and exact component SHA manifest, NOT an executable permit.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

FILES = (
    "demo_adapter/scripts/v11_readonly_collector.py",
    "demo_adapter/scripts/v11_quote_coverage.py",
    "demo_adapter/scripts/v11_windows_readonly_host.py",
    "demo_adapter/scripts/v11_policy_a_source_bridge.py",
    "demo_adapter/scripts/v11_windows_readonly_capture.ps1",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data: dict[str, object]) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()


def seal(*, repo: Path, exact_head: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", exact_head) is None:
        raise ValueError("exact final reviewed GitHub head required")
    sources = {name: (repo / name).read_bytes() for name in FILES}
    for name, data in sources.items():
        if b"\r" in data:
            raise ValueError(f"CRLF or stray carriage return in component {name}")
    manifest = {
        "schema": "DEMO_V11_READ_ONLY_EXECUTION_OFF_BUNDLE_V1",
        "exact_git_head": exact_head,
        "classification": "DEMO_LIFECYCLE_ONLY_CAPTURE_SOURCE_NOT_ADMITTED",
        "mt5_broker_action_authorized": False,
        "mt5_external_python_trading_enable_authorized": False,
        "vps_capture_owner_approved": False,
        "run_registration_filled": False,
        "components": [
            {"path": name, "sha256": sha(sources[name]), "bytes": len(sources[name])}
            for name in sorted(sources)
        ],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted({**sources, "manifest.json": canonical(manifest)}.items()):
            zi = zipfile.ZipInfo(name, (2026, 10, 21, 0, 0, 0))
            zi.external_attr = 0o600 << 16
            zi.compress_type = zipfile.ZIP_STORED
            archive.writestr(zi, raw)
    return buf.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    zip_bytes = seal(repo=repo, exact_head=args.exact_head)
    if args.output.exists():
        raise ValueError("output already exists; do not overwrite sealed bundle")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as f:
        f.write(zip_bytes)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        manifest = z.read("manifest.json")
    print("V11_READONLY_EXECUTION_OFF_BUNDLE_SHA256=" + sha(zip_bytes))
    print("V11_READONLY_MANIFEST_SHA256=" + sha(manifest))
    print("V11_READONLY_HEAD=" + args.exact_head)
    print("V11_READONLY_CAPTURE_AUTHORIZED=False")
    print("V11_BROKER_ACTIONS_AUTHORIZED=False")


if __name__ == "__main__":
    main()
