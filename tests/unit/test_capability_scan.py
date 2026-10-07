from pathlib import Path

import pytest

from scripts.verify_execution_disabled import CapabilityViolation, verify


def test_current_source_has_no_order_capability() -> None:
    verify(Path("src/xauusd_agent"))


def test_scanner_rejects_order_send(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.py"
    source.write_text("def order_send():\n    return None\n", encoding="utf-8")
    with pytest.raises(CapabilityViolation):
        verify(tmp_path)
