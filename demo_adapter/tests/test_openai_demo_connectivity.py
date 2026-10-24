"""Model/project preflight uses the actual API entitlement, no hard-coded 404.

All responses faked; never read a real key or call the internet/MT5.
"""
from __future__ import annotations

import urllib.error

import pytest

from xauusd_demo import openai_demo_connectivity as probe
from xauusd_demo.envelope import DemoSafetyError


def _ok():
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"status":"READY"}'}],
            }
        ],
    }


def test_luna_404_selects_project_visible_fallback(monkeypatch):
    names = []
    def fake(*, api_key, path, payload=None):
        assert api_key == "t"*25
        if path == "/v1/models":
            return {"data": [
                {"id": "gpt-6-luna"},
                {"id": "gpt-5-mini"},
                {"id": "untrusted-model"},
            ]}
        assert path == "/v1/responses"
        names.append(payload["model"])
        if payload["model"] == "gpt-6-luna":
            raise urllib.error.HTTPError("", 404, "Not Found", {}, None)
        return _ok()

    monkeypatch.setattr(probe, "_json_request", fake)
    assert probe.select_verified_model("t"*25) == "gpt-5-mini"
    assert names == ["gpt-6-luna", "gpt-5-mini"]


def test_project_entitlement_list_governs_model_choice(monkeypatch):
    names = []
    def fake(*, api_key, path, payload=None):
        if path == "/v1/models":
            return {"data": [{"id": "gpt-4.1-mini"}]}
        names.append(payload["model"])
        return _ok()
    monkeypatch.setattr(probe, "_json_request", fake)
    assert probe.select_verified_model("z"*25) == "gpt-4.1-mini"
    assert names == ["gpt-4.1-mini"]


def test_missing_approved_model_never_sends_inference(monkeypatch):
    def fake(*, api_key, path, payload=None):
        if path == "/v1/models":
            return {"data": [{"id": "non-admitted-model"}]}
        raise AssertionError("should never submit unreviewed model")
    monkeypatch.setattr(probe, "_json_request", fake)
    with pytest.raises(DemoSafetyError, match="NO_REVIEWED"):
        probe.select_verified_model("t"*25)


def test_invalid_project_key_fails_before_trade(monkeypatch):
    def fake(*, api_key, path, payload=None):
        raise urllib.error.HTTPError("", 401, "Unauthorized", {}, None)
    monkeypatch.setattr(probe, "_json_request", fake)
    with pytest.raises(DemoSafetyError, match="HTTP_401"):
        probe.select_verified_model("t"*25)
