# News/Data Provider Shortlist for XAUUSD Event Protection

**Research date:** 2026-08-11; public-source conformance refresh 2026-08-12  
**Status:** procurement shortlist only; no purchase or provider admission  
**Scope:** scheduled-event avoidance and replay lineage, not release prediction or headline trading

## Finding

No candidate is yet admitted under the frozen provider-admission requirements. Public plan pages do not establish all required automation, VPS processing, storage, audit-retention, revision/cancellation, SLA, and derived-use rights. A signed/order-form rights confirmation and a sample-data conformance test are therefore mandatory before purchase or use.

## Shortlist

| Rank | Candidate | Published cost observed | Relevant official evidence | Licensing/operational conclusion |
|---:|---|---:|---|---|
| 1 | Trading Economics API | USD 149/month billed yearly (USD 1,788/year) for the entry API plan; Professional shown at USD 299/month billed yearly (USD 3,588/year) | The official [Calendar API](https://tradingeconomics.com/api/calendar.aspx) describes a near-real-time calendar, 24-hour updates, official-source actual values, prior revisions, and consensus. The official [API overview](https://tradingeconomics.com/api/) supports downloads and live-event subscriptions. | **Recommended for a time-limited technical evaluation, conditional on written rights clarification.** Best documented fit for scheduled macro events. Its public [terms](https://tradingeconomics.com/terms.aspx) grant only a limited personal, non-transferable licence and disclaim timeliness/accuracy; they do not expressly grant every required storage/VPS/audit right. Annual billing also creates avoidable commitment until conformance is proved. |
| 2 | Benzinga International Economic Calendar | Quote required | The official [product page](https://www.benzinga.com/apis/cloud-product/economic_calendar/) states intraday delivery, international coverage, history from 2003, JSON/XML, importance/category filters, revisions, and platform/API integration. | **Best enterprise-contract alternative.** Public price and the specific retention/automation licence are unavailable, so obtain a written quote and rights matrix. EST delivery requires explicit timezone/DST conformance testing. |
| 3 | EODHD Economic Events Data API | Fundamentals USD 59.99/month or USD 599.90/year; All-in-One USD 99.99/month or USD 999.90/year | The official [Economic Events API](https://eodhd.com/financial-apis/economic-events-data-api) exposes past/future events from 2020. The official [pricing page](https://eodhd.com/pricing) lists Economic Events under fundamental data and the prices above. | **Low-cost evaluation fallback only.** The public plans are identified as personal use; commercial use is by request. The pricing page also warns that its data may not be real-time or accurate and may be inappropriate for trading purposes. Must not be admitted without a commercial/automation rights response plus schedule-completeness and latency evidence. |

Published prices are snapshots from the research date, exclude tax, and must be reconfirmed at purchase. Trading Economics pricing text is dynamically rendered; the USD 149/299 figures were visible in its official search result but should be reconfirmed in a formal quote before approval.

## Required pre-purchase questions

Send the same written matrix to candidates; a marketing reply is insufficient:

1. Does the quoted licence allow an individual-owned automated trading risk-control service to fetch the calendar on a Windows VPS?
2. May raw responses be encrypted and retained for immutable audit/replay, and for how long?
3. May the system store normalized event records and derived lock states indefinitely?
4. Are redistribution and external-AI transmission unnecessary if all processing is local? Confirm that keeping the provider payload local is permitted.
5. Are stable IDs, original scheduled time, UTC/timezone, revisions, postponements, and cancellations supplied? What are their semantics?
6. What are the rate limits, status/incident feed, uptime/latency SLA, support escalation path, and historical-calendar coverage?
7. Does the feed cover all frozen Tier 1/Tier 2 events, including separate FOMC statement and press-conference records and scheduled Fed speakers?
8. Can a trial/sample be tested before an annual commitment? What refund/cancellation rules apply?

## Recommendation and owner decision packet

Do **not** purchase yet. First request:

- Trading Economics: trial/monthly evaluation option, full rights answers, and a monthly rather than annual commitment;
- Benzinga: quote for International Economic Calendar with internal automated use and audit retention;
- EODHD: commercial-use quote and explicit fitness/latency position for event-risk controls.

If Trading Economics supplies acceptable written rights and a non-annual evaluation, it is the preferred first operational provider. Otherwise compare the Benzinga enterprise quote. EODHD should be used only if its lower cost is accompanied by satisfactory commercial rights and empirical completeness/latency results.

Official BLS, BEA, Federal Reserve, and DOL schedules remain authoritative reconciliation sources for their own releases. They do not by themselves remove the operational-provider health requirement, and undocumented page scraping remains prohibited.

## Gate effect

Provider procurement remains open. Until one candidate passes contractual review and conformance tests, Event Guard remains `SOURCE_UNHEALTHY`; this blocks automated entry but does not block offline corpus testing or read-only diagnostics.

## 2026-08-12 public licensing/conformance review

| Requirement | Trading Economics | Benzinga International Economic Calendar | EODHD Economic Events |
|---|---|---|---|
| Scheduled macro calendar | PASS on public documentation | PASS on public product page | PASS on public documentation |
| Update timeliness | Nearly real-time; REST updates and calendar WebSocket documented | Intraday/near-instantaneous marketing claim | Not established; site warns data may not be real-time |
| Stable event identity | `CalendarId` documented | Not established publicly | Not established publicly |
| Timezone semantics | Streaming `date` documented as UTC | EST is stated; DST normalization requires test | Timestamp supplied but timezone semantics not established publicly |
| Importance classification | Numeric 1/2/3 documented | Importance filtering is described | Not established in the documented response fields reviewed |
| Revisions/update lineage | `LastUpdate`, `Revised`, update endpoint and point-in-time history documented | Revision support is claimed, but exact mutation semantics need sample/contract | Exact revision/cancellation semantics not established |
| Cancellation/postponement semantics | Not established publicly | Not established publicly | Not established publicly |
| Historical audit suitability | Point-in-time endpoint explicitly documented for backtest/audit | History from 2003 | History from 2020; point-in-time mutation lineage not established |
| Rate/streaming controls | General 2 requests/second; calendar 1,000 rows/request; calendar WebSocket documented | Quote/sample required | 100,000 requests/day in general paid terms; endpoint-specific suitability unproved |
| Public licence fit | **FAIL/AMBIGUOUS:** public terms are limited, personal, non-transferable and revocable | **UNRESOLVED:** provider markets licensing to financial platforms, but exact internal automation/storage terms and price require contract/quote | **FAIL for self-serve plan:** public prices are personal use; commercial use needs a quote; stored copies must be deleted within one month after termination absent different written terms |
| SLA/support | No adequate public operational SLA found | Enterprise support marketed; contractual SLA not public | Commercially reasonable efforts, but no uninterrupted/error-free warranty |

### Public-review conclusion

1. **Trading Economics remains the technical first choice** because it is the only reviewed candidate publicly documenting stable IDs, UTC streaming time, importance, update/revision fields, point-in-time audit history, and calendar streaming together.
2. **It is not approved for purchase or production admission.** The USD 149/month Standard plan is billed yearly (USD 1,788/year), while public terms do not establish the required automated internal VPS, immutable audit retention, normalized derivative retention, or post-termination evidence rights.
3. **Benzinga is the contractual alternative**, particularly if it will quote a short evaluation and explicitly grant internal automated risk-control and audit rights. Public price, stable IDs, timezone/DST semantics, cancellations, retention and SLA remain unverified.
4. **EODHD is rejected as the primary Event Guard candidate at this stage.** Its self-serve licence does not fit a project/business use without commercial approval, its public terms require data deletion after termination, and it disclaims real-time/accuracy suitability. It may be reconsidered only as a low-cost secondary reconciliation source under a specific written commercial licence.

### Recommended next procurement step — requires no purchase

Request written trial/quote responses from Trading Economics and Benzinga using the eight-question matrix above. Prefer a 14–30 day non-renewing evaluation. Do not submit payment details or accept annual terms. Admission requires a sample feed to pass timezone/DST, stable-ID, revision, cancellation, completeness, stale-source, rate-limit and source-disagreement tests against official BLS/BEA/Federal Reserve/DOL schedules.

Current recommendation for owner approval: **authorize quote/trial outreach to Trading Economics and Benzinga only; authorize no purchase.**
