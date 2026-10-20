"""Prospective APC-only isolated staged-wheel loader. Does not grant broker authority.

--mode verify never imports MetaTrader5. Entry/close are unapproved until
a NEW explicit owner APC-DEMO-CANARY authorization binds an exact script SHA.
Run only with -B -I; this source is not part of the frozen PR23 artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import runpy
import sqlite3
import sys
import zipfile

EXPECTED_HEAD = "e32f6dda35b2f29f2f5c0d762d0d26846bc5f384"
EXPECTED_INNER = "61535b668da13605d62a00517bc76cc6b4b918eab1db769b001e64b1bfa241a5"
EXPECTED_MANIFEST = "03886c4afd8a2716f7c5d2d59aaa6fe535d4d5af0c97745da681c46839d4eed3"
EXPECTED_OPERATOR = "002f4ad5d3ed372026172b99a2dcfd6ca293196a2b9dfb0f1b6c7f2b503a776f"
ROOT_NAME = "XAUUSD-APC-DEMO-CANARY"
EXPECTED_FILES = {
    "source/demo_adapter/scripts/apc-demo-canary-readonly-preflight.ps1":
        "11db0ba0877f29ddf62ff0b626dc060d80393176f79d97f7e8dca32f20154519",
    "source/demo_adapter/scripts/apc_demo_canary_attended_operator.py":
        EXPECTED_OPERATOR,
    "source/demo_adapter/scripts/apc_demo_canary_readonly_preflight.py":
        "484348e154e3072192b9a4b1fa8031b457355e6c46035bc1696ee22afcfabfc6",
    "wheel/xauusd_demo_adapter-0.1.0.dev0-py3-none-any.whl":
        "699b3a47c42bb57c875dfa1342a01546d68cd253de31a7af74d146c85d130980",
    "wheel/xauusd_production_candidate-0.1.0.dev0-py3-none-any.whl":
        "2000b2ae1af7a0a252bb25d11ab19381c728310f6b3fe5b2b35b8b179abe89aa",
}
APC_TOKEN = "APC-DEMO-CANARY-ONE-ENTRY-ONE-CLOSE"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_stage(root: pathlib.Path, mode: str) -> tuple[pathlib.Path, pathlib.Path]:
    if not root.is_dir() or root.name != ROOT_NAME:
        raise RuntimeError("CANARY_ISOLATED_STAGE_MISSING")
    inner = (root / "sealed.zip").read_bytes()
    if digest(inner) != EXPECTED_INNER:
        raise RuntimeError("CANARY_STAGED_SEALED_SHA_MISMATCH")
    manifest = (root / "manifest.json").read_bytes()
    if digest(manifest) != EXPECTED_MANIFEST:
        raise RuntimeError("CANARY_STAGED_MANIFEST_SHA_MISMATCH")
    obj = json.loads(manifest)
    if obj.get("exact_git_head") != EXPECTED_HEAD:
        raise RuntimeError("CANARY_STAGED_GITHUB_HEAD_MISMATCH")
    if {(x["path"], x["sha256"]) for x in obj["source_files"]} != set(EXPECTED_FILES.items()):
        raise RuntimeError("CANARY_STAGED_COMPONENT_MANIFEST_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(inner)) as sealed:
        if set(sealed.namelist()) != set(EXPECTED_FILES) | {"manifest.json"}:
            raise RuntimeError("CANARY_STAGED_ARCHIVE_ENTRY_MISMATCH")
        if sealed.read("manifest.json") != manifest:
            raise RuntimeError("CANARY_STAGED_MANIFEST_BYTES_MISMATCH")
        for name, expected_sha in EXPECTED_FILES.items():
            source = sealed.read(name)
            if digest(source) != expected_sha:
                raise RuntimeError("CANARY_STAGED_COMPONENT_SHA_MISMATCH")
            folder = "wheels" if name.startswith("wheel/") else "sources"
            disk = root / folder / name.split("/")[-1]
            if disk.is_symlink() or disk.read_bytes() != source:
                raise RuntimeError("CANARY_STAGED_DISK_SOURCE_MISMATCH")
            if name.startswith("wheel/"):
                with zipfile.ZipFile(io.BytesIO(source)) as wheel:
                    for member in wheel.namelist():
                        f = root / "site" / member
                        if f.is_symlink() or not f.is_file() or f.read_bytes() != wheel.read(member):
                            raise RuntimeError("CANARY_STAGED_SITE_FILE_MISMATCH")
    evidence = json.loads((root / "staging_evidence.json").read_text(encoding="utf-8"))
    if (evidence.get("control"), evidence.get("canary_journal"),
            evidence.get("sealed_sha256")) != ("KILLED", "UNUSED", EXPECTED_INNER):
        raise RuntimeError("CANARY_STAGED_EVIDENCE_MISMATCH")
    control = root / "control.sqlite3"
    journal = root / "canary.sqlite3"
    if not control.is_file() or not journal.is_file():
        raise RuntimeError("CANARY_STAGED_SQLITE_MISSING")
    with sqlite3.connect(f"file:{control.as_posix()}?mode=ro", uri=True) as db:
        crows = db.execute("SELECT state FROM demo_control WHERE singleton_id=1").fetchall()
    with sqlite3.connect(f"file:{journal.as_posix()}?mode=ro", uri=True) as db:
        jrows = db.execute("SELECT stage FROM canary WHERE id=1").fetchall()
    admitted = ((crows == [("KILLED",)] and jrows == []) if mode in ("verify", "entry")
                else (crows == [("ACTIVE",)] and jrows == [("OPEN",)]))
    if not admitted:
        raise RuntimeError("CANARY_STAGED_CONTROL_OR_JOURNAL_NOT_ADMITTED_" + mode.upper())
    return root / "site", root / "sources" / "apc_demo_canary_attended_operator.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("verify", "entry", "close"), required=True)
    parser.add_argument("--owner-apc", default="")
    parser.add_argument("--activation-id")
    parser.add_argument("--expires-utc")
    parser.add_argument("--side", choices=("BUY", "SELL"))
    parser.add_argument("--stop")
    args = parser.parse_args(argv)
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("CANARY_REQUIRES_PYTHON_B_I")
    base = os.getenv("LOCALAPPDATA")
    if not base:
        raise RuntimeError("CANARY_LOCALAPPDATA_MISSING")
    if args.mode != "verify" and args.owner_apc != APC_TOKEN:
        raise RuntimeError("CANARY_APC_BROKER_AUTHORIZATION_REQUIRED")
    site, script = verify_stage(pathlib.Path(base) / ROOT_NAME, args.mode)
    if args.mode == "verify":
        if "MetaTrader5" in sys.modules:
            raise RuntimeError("CANARY_VERIFY_MUST_NOT_IMPORT_METATRADER5")
        print("CANARY_ISOLATED_STAGE_VERIFIED__KILLED__UNUSED__NO_MT5")
        return 0
    if not args.activation_id or not args.expires_utc:
        raise RuntimeError("CANARY_ACTIVATION_AND_EXPIRY_REQUIRED")
    params = ["--mode", args.mode, "--owner-apc", APC_TOKEN,
              "--activation-id", args.activation_id,
              "--expires-utc", args.expires_utc]
    if args.mode == "entry":
        if args.side is None or args.stop is None:
            raise RuntimeError("CANARY_ENTRY_SIDE_AND_STOP_REQUIRED")
        params.extend(["--side", args.side, "--stop", args.stop])
    elif args.side is not None or args.stop is not None:
        raise RuntimeError("CANARY_CLOSE_DOES_NOT_ACCEPT_SIDE_STOP")
    # Only this Python child sees the pinned wheel site directory;
    # no global pip installation or Python environment changes.
    sys.path.insert(0, str(site))
    try:
        source = runpy.run_path(str(script), run_name="canary_owner_gated_loader")
        return int(source["main"](params))
    finally:
        sys.path.remove(str(site))


if __name__ == "__main__":
    raise SystemExit(main())
