# V11 2026-10-21 12:30–16:30 UTC capture — minimum source gate

**State:** PROSPECTIVE CANDIDATE, NOT AN EXECUTABLE RUN REGISTRATION, NOT MT5/VPS APPROVAL. Owner requested earliest safe DEMO lifecycle; accepted 4h session-band clarification is frozen in `DEMO_V11_RESTRICTED_SESSION_4H_BAND_OWNER_CLARIFICATION_2026-10-21.json`. Prior 2026-10-22 candidate is **superseded for priority only**, not erased. Staged PR28 exact source `90c3e93330edeee58a0709a41e7393f7818f4ea8` at private VPS directory stays execution-OFF. No restaging.

## Target and session evidence

- Candidate `2026-10-21T12:30:00Z` to `2026-10-21T16:30:00Z` (Pakistan 17:30–21:30), one 240min capture; 12:30–13:30 London-only and full 13:30–16:30 London/New York summer overlap. Alternative 13:30–17:30 exists but not concurrently approved as a retry. Operator must be present before beginning.
- Official Exness [instrument-hours and centre-hour reference](https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours): trading servers UTC+0; London summer 08:00–16:30, New York 13:30–20:00. XAUUSD specific date custom schedule lives in the **dynamic date/instrument selector**, which has NOT been independently downloaded/hash-validated here. Static page was updated July 29, 2026 at 06:33 per retrieved page; text alone does **NOT** prove date-specific XAUUSD quote-only/open/closed status or unscheduled changes. The stage must remain unused until this instrument/session proof is obtained and checked.
- Exness normal summer rollover 21:00 UTC (well outside candidate) but quote spikes/maintenance/shocks may still occur and demand deny; do not equate normal opening with guaranteed tick coverage.

## Checked official-event evidence vs. frozen protective taxonomy

Selected original project Event Guard `src/xauusd_agent/guards/event_guard.py` and independent event oracle `phase0/validation/event_guard/event_guard_oracle.py` at production main `2848c98940def262459fd89d5897c6f63dd6aadb`: **Tier 1** employment report/NFP, CPI, personal income and outlays/PCE, FOMC statement/press conference/minutes; **Tier 2** weekly jobless claims and enumerated Fed communications. Frozen pre-/post-windows 30min/30min Tier1 and 15min/15min Tier2. Source unknown/disagreement, coverage incomplete, uncertain or shocks are **not healthy**; never interpret missing source as no events.

