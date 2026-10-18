"""Pure offline v1.2 Option A cost-scope rehearsal. NEVER execution authority.

All broker/provenance and USD conversion origins require an independent verifier;
caller-provided hashes/labels are NOT source authentication. Real broker costs,
risk governors and demo submission are deliberately not imported/connected.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

CENT = Decimal("0.01")


class OptionACostSafetyError(ValueError):
    """Missing or invalid evidence => NO numeric calibration admission."""


@dataclass(frozen=True, slots=True)
class MinuteAdverseQuote:
    # 0..239 and aligned to exactly the prospectively selected 4h window.
    minute_index: int
    timestamp_utc: datetime
    spread_usd: Decimal
    move_1s_usd: Decimal
    move_5s_usd: Decimal
    move_30s_usd: Decimal
    gap_quote_proxy_usd: Decimal
    pair_count_1s: int
    pair_count_5s: int
    pair_count_30s: int


@dataclass(frozen=True, slots=True)
class ExternalEventStressQuote:
    timestamp_utc: datetime
    event_source_digest: str
    spread_usd: Decimal
    move_proxy_usd: Decimal
    gap_quote_proxy_usd: Decimal


@dataclass(frozen=True, slots=True)
class OptionAComponentProof:
    # All are separately sourced, exact USD for the broker's 0.01-lot
    # account-specific symbol contract. No amount is admitted by this code.
    pre_demo_slippage_floor_usd: Decimal
    gap_floor_usd: Decimal
    round_trip_commission_usd: Decimal
    holding_contingency_usd: Decimal
    stressed_commission_usd: Decimal
    stressed_holding_contingency_usd: Decimal
    # Identical actual source digests must be verified OUTSIDE this module.
    observation_sha256: str
    independent_symbol_to_usd_proof_sha256: str
    official_overlap_and_event_guard_proof_sha256: str
    component_method_nonoverlap_proof_sha256: str
    pre_demo_slippage_floor_source_sha256: str
    broker_commission_swap_proof_sha256: str
    external_stress_manifest_sha256: str


@dataclass(frozen=True, slots=True)
class CostRecipeResult:
    status: str
    eligible_baseline_minute_count: int
    observation_minute_count: int
    external_stress_record_count: int
    current_spread_usd: Decimal
    current_slippage_quote_proxy_floor_usd: Decimal
    current_gap_quote_proxy_floor_usd: Decimal
    current_adverse_cost_usd: Decimal
    stressed_adverse_cost_usd: Decimal
    execution_slippage_measured: bool = False
    execution_or_demo_admitted: bool = False


def _sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value
    )


def _amount(value: object, name: str, *, strictly_positive: bool = False) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise OptionACostSafetyError(f"{name}: unknown exact Decimal")
    if value < 0 or (strictly_positive and value <= 0):
        raise OptionACostSafetyError(f"{name}: negative or missing required positive reserve")
    return value


def _utc(value: datetime, label: str) -> datetime:
    if (
        type(value) is not datetime or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise OptionACostSafetyError(f"{label}: UTC proof missing")
    return value.astimezone(UTC)


def _cent_up(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_CEILING)


def _quote_fields(
    spread: object, move: object, gap: object, label: str
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        _amount(spread, label + ".spread"),
        _amount(move, label + ".move"),
        _amount(gap, label + ".gap"),
    )


def rehearse_option_a_cost_split(
    *,
    observation_start_utc: datetime,
    observation_end_utc: datetime,
    overlap_start_utc: datetime,
    overlap_end_utc: datetime,
    minute_quotes: tuple[MinuteAdverseQuote, ...],
    event_stress_quotes: tuple[ExternalEventStressQuote, ...],
    cost_proof: OptionAComponentProof,
) -> CostRecipeResult:
    """Replay exact (synthetic) USD reserves without admitting a calibration.

    Baseline derives ONLY from all verified non-event minute bins wholly within
    the admitted overlap. The broader 4h + independent event-stress source
    informs stressed reserves. The preregistration/window verifier separately
    rejects actual event-contaminated and broker-ineligible capture periods.
    """
    start = _utc(observation_start_utc, "observation start")
    end = _utc(observation_end_utc, "observation end")
    entry_start = _utc(overlap_start_utc, "entry overlap start")
    entry_end = _utc(overlap_end_utc, "entry overlap end")
    if end - start != timedelta(hours=4):
        raise OptionACostSafetyError("only exact 4h observation is eligible")
    if not start <= entry_start < entry_end <= end:
        raise OptionACostSafetyError("overlap not contained inside observation")
    if entry_start.second or entry_end.second or (
        entry_start.microsecond or entry_end.microsecond
    ):
        raise OptionACostSafetyError("overlap minute alignment missing")
    if (entry_start - start).total_seconds() % 60 or (
        entry_end - start
    ).total_seconds() % 60:
        raise OptionACostSafetyError("overlap not aligned to observation minutes")
    first = int((entry_start - start).total_seconds() // 60)
    last = int((entry_end - start).total_seconds() // 60)
    if last - first < 10:
        raise OptionACostSafetyError("no meaningful full overlap cohort")

    for name in (
        "observation_sha256", "independent_symbol_to_usd_proof_sha256",
        "official_overlap_and_event_guard_proof_sha256",
        "component_method_nonoverlap_proof_sha256",
        "pre_demo_slippage_floor_source_sha256",
        "broker_commission_swap_proof_sha256",
        "external_stress_manifest_sha256",
    ):
        if not _sha(getattr(cost_proof, name)):
            raise OptionACostSafetyError(name + ": independently admitted proof absent")
    slip_min = _amount(
        cost_proof.pre_demo_slippage_floor_usd, "pre_demo_slippage_floor_usd",
        strictly_positive=True,
    )
    gap_min = _amount(cost_proof.gap_floor_usd, "gap_floor_usd")
    commission = _amount(cost_proof.round_trip_commission_usd, "commission")
    holding = _amount(cost_proof.holding_contingency_usd, "holding")
    stressed_commission = _amount(cost_proof.stressed_commission_usd, "stressed commission")
    stressed_holding = _amount(
        cost_proof.stressed_holding_contingency_usd, "stressed holding"
    )
    if stressed_commission < commission or stressed_holding < holding:
        raise OptionACostSafetyError("stress costs cannot undercut current account reserves")
    if len(minute_quotes) != 240:
        raise OptionACostSafetyError("full 240-minute observation source required")

    observations: list[tuple[Decimal, Decimal, Decimal]] = []
    baseline: list[tuple[Decimal, Decimal, Decimal]] = []
    coverage: dict[int, list[int]] = {}
    for index, quote in enumerate(minute_quotes):
        if type(quote.minute_index) is not int or quote.minute_index != index:
            raise OptionACostSafetyError("missing/reordered/repeated observed minute")
        if _utc(quote.timestamp_utc, "minute") != start + timedelta(minutes=index):
            raise OptionACostSafetyError("minute clock or source order mismatch")
        pair_counts = (
            quote.pair_count_1s, quote.pair_count_5s, quote.pair_count_30s
        )
        if any(type(n) is not int or n < 0 for n in pair_counts):
            raise OptionACostSafetyError("invalid genuine tick pair count")
        spread, quote_proxy, gap = _quote_fields(
            quote.spread_usd,
            max(
                _amount(quote.move_1s_usd, "1s"),
                _amount(quote.move_5s_usd, "5s"),
                _amount(quote.move_30s_usd, "30s"),
            ),
            quote.gap_quote_proxy_usd, "observation",
        )
        observations.append((spread, quote_proxy, gap))
        if first <= index < last:
            baseline.append((spread, quote_proxy, gap))
            bin_id = (index - first) // 10
            if bin_id not in coverage:
                coverage[bin_id] = [0, 0, 0]
            for j, n in enumerate(pair_counts):
                coverage[bin_id][j] += n

    # Any missing 1/5/30-second actual tick pair for any ten-minute overlap
    # segment is a denial, even if the full 4h window otherwise passed.
    if any(min(bins) <= 0 for bins in coverage.values()):
        raise OptionACostSafetyError("incomplete true tick pairs in baseline overlap")
    if len(coverage) != (last - first + 9) // 10:
        raise OptionACostSafetyError("missing overlap ten-minute blocks")
    if not baseline:
        raise OptionACostSafetyError("empty non-event entry baseline")

    if not event_stress_quotes:
        raise OptionACostSafetyError("relevant externally sourced stress evidence absent")
    stress: list[tuple[Decimal, Decimal, Decimal]] = list(observations)
    source_manifest = cost_proof.external_stress_manifest_sha256
    seen: set[datetime] = set()
    for event in event_stress_quotes:
        timestamp = _utc(event.timestamp_utc, "event stress")
        if start <= timestamp < end or timestamp in seen:
            raise OptionACostSafetyError("event stress overlaps or duplicates observation")
        seen.add(timestamp)
        if not _sha(event.event_source_digest):
            raise OptionACostSafetyError("event source proof unavailable")
        if event.event_source_digest == source_manifest:
            # Separate event source fingerprint, not the manifest itself.
            raise OptionACostSafetyError("event source distinct origin not demonstrated")
        stress.append(_quote_fields(
            event.spread_usd, event.move_proxy_usd, event.gap_quote_proxy_usd,
            "external stress",
        ))

    def max_component(records: list[tuple[Decimal, Decimal, Decimal]], axis: int) -> Decimal:
        return max(row[axis] for row in records)

    current_spread = max_component(baseline, 0)
    current_quote_floor = max(slip_min, max_component(baseline, 1))
    current_gap_floor = max(gap_min, max_component(baseline, 2))
    current = _cent_up(
        current_spread + current_quote_floor
        + current_gap_floor + commission + holding
    )
    stressed_spread = max_component(stress, 0)
    stressed_quote_floor = max(slip_min, max_component(stress, 1))
    stressed_gap_floor = max(gap_min, max_component(stress, 2))
    stressed_components = _cent_up(
        stressed_spread + stressed_quote_floor + stressed_gap_floor
        + stressed_commission + stressed_holding
    )
    stressed = _cent_up(max(Decimal(2) * current, stressed_components))
    return CostRecipeResult(
        status="SYNTHETIC_MATH_ONLY_INDEPENDENT_BROKER_CALIBRATION_NOT_ADMITTED",
        eligible_baseline_minute_count=len(baseline),
        observation_minute_count=len(observations),
        external_stress_record_count=len(event_stress_quotes),
        current_spread_usd=current_spread,
        current_slippage_quote_proxy_floor_usd=current_quote_floor,
        current_gap_quote_proxy_floor_usd=current_gap_floor,
        current_adverse_cost_usd=current,
        stressed_adverse_cost_usd=stressed,
    )
