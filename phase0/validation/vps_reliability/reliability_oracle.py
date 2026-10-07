"""Deterministic, offline oracle for the Gate 0 VPS reliability matrix.

This module models observations only.  It has no MetaTrader import, network
client, process-control primitive, credential input, or trading capability.
The numeric thresholds are fixture policy values used to test boundary
behavior; they do not freeze the still-open production operating policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


HEALTHY = "HEALTHY"
UNHEALTHY = "UNHEALTHY"
SAFE_STOP = "SAFE_STOP"

RESTART_EVENTS = {"PROCESS_RESTART", "MT5_RESTART", "WINDOWS_RESTART"}
REPROBE_EVENTS = RESTART_EVENTS | {"RECONNECT"}


@dataclass(frozen=True)
class Policy:
    max_tick_age_ms: int = 30_000
    max_future_tick_ms: int = 2_000
    max_abs_clock_offset_ms: int = 1_000


@dataclass(frozen=True)
class Verdict:
    state: str
    reason: str

    def label(self) -> str:
        return f"{self.state}:{self.reason}"


DEFAULT_FRAME: dict[str, Any] = {
    "event": "SAMPLE",
    "boot_id": "boot-a",
    "sequence": 0,
    "monotonic_ms": 1_000,
    "manifest_verified": True,
    "static_verifier_pass": True,
    "write_ok": True,
    "tradeapi_disabled": True,
    "attach_ok": True,
    "connected": True,
    "startup_checks": True,
    "full_probe_ok": True,
    "terminal_candidates": 1,
    "identity": "account-a|server-a|XAUUSD",
    "terminal_build": 6104,
    "compatibility_validated": False,
    "tick_age_ms": 250,
    "clock_offset_ms": 10,
}


class ReliabilityOracle:
    """Stateful evaluator that preserves only redacted identity/build state."""

    def __init__(self, policy: Policy | None = None) -> None:
        self.policy = policy or Policy()
        self.baseline_identity: str | None = None
        self.baseline_build: int | None = None
        self.boot_id: str | None = None
        self.last_sequence: int | None = None
        self.last_monotonic_ms: int | None = None
        self.safe_stopped = False

    def _verdict(self, state: str, reason: str) -> Verdict:
        if state == SAFE_STOP:
            self.safe_stopped = True
        return Verdict(state, reason)

    def evaluate(self, supplied: dict[str, Any]) -> Verdict:
        frame = {**DEFAULT_FRAME, **supplied}
        event = frame["event"]

        if self.safe_stopped:
            return Verdict(SAFE_STOP, "SAFE_STOP_LATCHED")

        # These are evidence-integrity or safety-barrier failures.  Recovery in
        # the same run is forbidden because accepting later rows would make an
        # invalid run appear continuous.
        if frame["tradeapi_disabled"] is not True:
            return self._verdict(SAFE_STOP, "EXTERNAL_PYTHON_TRADING_NOT_DISABLED")
        if frame["manifest_verified"] is not True:
            return self._verdict(SAFE_STOP, "PACKAGE_MANIFEST_UNVERIFIED")
        if frame["static_verifier_pass"] is not True:
            return self._verdict(SAFE_STOP, "STATIC_VERIFIER_FAILED")
        if frame["write_ok"] is not True:
            return self._verdict(SAFE_STOP, "DURABLE_WRITE_FAILED")

        if frame["terminal_candidates"] != 1:
            return self._verdict(UNHEALTHY, "TERMINAL_SELECTION_AMBIGUOUS")
        if frame["attach_ok"] is not True:
            return self._verdict(UNHEALTHY, "TERMINAL_ATTACH_FAILED")
        if frame["connected"] is not True:
            return self._verdict(UNHEALTHY, "NETWORK_OR_TERMINAL_DISCONNECTED")

        if self.baseline_identity is None:
            if event != "STARTUP":
                return self._verdict(UNHEALTHY, "NO_ACCEPTED_STARTUP_BASELINE")
            if frame["startup_checks"] is not True or frame["full_probe_ok"] is not True:
                return self._verdict(UNHEALTHY, "STARTUP_REPROBE_INCOMPLETE")
            self.baseline_identity = frame["identity"]
            self.baseline_build = frame["terminal_build"]
            self.boot_id = frame["boot_id"]
        elif frame["identity"] != self.baseline_identity:
            return self._verdict(SAFE_STOP, "IDENTITY_DRIFT")

        build_changed = frame["terminal_build"] != self.baseline_build
        if build_changed:
            if frame["compatibility_validated"] is not True:
                return self._verdict(UNHEALTHY, "BUILD_REVALIDATION_REQUIRED")
            if event not in REPROBE_EVENTS:
                return self._verdict(UNHEALTHY, "BUILD_CHANGE_WITHOUT_REPROBE_BOUNDARY")
            if frame["full_probe_ok"] is not True:
                return self._verdict(UNHEALTHY, "BUILD_REPROBE_INCOMPLETE")
            self.baseline_build = frame["terminal_build"]

        if event in RESTART_EVENTS:
            if frame["startup_checks"] is not True or frame["full_probe_ok"] is not True:
                return self._verdict(UNHEALTHY, "RESTART_REPROBE_INCOMPLETE")
            if event in {"PROCESS_RESTART", "WINDOWS_RESTART"}:
                if frame["boot_id"] == self.boot_id:
                    return self._verdict(UNHEALTHY, "RESTART_BOOT_ID_NOT_CHANGED")
                if frame["sequence"] != 0:
                    return self._verdict(UNHEALTHY, "RESTART_SEQUENCE_NOT_RESET")
                self.boot_id = frame["boot_id"]
                self.last_sequence = None
                self.last_monotonic_ms = None
        elif frame["boot_id"] != self.boot_id:
            return self._verdict(UNHEALTHY, "UNDECLARED_PROCESS_RESTART")

        if event == "RECONNECT" and frame["full_probe_ok"] is not True:
            return self._verdict(UNHEALTHY, "RECONNECT_REPROBE_INCOMPLETE")

        if abs(frame["clock_offset_ms"]) > self.policy.max_abs_clock_offset_ms:
            return self._verdict(UNHEALTHY, "CLOCK_OFFSET_LIMIT_EXCEEDED")
        if frame["tick_age_ms"] > self.policy.max_tick_age_ms:
            return self._verdict(UNHEALTHY, "STALE_TICK")
        if frame["tick_age_ms"] < -self.policy.max_future_tick_ms:
            return self._verdict(UNHEALTHY, "FUTURE_TICK_LIMIT_EXCEEDED")

        if self.last_monotonic_ms is not None and frame["monotonic_ms"] <= self.last_monotonic_ms:
            return self._verdict(UNHEALTHY, "MONOTONIC_TIME_NOT_INCREASING")
        if self.last_sequence is not None and frame["sequence"] != self.last_sequence + 1:
            # Preserve the observed location of the gap, so the next correctly
            # sequenced row can recover without pretending the missing row was
            # backfilled.
            self.last_sequence = frame["sequence"]
            self.last_monotonic_ms = frame["monotonic_ms"]
            return self._verdict(UNHEALTHY, "OBSERVATION_SEQUENCE_GAP")

        self.last_sequence = frame["sequence"]
        self.last_monotonic_ms = frame["monotonic_ms"]
        return self._verdict(HEALTHY, "OK")


def run_scenario(scenario: dict[str, Any]) -> list[str]:
    policy = Policy(**scenario.get("policy", {}))
    oracle = ReliabilityOracle(policy)
    return [oracle.evaluate(frame).label() for frame in scenario["frames"]]


def load_corpus(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("corpus scenarios must be a list")
    ids = [row.get("id") for row in scenarios]
    if any(not isinstance(value, str) or not value for value in ids):
        raise ValueError("every scenario needs a non-empty string id")
    if len(ids) != len(set(ids)):
        raise ValueError("scenario ids must be unique")
    return scenarios


def verify_corpus(scenarios: Iterable[dict[str, Any]]) -> list[str]:
    failures = []
    for scenario in scenarios:
        actual = run_scenario(scenario)
        if actual != scenario["expected"]:
            failures.append(f"{scenario['id']}: expected {scenario['expected']!r}, got {actual!r}")
    return failures

