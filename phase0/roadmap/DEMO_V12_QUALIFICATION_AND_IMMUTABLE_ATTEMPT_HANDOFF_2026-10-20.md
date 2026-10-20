# DEMO-ADMIT v1.2 — owner-independent qualification and immutable-attempt closure (2026-10-20)

**Disposition: STOP CONDITION B. No near-term four-hour Exness XAUUSD window can CURRENTLY be qualified from admissible evidence.** This is an epistemic/provenance failure, **not** proof that the broker cannot supply a four-hour eligible window on a given date. The official source archive, date-specific XAUUSD instrument schedule, broker event health and future first-run private VPS facts are missing. The run template remains intentionally **NOT EXECUTABLE**. No VPS/MT5 interaction occurred.

## Frozen GitHub lineage and historical immutability

- main `ccaa8338aecee8bd3afbc358644410dff6c512e5`, unchanged at branch reconciliation.
- owner-approved frozen v1.2 **DESIGN** PR #13 `847829378956670e8936bf46c82e685de41145fd`; offline preflight PR #14 `9d768fcfd160b3ccfc92ecef44fe040da6b77db6`; initial unexecuted collector preparation PR #15 `cbb8f3bf0fc0e46fb187f62a3e849341756a4f80`. Current successor PR #16 branch `implementation/demo-v12-immutable-failure-evidence-20261019`, stacked on #15, DRAFT/UNMERGED.
- Frozen historical v1.0 registration Git blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77`; v1.1 `5210056f0a07faad9225e24228392f43090c5561`; owner-approved v1.2 `c7dcf520fe2a3b12437cec6a1b5dd06c25494d5f` all unchanged. PCR3 FAIL/QUARANTINE and all older Gate failures immutable; no attempt reruns/erasures and no change to existing scheduler.

## Independent official-source screening — SOURCE FACT vs SOURCE ADMISSION

Latest machine-readable dated status: `phase0/roadmap/DEMO_V12_SOURCE_CANDIDATE_QUALIFICATION_2026-10-20.json`; earlier 2026-10-19 source record retained verbatim.

We reviewed primary/official website *identities and readable page text*:
- Exness `https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours`: date-filtered instrument-specific schedule is required for XAUUSD trading, quote-only/close-only, maintenance/holidays/DST; generic summer US New York vs London overlap three hours (13:30–16:30 UTC), winter two hours (14:30–16:30 UTC). 240-minute OBSERVATION may include distinct broker-eligible pre-overlap minutes but all 240 must independently be shown XAUUSD open/liquid. Public generic center table **CANNOT authenticate** actual dated XAUUSD tradeability. Exness rollover warning and holiday exceptions further defeat assumptions.
- BLS `https://www.bls.gov/schedule/2026/10_sched.htm`: Tuesday Oct 20 State Employment/Unemployment at 10:00 ET = 14:00 UTC; Wednesday Oct 21 Usual Weekly Earnings at 10:00 ET = 14:00 UTC. Oct 28 additional 10:00 ET BLS releases. No dates are certified clear by absence from only this schedule.
- BEA `https://www.bea.gov/news/schedule/`: Oct 29 08:30 ET GDP Advance and Personal Income/Outlays = 12:30 UTC.
- Federal Reserve `https://www.federalreserve.gov/newsevents/2026-october.htm`: Oct 27–28 FOMC, 28 Oct statement/press, plus routine statistical releases. Exact full-source and project tier classification unknown.
- Census `https://www.census.gov/econ/indicators/release_schedule.html`: Oct 28 Advance Economic Indicators 08:30 ET. Census `https://www.census.gov/wholesale/index.html`: **tentative** revisions Oct 26 10:00 ET = 14:00 UTC, so Oct 26 cannot simply be called event-free; prior housing 20 Oct 08:30 ET relevant.
- DOL `https://www.dol.gov/agencies/eta/ui-claims`: weekly Thursday claims release generally 08:30 ET, including Oct 22 subject to independently verified dated original schedule/holiday exceptions.

All authorities are public official domains, **but our tools returned processed website text, not exact original HTTP response/document bytes**. Direct container HTTP download of the BEA source was attempted and failed due to external network DNS unavailability. The original-source SHA-256 for Exness/BLS/BEA/Fed/Census/DOL and independent TLS/origin evidence therefore remain **NULL**, not fabricated. Exness dynamically generated *selected date + XAUUSD* schedule was not recovered, and actual broker account fees/quote-only/calendar/event/source health cannot be probed without VPS. Thus this evidence is **for screening only**, not an admissible run packet.

Frozen `src/xauusd_agent/guards/event_guard.py` sets pre/post `TIER_1` 30 minutes and `TIER_2` 15 minutes; tentative/suspended, stale/unhealthy/disagreeing/missing sources or unnormalized/shock inputs block entries. Actual date-specific Event Guard tier/time, normalization and health remain UNKNOWN. The fixed `v12_offline_source_packet` layer never upgrades caller-provided hashes/flags to independently authenticated provider truth.

### Prospective date screening (not a registration)

| UTC DATE | Official scheduled issue / review | QUALIFIED? |
| --- | --- | --- |
| Tue 2026-10-20 | Census housing 12:30 + BLS state employment 14:00 | NO |
| Wed 2026-10-21 | BLS usual weekly earnings 14:00 | NO |
| Thu 2026-10-22 | Recurring DOL UI claims release 08:30 EDT (12:30 UTC), exact dated archive/normalization missing | NO |
| Fri 2026-10-23 | Earliest worthwhile date for further **calendar screening only**; absent full original archive, live unscheduled Event Guard and broker instrument schedule | NO |
| Mon 2026-10-26 | Tentative Census wholesale historical revisions 10:00 EDT (14:00 UTC) + UK DST switch 25 Oct; actual XAUUSD schedule and Event Guard unknown | NO |
| Oct 27–29 | Census/BLS/FOMC/BEA conflicts need explicit classifications | NO |

