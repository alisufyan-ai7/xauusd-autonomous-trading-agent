"""Typed, fail-closed market and Event Guard decisions."""

from .event_guard import (
    EventGuardDecision,
    EventGuardState,
    EventObservation,
    ProtectedEvent,
    evaluate_event_guard,
)
from .market_gates import (
    GateDecision,
    GateState,
    SessionObservation,
    ShockObservation,
    combine_gates,
    evaluate_session_gate,
    evaluate_shock_gate,
)

__all__ = [
    "EventGuardDecision",
    "EventGuardState",
    "EventObservation",
    "GateDecision",
    "GateState",
    "ProtectedEvent",
    "SessionObservation",
    "ShockObservation",
    "combine_gates",
    "evaluate_event_guard",
    "evaluate_session_gate",
    "evaluate_shock_gate",
]
