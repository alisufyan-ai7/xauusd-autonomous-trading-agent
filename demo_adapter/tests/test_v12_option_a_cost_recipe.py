"""Synthetic independent checks of owner-refined v1.2 COST SCOPES, no live data."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from scripts.v12_option_a_cost_recipe import (
    ExternalEventStressQuote,
    MinuteAdverseQuote,
    OptionAComponentProof,
    OptionACostSafetyError,
    rehearse_option_a_cost_split,
)

START = datetime(2026, 10, 20, 12, 30, tzinfo=UTC)
END = START + timedelta(hours=4)
OVERLAP_START = START + timedelta(hours=1)
OVERLAP_END = END


def sample() -> tuple[tuple[MinuteAdverseQuote, ...], tuple[ExternalEventStressQuote, ...], OptionAComponentProof]:
    quotes = tuple(
        MinuteAdverseQuote(
            minute_index=i, timestamp_utc=START + timedelta(minutes=i),
            spread_usd=D("0.10") if i >= 60 else D("20.00"),
            move_1s_usd=D("0.20") if i >= 60 else D("40.00"),
            move_5s_usd=D("0.30") if i >= 60 else D("50.00"),
            move_30s_usd=D("0.40") if i >= 60 else D("60.00"),
            gap_quote_proxy_usd=D("0.50") if i >= 60 else D("80.00"),
            pair_count_1s=1, pair_count_5s=1, pair_count_30s=1,
        )
        for i in range(240)
    )
    event = (
        ExternalEventStressQuote(
            timestamp_utc=START - timedelta(days=1),
            event_source_digest="e" * 64,
            spread_usd=D("90.00"), move_proxy_usd=D("100.00"),
            gap_quote_proxy_usd=D("150.00"),
        ),
    )
    proof = OptionAComponentProof(
        pre_demo_slippage_floor_usd=D("0.60"),
        gap_floor_usd=D("0.70"),
        round_trip_commission_usd=D("1.00"),
        holding_contingency_usd=D("2.00"),
        stressed_commission_usd=D("1.00"),
        stressed_holding_contingency_usd=D("2.00"),
        observation_sha256="1" * 64,
        independent_symbol_to_usd_proof_sha256="2" * 64,
        official_overlap_and_event_guard_proof_sha256="3" * 64,
        component_method_nonoverlap_proof_sha256="4" * 64,
        pre_demo_slippage_floor_source_sha256="5" * 64,
        broker_commission_swap_proof_sha256="6" * 64,
        external_stress_manifest_sha256="7" * 64,
    )
    return quotes, event, proof


def rehearse(
    quotes: tuple[MinuteAdverseQuote, ...] | None = None,
    event: tuple[ExternalEventStressQuote, ...] | None = None,
    proof: OptionAComponentProof | None = None,
    overlap_start: datetime = OVERLAP_START,
) -> object:
    base, stress, evidence = sample()
    return rehearse_option_a_cost_split(
        observation_start_utc=START, observation_end_utc=END,
        overlap_start_utc=overlap_start, overlap_end_utc=OVERLAP_END,
        minute_quotes=quotes if quotes is not None else base,
        event_stress_quotes=event if event is not None else stress,
        cost_proof=proof if proof is not None else evidence,
    )


def test_current_uses_overlap_only_and_stress_uses_full_window_plus_event() -> None:
    result = rehearse()
    assert result.eligible_baseline_minute_count == 180
    assert result.observation_minute_count == 240
    assert result.external_stress_record_count == 1
    assert result.current_spread_usd == D("0.10")
    assert result.current_slippage_quote_proxy_floor_usd == D("0.60")
    assert result.current_gap_quote_proxy_floor_usd == D("0.70")
    assert result.current_adverse_cost_usd == D("4.40")
    # Event evidence is 90 spread + 100 proxy + 150 quote gap + 1+2 costs.
    assert result.stressed_adverse_cost_usd == D("343.00")
    assert result.execution_slippage_measured is False
    assert result.execution_or_demo_admitted is False


def test_nonoverlap_shock_cannot_contaminate_current() -> None:
    quotes, event, proof = sample()
    modified = list(quotes)
    modified[12] = replace(modified[12], spread_usd=D("9999"))
    result = rehearse(tuple(modified), event, proof)
    assert result.current_adverse_cost_usd == D("4.40")
    assert result.stressed_adverse_cost_usd > D("9999")


def test_overlap_shock_cannot_be_hidden_by_synthetic_result() -> None:
    quotes, event, proof = sample()
    modified = list(quotes)
    modified[62] = replace(modified[62], gap_quote_proxy_usd=D("20.00"))
    result = rehearse(tuple(modified), event, proof)
    assert result.current_adverse_cost_usd == D("23.70")
    assert result.stressed_adverse_cost_usd >= D("343.00")


def test_stressed_cannot_below_double_current_floor() -> None:
    quotes, event, proof = sample()
    tame = tuple(replace(q, spread_usd=D("0.01"),
                         move_proxy_usd=D("0.01"),
                         gap_quote_proxy_usd=D("0.01")) for q in event)
    result = rehearse(quotes, tame, proof)
    assert result.stressed_adverse_cost_usd >= D("8.80")


def test_baseline_requires_all_180_minutes_even_if_stress_is_complete() -> None:
    quotes, event, proof = sample()
    with pytest.raises(OptionACostSafetyError, match="240-minute"):
        rehearse(quotes[1:], event, proof)


def test_proof_missing_is_denial_not_assumed_zero() -> None:
    quotes, event, proof = sample()
    bad = replace(proof, pre_demo_slippage_floor_source_sha256="")
    with pytest.raises(OptionACostSafetyError, match="proof absent"):
        rehearse(quotes, event, bad)


def test_missing_positive_pre_demo_proxy_floor_is_denial() -> None:
    quotes, event, proof = sample()
    with pytest.raises(OptionACostSafetyError, match="positive reserve"):
        rehearse(quotes, event, replace(proof, pre_demo_slippage_floor_usd=D("0")))


def test_quote_moves_never_called_measured_execution_slippage() -> None:
    result = rehearse()
    assert "SYNTHETIC_MATH_ONLY" in result.status
    assert result.execution_slippage_measured is False
    assert result.execution_or_demo_admitted is False


def test_missing_relevant_external_event_stress_denied() -> None:
    quotes, _, proof = sample()
    with pytest.raises(OptionACostSafetyError, match="stress evidence absent"):
        rehearse(quotes, (), proof)


def test_event_stress_inside_baseline_contaminates_and_is_rejected() -> None:
    quotes, event, proof = sample()
    inside = (replace(event[0], timestamp_utc=START + timedelta(minutes=90)),)
    with pytest.raises(OptionACostSafetyError, match="overlaps"):
        rehearse(quotes, inside, proof)


def test_broker_negative_spread_or_cost_denied() -> None:
    quotes, event, proof = sample()
    modified = list(quotes)
    modified[78] = replace(modified[78], spread_usd=D("-1"))
    with pytest.raises(OptionACostSafetyError, match="negative"):
        rehearse(tuple(modified), event, proof)
    with pytest.raises(OptionACostSafetyError, match="negative"):
        rehearse(quotes, event, replace(proof, round_trip_commission_usd=D("-1")))


def test_nan_and_unproven_currency_conversion_denied() -> None:
    quotes, event, proof = sample()
    with pytest.raises(OptionACostSafetyError, match="unknown"):
        rehearse(quotes, event, replace(proof, holding_contingency_usd=D("NaN")))
    with pytest.raises(OptionACostSafetyError, match="proof absent"):
        rehearse(quotes, event, replace(proof, independent_symbol_to_usd_proof_sha256="0"))


def test_broken_genuine_tick_pair_coverage_inside_overlap_denied() -> None:
    quotes, event, proof = sample()
    corrupt = list(quotes)
    for i in range(60, 70):
        corrupt[i] = replace(corrupt[i], pair_count_30s=0)
    with pytest.raises(OptionACostSafetyError, match="incomplete true tick pairs"):
        rehearse(tuple(corrupt), event, proof)


def test_reordered_source_minutes_rejected_even_when_values_match() -> None:
    quotes, event, proof = sample()
    corrupt = list(quotes)
    corrupt[100], corrupt[101] = corrupt[101], corrupt[100]
    with pytest.raises(OptionACostSafetyError, match="reordered"):
        rehearse(tuple(corrupt), event, proof)


def test_event_record_must_have_unique_external_source() -> None:
    quotes, event, proof = sample()
    with pytest.raises(OptionACostSafetyError, match="source proof"):
        rehearse(quotes, (replace(event[0], event_source_digest=""),), proof)


def test_utc_boundary_and_regime_cannot_expand_after_observation() -> None:
    quotes, event, proof = sample()
    with pytest.raises(OptionACostSafetyError, match="overlap"):
        rehearse(quotes, event, proof, overlap_start=START - timedelta(minutes=1))
    with pytest.raises(OptionACostSafetyError, match="UTC"):
        rehearse(quotes, event, proof, overlap_start=OVERLAP_START.replace(tzinfo=None))
