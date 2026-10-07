# XAUUSD historical-dataset licensing review R24

**Date:** 2026-08-23  
**Scope:** Public official/provider materials only; no acquisition, trial or purchase  
**Admission result:** `NO_PROVIDER_ADMITTED`

## Required rights and technical content

The Gate 0 replay corpus requires XAUUSD tick bid/ask or canonical bid/ask bars,
enough history to derive exact H4/H1/M15 frames, UTC timestamps, provider and
instrument semantics, and documentary permission for automated internal use,
local retention, derived analytical data, historical replay and audit retention.
Redistribution must remain prohibited. Treatment of retained evidence after
subscription/account termination must be explicit.

## Public-material review

| Candidate | Technical fit | Public-rights finding | R24 disposition |
|---|---|---|---|
| Dukascopy Historical Data Export | Strongest free technical candidate. The official export lists XAU/USD, multiple timeframes including tick data, and backtesting/analysis use. | The separate general Terms of Use limit use to personal non-commercial use and prohibit database construction and derivative works without written approval. The conflict is material for our retained derived replay corpus. | `CONDITIONAL_CANDIDATE_NOT_ADMITTED`; written permission is required before download. |
| HistData | Lists XAU/USD and says its files are suitable for MT4/MT5 backtesting. | No sufficiently explicit public legal grant was found for automated retrieval, retained derived data, replay and audit retention. Automatic updates and FTP/SFTP are separate access offerings. | `RIGHTS_UNRESOLVED_NOT_ADMITTED`; no download or subscription. |
| OANDA Trading API | Its API agreement permits internal use and necessary archival/emergency copies, and prohibits third-party redistribution. | Access is account/entity/agreement specific, license fees may apply, and termination requires destruction/return of licensed materials. The public agreement defines the rate feed as real-time and does not establish our required historical XAUUSD breadth plus post-termination audit retention. | `CONDITIONAL_COMMERCIAL_NOT_ADMITTED`; no account, trial or purchase activated. |
| OANDA Corporate FX Services | Provides historical precious-metal rates. | The public product is daily/corporate reference-rate oriented rather than the intraday bid/ask or tick corpus required for execution-aware replay; trial/subscription activation is prohibited without owner approval. | `CAPABILITY_MISMATCH`; not pursued. |
| Exness MT5 history | Best account-semantics cross-check. Exness officially documents downloading MT5 history and using it for backtesting. | The public instructional material does not expressly grant the full retention, derived-data and audit rights required by the admission gate. The owner has also closed further Exness-support outreach. | `SECONDARY_ACCOUNT_COMPATIBILITY_ONLY`; not the primary licensed replay corpus. |

Official sources reviewed:

- [Dukascopy Historical Data Export](https://www.dukascopy.com/swiss/english/marketwatch/historical/)
- [Dukascopy Terms of Use](https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/)
- [HistData download page](https://www.histdata.com/download-free-forex-data/)
- [HistData automatic updates](https://www.histdata.com/automatic-updates-forex-historical-data/)
- [OANDA Corporation API License Agreement](https://legal.oanda.com/oc/api_license_agreement_oc/en)
- [OANDA Corporate FX Services legal documents](https://www.oanda.com/corporate-fx-services/en/legal/)
- [OANDA Exchange Rates API plans](https://www.oanda.com/foreign-exchange-data-services/en/exchange-rates-api/api-plans/)
- [Exness historical-data/backtesting guide](https://www.exness.com/indices/algorithmic-trading/)

## Recommendation

Dukascopy is the first no-purchase clarification target because it is the best
technical match and the historical export is free, but it must not be downloaded
for this project until Dukascopy confirms in writing that the following are
allowed for internal, non-redistributed research:

1. automated or repeatable acquisition of the selected XAUUSD range;
2. local immutable raw retention and backups;
3. deterministic H4/H1/M15 transformation and derived features;
4. historical replay/backtesting and internal audit retention; and
5. continued retention of the sealed evidence needed to reproduce prior results.

No outreach is sent by this revision. No candidate satisfies the admission gate
from currently reviewed public materials, so the licensed replay blocker remains
open and no market-data bytes were acquired.
