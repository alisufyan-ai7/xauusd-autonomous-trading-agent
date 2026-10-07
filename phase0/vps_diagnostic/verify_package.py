"""Static and behavioral safety verification for the VPS diagnostic."""

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

FILES = ("diagnostic.py", "readonly_mt5.py")
FORBIDDEN = {"order_send", "order_check", "login", "symbol_select", "market_book_add", "market_book_release", "positions_get", "orders_get", "history_deals_get", "history_orders_get", "getattr", "setattr", "eval", "exec", "compile", "__import__"}
FORBIDDEN_IMPORTS = {"socket", "requests", "urllib", "http", "ftplib", "subprocess", "ctypes", "win32com"}
ALLOWED_MT5 = {"initialize", "shutdown", "last_error", "version", "terminal_info", "account_info", "symbol_info", "symbol_info_tick"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            roots = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [(node.module or "").split(".")[0]]
            findings += [f"forbidden import {r}" for r in roots if r in FORBIDDEN_IMPORTS]
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
            if name in FORBIDDEN:
                findings.append(f"forbidden call {name} line {node.lineno}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "_mt5" and node.attr not in ALLOWED_MT5:
            findings.append(f"non-allow-listed MT5 attribute {node.attr} line {node.lineno}")
    return {"file": path.name, "sha256": sha(path), "findings": findings}


def main():
    base = Path(__file__).resolve().parent
    sources = [verify_source(base / name) for name in FILES]
    test = subprocess.run([sys.executable, "-m", "unittest", "-v", "test_diagnostic.py"], cwd=base, text=True, capture_output=True)
    ok = not any(x["findings"] for x in sources) and test.returncode == 0
    report = {"status": "PASS" if ok else "FAIL", "sources": sources, "tests": {"exit_code": test.returncode, "stdout": test.stdout, "stderr": test.stderr}, "forbidden_calls": sorted(FORBIDDEN), "allowed_mt5_attributes": sorted(ALLOWED_MT5)}
    (base / "VERIFICATION_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

