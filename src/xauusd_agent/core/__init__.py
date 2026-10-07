"""Deterministic core primitives for the execution-disabled XAUUSD agent."""

from .canonical import canonical_bytes, canonical_json, sha256_hex
from .clock import Clock, SystemClock, TimeObservation, ensure_utc, format_utc, parse_utc
from .decimal_value import ExactDecimal, canonical_decimal, parse_decimal
from .errors import (
    AgentError,
    CapabilityError,
    ConcurrentWriteError,
    IntegrityError,
    LeaseError,
    ValidationError,
)
from .model import (
    AuditEventType,
    DecisionKind,
    ExecutionCapability,
    InternalEventType,
    ReasonCode,
    RuntimeMode,
    RuntimeState,
)

__all__ = [
    "AgentError",
    "AuditEventType",
    "CapabilityError",
    "Clock",
    "ConcurrentWriteError",
    "DecisionKind",
    "ExactDecimal",
    "ExecutionCapability",
    "IntegrityError",
    "InternalEventType",
    "LeaseError",
    "ReasonCode",
    "RuntimeMode",
    "RuntimeState",
    "SystemClock",
    "TimeObservation",
    "ValidationError",
    "canonical_bytes",
    "canonical_decimal",
    "canonical_json",
    "ensure_utc",
    "format_utc",
    "parse_decimal",
    "parse_utc",
    "sha256_hex",
]
