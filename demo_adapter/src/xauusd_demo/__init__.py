"""Bounded demo-only XAUUSD execution package.

This package is deliberately separate from xauusd_agent. It is not part of
the execution-disabled production-candidate wheel and must never be selected
for a live-account fingerprint.
"""

from .control import (
    ARM_CONFIRMATION,
    RESET_CONFIRMATION,
    DemoControlSnapshot,
    DemoControlState,
    DemoControlStore,
)
from .envelope import (
    DemoActivationPermit,
    DemoIdentity,
    DemoOrderRequest,
    DemoPolicy,
    DemoSafetyError,
    DemoSide,
)
from .ledger import DemoSubmissionLedger
from .mt5_demo import DemoMT5Adapter
from .risk_binding import DEMO_LIFECYCLE_SCOPE, DemoRiskCalibration

__all__ = [
    "ARM_CONFIRMATION",
    "DEMO_LIFECYCLE_SCOPE",
    "RESET_CONFIRMATION",
    "DemoActivationPermit",
    "DemoControlSnapshot",
    "DemoControlState",
    "DemoControlStore",
    "DemoIdentity",
    "DemoMT5Adapter",
    "DemoOrderRequest",
    "DemoPolicy",
    "DemoRiskCalibration",
    "DemoSafetyError",
    "DemoSide",
    "DemoSubmissionLedger",
]
