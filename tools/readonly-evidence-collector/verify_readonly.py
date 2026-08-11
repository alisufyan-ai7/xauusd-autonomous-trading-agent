"""Static and behavioral verifier for the Phase 0 evidence collector."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path


POLICY_VERSION = "phase0-readonly-v1"
PRODUCTION_FILES = ("collector.py", "readonly_mt5.py")
DEPENDENCY_LOCK = "requirements-win-py312.txt"
EXPECTED_DEPENDENCY_LOCK_LINES = {
    "--only-binary=:all:",
    "MetaTrader5==5.0.6090 --hash=sha256:70601ae582a0d9a5b8e4d074b6f198ccf82a3172ced4c8eb4b47ad091f578a86",
    "numpy==2.5.0 --hash=sha256:6f2d6873e2940c860a309d21e25b1e69af6aaffdd80aa056b04c16380db1c4f2",
}
FORBIDDEN_CALLS = {
    "order_send", "order_check", "login", "symbol_select", "market_book_add",
    "market_book_release", "eval", "exec", "compile", "__import__", "getattr",
    "setattr", "delattr",
}
FORBIDDEN_IMPORT_ROOTS = {
    "socket", "requests", "urllib", "http", "ftplib", "telnetlib", "subprocess",
    "ctypes", "multiprocessing", "win32com",
}
ALLOWED_MT5_ATTRIBUTES = {
    "__author__", "__version__", "initialize", "shutdown", "last_error", "version",
    "terminal_info", "account_info", "symbols_get", "symbol_info", "symbol_info_tick",
    "copy_rates_from_pos", "copy_ticks_from", "orders_get", "positions_get",
    "history_orders_get", "history_deals_get", "order_calc_profit", "order_calc_margin",
    "TIMEFRAME_M1", "TIMEFRAME_M5", "TIMEFRAME_M15", "TIMEFRAME_H1", "TIMEFRAME_H4",
    "TIMEFRAME_D1", "COPY_TICKS_ALL", "ORDER_TYPE_BUY", "ORDER_TYPE_SELL",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dotted_name(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def verify_source(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    findings = []
    mt5_attributes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                    findings.append(f"forbidden import {alias.name} at line {node.lineno}")
                if path.name == "collector.py" and alias.name == "MetaTrader5":
                    findings.append(f"collector imports MetaTrader5 directly at line {node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_IMPORT_ROOTS:
                findings.append(f"forbidden import {node.module} at line {node.lineno}")
            if path.name == "collector.py" and node.module == "MetaTrader5":
                findings.append(f"collector imports MetaTrader5 directly at line {node.lineno}")
        elif isinstance(node, ast.Call):
            called = dotted_name(node.func)
            if called.split(".")[-1] in FORBIDDEN_CALLS:
                findings.append(f"forbidden call {called} at line {node.lineno}")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "_mt5":
            mt5_attributes.add(node.attr)
            if node.attr not in ALLOWED_MT5_ATTRIBUTES:
                findings.append(f"non-allow-listed MT5 attribute {node.attr} at line {node.lineno}")
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "mt5_attributes": sorted(mt5_attributes),
    }


def verify_manifest(base: Path, filename: str) -> dict:
    path = base / filename
    findings = []
    files = []
    if not path.is_file():
        return {"status": "FAIL", "findings": [f"missing {filename}"], "files": []}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        target = (base / relative).resolve()
        if target.parent != base.resolve() or not target.is_file():
            findings.append(f"invalid manifest path {relative}")
            continue
        actual = sha256_file(target)
        files.append({"path": relative, "expected": expected, "actual": actual})
        if actual != expected:
            findings.append(f"hash mismatch {relative}")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings, "files": files}


def verify_dependency_lock(base: Path) -> dict:
    path = base / DEPENDENCY_LOCK
    if not path.is_file():
        return {
            "status": "FAIL",
            "path": DEPENDENCY_LOCK,
            "findings": [f"missing {DEPENDENCY_LOCK}"],
        }
    actual_lines = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing = sorted(EXPECTED_DEPENDENCY_LOCK_LINES - actual_lines)
    unexpected = sorted(actual_lines - EXPECTED_DEPENDENCY_LOCK_LINES)
    findings = [f"missing locked line: {line}" for line in missing]
    findings.extend(f"unexpected lock line: {line}" for line in unexpected)
    return {
        "status": "PASS" if not findings else "FAIL",
        "path": DEPENDENCY_LOCK,
        "sha256": sha256_file(path),
        "binary_only": "--only-binary=:all:" in actual_lines,
        "locked_distributions": ["MetaTrader5==5.0.6090", "numpy==2.5.0"],
        "findings": findings,
    }


def verify_package(base: Path, manifest: str | None = None, run_tests: bool = False) -> dict:
    source_results = [verify_source(base / filename) for filename in PRODUCTION_FILES]
    dependency_lock_result = verify_dependency_lock(base)
    result = {
        "schema_version": "1.0",
        "policy_version": POLICY_VERSION,
        "production_source_verification": source_results,
        "forbidden_call_set": sorted(FORBIDDEN_CALLS),
        "allowed_mt5_attributes": sorted(ALLOWED_MT5_ATTRIBUTES),
        "dependency_lock_verification": dependency_lock_result,
    }
    if manifest:
        result["package_manifest_verification"] = verify_manifest(base, manifest)
    if run_tests:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", "test_readonly.py"],
            cwd=base,
            capture_output=True,
            text=True,
            check=False,
        )
        result["behavioral_test"] = {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    statuses = [item["status"] for item in source_results]
    statuses.append(dependency_lock_result["status"])
    if manifest:
        statuses.append(result["package_manifest_verification"]["status"])
    if run_tests:
        statuses.append(result["behavioral_test"]["status"])
    result["status"] = "PASS" if all(status == "PASS" for status in statuses) else "FAIL"
    result["claim_scope"] = (
        "PASS means the shipped production sources use only the frozen observation/calculation call surface, "
        "the fake-MT5 trap test observed no risk-changing call, the dependency lock is exact and binary-only, "
        "and package hashes matched. The intended live "
        "terminal must still report tradeapi_disabled=true before and after collection."
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-manifest")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    result = verify_package(base, args.verify_manifest, args.self_test)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json:
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
