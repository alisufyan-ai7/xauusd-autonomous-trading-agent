import json
from pathlib import Path

ROADMAP = Path("phase0/roadmap")
TRACEABILITY = ROADMAP / "APC_R42_PRODUCT_TEST_TRACEABILITY_2026-10-07.json"


def _ids(path: Path, key: str) -> set[str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    collection = document[key]
    return {item["id"] for item in collection}


def test_traceability_covers_every_frozen_r42_port() -> None:
    trace = json.loads(TRACEABILITY.read_text(encoding="utf-8"))
    registered = _ids(ROADMAP / "GATE_1_PORT_CONTRACT_CATALOG_R42.json", "contracts")
    assert set(trace["port_coverage"]) == registered


def test_traceability_covers_every_frozen_r42_fault_family_with_real_tests() -> None:
    trace = json.loads(TRACEABILITY.read_text(encoding="utf-8"))
    registered = _ids(ROADMAP / "GATE_2_FAULT_MATRIX_REGISTER_R42.json", "scenarios")
    coverage = trace["fault_family_component_coverage"]
    assert set(coverage) == registered
    assert all(paths for paths in coverage.values())
    assert all(Path(path).is_file() for paths in coverage.values() for path in paths)


def test_traceability_does_not_claim_pcr_or_gate_credit() -> None:
    trace = json.loads(TRACEABILITY.read_text(encoding="utf-8"))
    assert "not PCR-1 or PCR-2 acceptance" in trace["claim_limit"]
    assert "not Gate 0 credit" in trace["claim_limit"]
    assert trace["current_status"]["pcr_1"] == "NOT_YET_READY"
    assert trace["current_status"]["pcr_2"] == "NOT_YET_READY"
