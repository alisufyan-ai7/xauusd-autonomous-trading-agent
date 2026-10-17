"""Static proof that order-capable demo code is outside the PCR package."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRODUCTION = REPO / "src" / "xauusd_agent"
DEMO = REPO / "demo_adapter" / "src" / "xauusd_demo"

for path in PRODUCTION.rglob("*.py"):
    text = path.read_text(encoding="utf-8")
    if "xauusd_demo" in text:
        raise SystemExit(f"production source imports demo package: {path}")
    if "order_send(" in text:
        raise SystemExit(f"production source contains order_send capability: {path}")

if not (DEMO / "mt5_demo.py").is_file():
    raise SystemExit("separate demo adapter is missing")

if "order_send(" not in (DEMO / "mt5_demo.py").read_text(encoding="utf-8"):
    raise SystemExit("demo adapter does not contain the isolated submission capability")

print("DEMO PACKAGE BOUNDARY: PASS")
print(f"Production root: {PRODUCTION}")
print(f"Demo root:       {DEMO}")
