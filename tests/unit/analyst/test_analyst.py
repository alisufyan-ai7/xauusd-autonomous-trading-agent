from datetime import UTC, datetime, timedelta

from xauusd_agent.analyst import (
    AnalystClient,
    AnalystDecision,
    AnalystRequest,
    AnalystResponse,
    FakeAnalystTransport,
    SolAnalystAdapter,
)

HASH = "a" * 64


def request(now: datetime) -> AnalystRequest:
    return AnalystRequest(
        "r1", now, now + timedelta(seconds=10), "XAUUSD", HASH, HASH, HASH, {"rsi": 42.0}
    )


class StaticTransport:
    def __init__(self, payload: str):
        self.payload = payload

    def send(self, payload, *, timeout_seconds):
        assert payload["store"] is False
        assert payload["tools"] == []
        assert timeout_seconds > 0
        return self.payload


def test_default_transport_fails_closed():
    now = datetime.now(UTC)
    verdict = AnalystClient().evaluate(request(now), now=now)
    assert verdict == verdict.__class__(
        AnalystDecision.NO_TRADE,
        False,
        ("ANALYST_UNAVAILABLE:AnalystTransportDisabled",),
    )


def test_valid_echo_is_admissible_but_non_authoritative():
    now = datetime.now(UTC)
    payload = (
        '{"schema_version":"analyst-response-v1","request_id":"r1","state_hash":"'
        + HASH
        + '","decision":"SETUP","reason_codes":["STRUCTURE_OK"]}'
    )
    verdict = AnalystClient(StaticTransport(payload)).evaluate(request(now), now=now)
    assert verdict.decision is AnalystDecision.SETUP
    assert verdict.admissible is True


def test_bad_state_echo_fails_closed():
    now = datetime.now(UTC)
    payload = (
        '{"schema_version":"analyst-response-v1","request_id":"r1","state_hash":"'
        + ("b" * 64)
        + '","decision":"SETUP","reason_codes":["OK"]}'
    )
    verdict = AnalystClient(StaticTransport(payload)).evaluate(request(now), now=now)
    assert verdict.decision is AnalystDecision.NO_TRADE
    assert verdict.reason_codes == ("ANALYST_STATE_ECHO_MISMATCH",)


def test_schema_rejects_extra_response_key():
    try:
        AnalystResponse.parse(
            {
                "schema_version": "analyst-response-v1",
                "request_id": "r",
                "state_hash": HASH,
                "decision": "NO_TRADE",
                "reason_codes": ["X"],
                "extra": 1,
            }
        )
    except ValueError:
        pass
    else:
        raise AssertionError("extra response key was accepted")


def test_named_sol_adapter_has_only_offline_fake_transport():
    now = datetime.now(UTC)
    payload = (
        '{"schema_version":"analyst-response-v1","request_id":"r1","state_hash":"'
        + HASH
        + '","decision":"NO_TRADE","reason_codes":["ABSTAIN"]}'
    )
    fake = FakeAnalystTransport(payload)
    verdict = SolAnalystAdapter(fake).evaluate(request(now), now=now)
    assert verdict.decision is AnalystDecision.NO_TRADE
    assert verdict.admissible is True
    assert fake.calls == 1


def test_naive_evaluation_clock_fails_closed():
    now = datetime.now(UTC)
    verdict = AnalystClient().evaluate(request(now), now=datetime.now())
    assert verdict.decision is AnalystDecision.NO_TRADE
    assert verdict.reason_codes == ("ANALYST_CLOCK_INVALID",)


def test_response_must_be_json_object():
    try:
        AnalystResponse.parse([["schema_version", "analyst-response-v1"]])
    except ValueError:
        pass
    else:
        raise AssertionError("non-object response was accepted")
