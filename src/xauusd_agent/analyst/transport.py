"""Transport boundary.  The production-candidate default cannot call a model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


class AnalystTransportDisabled(RuntimeError):
    pass


class AnalystTransport(Protocol):
    def send(self, payload: Mapping[str, Any], *, timeout_seconds: float) -> str | bytes: ...


class DisabledAnalystTransport:
    """Default transport for the execution-disabled production candidate."""

    def send(self, payload: Mapping[str, Any], *, timeout_seconds: float) -> str | bytes:
        del payload, timeout_seconds
        raise AnalystTransportDisabled("analyst transport is disabled by baseline")


@dataclass(slots=True)
class FakeAnalystTransport:
    """Deterministic offline transport for tests and local composition only."""

    response: str | bytes
    calls: int = 0

    def send(self, payload: Mapping[str, Any], *, timeout_seconds: float) -> str | bytes:
        if timeout_seconds <= 0:
            raise TimeoutError("fake transport received an expired deadline")
        if payload.get("store") is not False or payload.get("tools") != []:
            raise ValueError("analyst privacy/tool restrictions are missing")
        self.calls += 1
        return self.response
