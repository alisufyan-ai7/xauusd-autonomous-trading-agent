from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
decision_log = (root / "phase0" / "DECISION_LOG.md").read_text(encoding="utf-8")
ids = [int(value) for value in re.findall(r"^\| D-(\d{4}) \|", decision_log, re.MULTILINE)]
if not ids or ids != list(range(1, max(ids) + 1)):
    raise SystemExit(f"Decision IDs are not continuous and unique: {ids}")

spec = (root / "phase0" / "PHASE_0_SPECIFICATION.md").read_text(encoding="utf-8")
if "Gate 0 is NOT complete" not in spec:
    raise SystemExit("Specification must explicitly keep Gate 0 incomplete")
if "Production implementation:** Prohibited" not in spec:
    raise SystemExit("Production prohibition is missing")

print(f"Validated D-0001 through D-{max(ids):04d}; Gate 0 remains incomplete.")
