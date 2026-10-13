from __future__ import annotations

import json
from pathlib import Path

from xauusd_agent import cli, host


def test_cli_static_preflight_is_execution_disabled(tmp_path: Path, capsys) -> None:
    assert cli.main(["--state-directory", str(tmp_path), "--print-preflight"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution_enabled"] is False
    assert payload["broker_sink"] == "NULL"
    assert payload["analyst_transport"] == "DISABLED"
    assert payload["broker_action_count"] == 0


def test_cli_broker_preflight_delegates_to_guarded_host(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    monkeypatch.setattr(
        host,
        "broker_preflight",
        lambda: {
            "connected": True,
            "trading_api_disabled": True,
            "open_positions": 0,
            "pending_orders": 0,
            "execution_enabled": False,
            "broker_action_count": 0,
        },
    )
    assert cli.main(["--state-directory", str(tmp_path), "--broker-preflight"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["trading_api_disabled"] is True
    assert payload["broker_action_count"] == 0


def test_cli_once_and_service_delegate_without_enabling_execution(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[Path, int, bool]] = []

    def fake_run(state_directory: Path, *, interval_seconds: int, once: bool) -> int:
        calls.append((state_directory, interval_seconds, once))
        return 0

    monkeypatch.setattr(host, "run_shadow_host", fake_run)

    assert (
        cli.main(
            [
                "--state-directory",
                str(tmp_path),
                "--once",
                "--interval-seconds",
                "9",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "--state-directory",
                str(tmp_path),
                "--run-service",
                "--interval-seconds",
                "15",
            ]
        )
        == 0
    )
    assert calls == [(tmp_path.resolve(), 9, True), (tmp_path.resolve(), 15, False)]
