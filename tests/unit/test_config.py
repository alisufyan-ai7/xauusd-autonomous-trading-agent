from pathlib import Path

import pytest

from xauusd_agent.cli import preflight
from xauusd_agent.config import ConfigurationError, RuntimeConfig


def test_execution_barrier_is_immutable(tmp_path: Path) -> None:
    config = RuntimeConfig(state_directory=tmp_path.resolve())
    assert config.execution_enabled is False
    assert preflight(config)["broker_action_count"] == 0
    with pytest.raises(AttributeError):
        config.execution_enabled = True  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("symbol", "EURUSD", "production candidate is bound to XAUUSD"),
        ("broker_sink", "MT5", "only the NULL broker sink is admitted"),
        ("analyst_transport", "OPENAI", "requires separate APC-SOL-SHADOW approval"),
        (
            "external_python_real_money_trading",
            "ENABLED",
            "external Python real-money trading must remain disabled",
        ),
    ],
)
def test_unsafe_configuration_is_rejected(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    values = {"state_directory": tmp_path.resolve(), field: value}
    with pytest.raises(ConfigurationError, match=message):
        RuntimeConfig(**values)  # type: ignore[arg-type]