**No exact four-hour UTC observation or eligible overlap selected.** Historical synthetic test dates 2026-10-20/26 are not real run dates. The previously illustrative 12:30–16:30 is NOT approved. Absence of a known release in an incomplete schedule is NOT evidence that `NORMALIZED=true` or `EVENT_GUARD_HEALTHY=true`.

## Resolved partial-failure preservation weakness — successor implementation

PR #16 adds `demo_adapter/scripts/v12_attempt_journal.py` and `demo_adapter/scripts/v12_journaled_readonly_port.py`, wires both into `v12_windows_mt5_readonly_host.py` and SHA pins into `v12-readonly-collector.ps1` / `v12-readonly-verifier.ps1`, with native Windows PowerShell 5.1 and synthetic adversarial tests. The program creates, *before any MT5 import/initialize*, a per-registration `v12-attempt-<registration_sha256>.jsonl` in the pre-existing outside-worktree private folder by `O_CREAT|O_EXCL`. Start is fsynced to disk, as are all terminal/exposure reads, 5-second XAUUSD polls and each raw true-tick ten-minute chunk including source ordinal/flags. If a read, parsing, disk write or validation fails it aborts, writes an explicit `FAIL_CLOSED` where possible and never resumes under that SHA; if killed/crashed/loses power without terminal entry, verifier treats it as `INCOMPLETE_FAIL_CLOSED`. Private complete raw file creation requires a final independently linked `COMPLETED_RAW_NOT_ADMITTED` event and exact matching SHA. A second attempt with the same registration hash is rejected, even if a different output filename is supplied.

This mechanism **preserves partial failure evidence** and prevents ordinary automatic rerun/relabeling, **but is not strong cryptographic non-repudiation against a Windows administrator deleting/editing all files**. Hash chains detect edits only when the original journal or independent digest is retained. Owner should preserve a separately reviewed protected/external immutable checkpoint or independently attest/store the first-attempt path and final digest once first VPS execution is separately authorized. Fsync does not guarantee survival of catastrophic disk/controller failure. None of this confers a real trading permit.

### Revised exact source SHA256 (UTF8/LF Git bytes)

Pinned manifest `phase0/roadmap/DEMO_V12_READONLY_SOURCE_SHA256_PIN_MANIFEST_2026-10-19.json`, supersedes **only for future preparation** the immutable original PR15 pins. Current revised:
- `demo_adapter/scripts/v12-readonly-collector.ps1`: `94d04fa7cd43dc7c92220808410f3135cf91256c80caec59bd3295ea01050c50`
- `demo_adapter/scripts/v12-readonly-verifier.ps1`: `fe9b19f074f26b3479204cddc8774f504613adcc915af154b6a28b6b60ebedd3`
- `demo_adapter/scripts/v12_windows_mt5_readonly_host.py`: `5a3f4bab1f775739dcfb1c4c0a1d15ce2b3977c0309b520a4f63227425110c46`
- `demo_adapter/scripts/v12_attempt_journal.py`: `547131361b690e95c6718734b6de727e812346e92af8c1a20ced4f6dbc12ef06`
- `demo_adapter/scripts/v12_journaled_readonly_port.py`: `085d6d51c4634e8ca60c59f9b78c381c6b8d3a7231eebc16ac73843d35cd1cd9`

Four unchanged v1.1 dependency pins remain in the same manifest. The independently tested LF `.gitattributes` scope ensures source-hash verification on Windows and Linux; native `Get-FileHash` on the owner-approved VPS checkout is additionally required **before** any later first execution. Historical PR15 hashes stay as immutable evidence of previous code state and must not be silently reused.

## Remaining VPS-only/source-origin facts; exact next boundary

- Date-specific, truly authenticated Exness XAUUSD instrument/full-eligible trading schedule and holiday quote/close-only boundaries with original protected bytes+SHA; independent BLS/BEA/Fed/Census/DOL archived bodies/time/origin; Event Guard current classified full calendar, health, normalization and shock status; independently verified full four-hour broker-eligible market **before any real UTC window registration**.
- Actual demo account identity, symbol tick-loss USD conversion, fees/swap/admin, real conservative proxy slippage/gap/stress, unknown/pending exposures. Actual execution slippage cannot be measured by quotes. Quote movement is not realized fill slippage.
- Owner-approved private existing Windows destination and exact terminal64.exe path/process, immutable external first-attempt retention mechanism, final reviewed registration/code/native hashes, and explicit **single first-run owner confirmation**.
- Real `CURRENT_ADVERSE_COST` only from independently verified non-event entry overlap; `STRESSED_ADVERSE_COST` conservatively from whole 4h + separately admissible stress/event evidence. **No numerical value admitted** and no offer to trade.

**STOP B** until independently admissible original sources and date-specific Exness/XAUUSD/Guard evidence can establish a qualified window. Do not provide or execute speculative PowerShell command. A FUTURE eligible single approval, **not requested now**, would be: `APPROVE FIRST EXACT SOURCE-QUALIFIED XAUUSD 4H VPS READ-ONLY CAPTURE AT [FROZEN GITHUB PR/UTC WINDOW/ENTRY SUBWINDOW/SOURCE SHA256/CODE SHA256/PRIVATE PATH/TERMINAL] — NO TRADING`. PR #8–#16 remain draft and unmerged; no VPS/MT5, Task Scheduler or PCR3 mutation, no Python trading enablement, no demo/live order submit/modify/cancel/close.
