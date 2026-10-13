"""Immutable runtime configuration and the non-bypassable execution barrier."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when configuration would weaken the production-candidate boundary."""


class RuntimeMode(StrEnum):
    SHADOW = "SHADOW"


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration admitted by the October execution-disabled artifact.

    There is deliberately no execution-enabled field.  The only admitted
    runtime mode is SHADOW and the only broker sink is NULL.
    """

    state_directory: Path
    symbol: str = "XAUUSD"
    mode: RuntimeMode = RuntimeMode.SHADOW
    broker_sink: str = "NULL"
    analyst_transport: str = "DISABLED"
    external_python_real_money_trading: str = "DISABLED"

    def __post_init__(self) -> None:
        if not self.state_directory.is_absolute():
            raise ConfigurationError("state_directory must be absolute")
        if self.symbol != "XAUUSD":
            raise ConfigurationError("production candidate is bound to XAUUSD")
        if self.mode is not RuntimeMode.SHADOW:
            raise ConfigurationError("only SHADOW mode is admitted")
        if self.broker_sink != "NULL":
            raise ConfigurationError("only the NULL broker sink is admitted")
        if self.analyst_transport != "DISABLED":
            raise ConfigurationError("Sol transport requires separate APC-SOL-SHADOW approval")
        if self.external_python_real_money_trading != "DISABLED":
            raise ConfigurationError("external Python real-money trading must remain disabled")

    @property
    def execution_enabled(self) -> bool:
        return False
