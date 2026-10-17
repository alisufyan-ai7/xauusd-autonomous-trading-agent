"""Bounded demo-only XAUUSD execution package.

This package is deliberately separate from xauusd_agent. It is not part of
the execution-disabled production-candidate wheel and must never be selected
for a live-account fingerprint.
"""

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
from .risk_binding import DemoRiskCalibration

__all__ = [
    "DemoActivationPermit",
    "DemoIdentity",
    "DemoMT5Adapter",
    "DemoOrderRequest",
    "DemoPolicy",
    "DemoRiskCalibration",
    "DemoSafetyError",
    "DemoSide",
    "DemoSubmissionLedger",
]