Official schedule review on 2026-10-21 from current web lookup (links below; **source-page raw-body SHA and all agency freshness metadata NOT independently frozen**, so this is informational evidence and not admission):
- [BLS Oct 2026 schedule](https://www.bls.gov/schedule/2026/10_sched_list.htm): Oct 21 10:00 Eastern / 14:00 UTC **Usual Weekly Earnings of Wage and Salary Workers Q3 2026**; this is not explicitly classified as frozen Tier1 NFP or Tier2 weekly *initial claims* (do not conflate either). Event is **WATCH ONLY under existing taxonomy**, not a licence to ignore actual quote shocks.
- [New York Fed Oct 2026 indicator calendar](https://www.newyorkfed.org/research/calendars/i-oct26.html): Oct 21 10:00 Eastern / 14:00 UTC **Outlook-at-Risk**; not classified as frozen Tier1/2; WATCH ONLY, assess shock/spread freshness independently.
- [BEA 2026 full schedule](https://www.bea.gov/news/schedule/full): lists Oct 6 and Oct 29 relevant US releases but **no Oct 21 PCE/GDP** on currently retrieved page. No evidence from this alone that other agencies are healthy.
- [Federal Reserve news/events calendar](https://www.federalreserve.gov/newsevents.htm): daily CP and H15 monetary statistics listed Oct 21; no confirmed Oct 21 FOMC statement/press conference/minutes in retrieved page. Event Guard **Fed communications and late revisions must be rechecked**, not inferred absent by a single static page.
- [Census economic indicators](https://www.census.gov/economic-indicators/2026-release-schedule-list-view.html) public page does not reliably expose date-specific structured 2026 entries to the current text extractor. Since Census is watch-only under frozen taxonomy, record source visibility limitations rather than inventing a pass.
- DOL weekly initial claims is generally Thursday, Oct 22; must still verify frozen authoritative source health and any exceptions before claiming full coverage (Oct21 Wednesday candidate does not automatically waive the health requirement).

**Static preliminary disposition:** NO specifically classified Tier1/2 event identified inside 12:30–16:30 from the successfully read public pages. `LIVE_EVENT_GUARD_HEALTH_AND_SOURCE_HASH=UNPROVEN`, `BROKER_XAUUSD_DATE_SPECIFIC_HOURS=UNPROVEN`, `SHOCK_STATE=UNPROVEN`. Therefore **`session_event_eligibility_prechecked=false` remains mandatory in executable run record**, despite preliminary classification. Do not set it true until final authoritative coverage, source agreement, holiday calendar and fresh eligibility checks succeed and are hash bound.

## Already pinned non-broker source identities

The fixed execution-OFF VPS stage proved all 5 source components. Future exact run uses:
- `v11_windows_readonly_host.py` SHA256 `5062645291bd2768d133c9b37fa2a469c3fdacbc30ae38987ebe30e148d55e7a`
- `v11_readonly_collector.py` SHA256 `ca81f62362d56b74fb7f4b9ab5768f44913498da3a4dc861fbad0d8824d6833d`
- `v11_windows_readonly_capture.ps1` SHA256 `99d71cfbf7432817d320395e162d2793b2aa9c97863bf0701530704d5f89ee2c`
- Official `source` URLs and unhashable web-rendered views do **not** constitute exact raw SHA256 agency/broker source checks.
- See `DEMO_V11_STATIC_READONLY_ALLOWLIST_VERIFICATION_2026-10-21.json` (static code only; runtime broker proof missing). No trading methods may be called; current stage `EXECUTION_OFF__NO_CAPTURE_AUTHORIZED` must stay unmodified.

## One narrow genuine source-contract issue to bind in eventual capture permission

Original v1.1 `sources_and_capture.read_only_functions_allowed` lists `initialize,shutdown,terminal_info,account_info,symbol_info,symbol_info_tick,copy_ticks_range,positions_get,orders_get,last_error`. The final staged read-only host additionally **calls `history_deals_get(start-90d,start)`** to source account-specific historical XAUUSD commission/swap proof candidates. This call is read-only and does not cause a trade, but was **not literally in the original enumerated allowlist**. Do NOT pretend the frozen method authorized it. Explicitly include this exact read-only function in the future one-run owner capture authorization, or prospectively register a narrow collection amendment and validate source contracts; otherwise block this staged host. A 90-day **account trade-history lookback is not 90 days of market-condition calibration**, which remains out of scope.

## Non-secret info still required from attended owner OS-only preflight (NOT currently permitted)

- Existing `terminal64` process ID **NOW**, exact executable path, start time, Python3.12 executable existence and SHA pin, stage marker and five component rehashes from the pre-existing stage, UTC OS clock. Never reuse old PID `6216` as though fresh.
- Confirm Navigator shows only admitted DEMO and verbally attest no retained live-account login credentials/no other operator account switch.
- **No trading API, MT5 import/initialize, quote/history read** in OS-only preflight. Any VPS read requires an owner-facing bounded authorization distinct from the capture.
- Authoritative future run record (full source hashes, static allowlist, valid terminal PID, owner ID and capture approval, concrete tolerance `100ms`) must be committed and hash-pinned **before** any read-only MT5 attach/capture. Note: `history_deals_get` and `mt5.initialize` require explicit read-only approval even though they do not send orders.

## Result and next boundary

`EARLIEST_OCT21_4H_CANDIDATE_PREPARED; NOT_CAPTURE_AUTHORIZED`. Missing date-specific Exness XAUUSD schedule raw source hash/attestation, live full Event Guard source health, current terminal OS identity and **separate owner MT5 read-only approval**. No further staging or redesign, no multi-day or week-reopen calibration, no live/demonstration broker order. If a critical missing source cannot be proved before 12:30 UTC, choose another future date **prospectively**; never start late or backfill. Real money permanently prohibited.
