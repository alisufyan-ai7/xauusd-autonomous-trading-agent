# XAU/USD Phase 0 — Account/VPS Evidence Review

**Review date:** 2026-08-10 UTC  
**Verdict:** Accepted as one point-in-time Phase 0 account/VPS observation; not contractual authorization, not a production dependency acceptance, and not production readiness  
**Gate 0:** INCOMPLETE  
**Production implementation:** Not authorized

## 1. Frozen input

| Item | SHA-256 / result |
|---|---|
| `xauusd-phase0-evidence-20260809T235355Z-c6a411ea.zip` | `021f658ac2acb463d17e17d4ad2150f3fcb24750fce49789024e3b150645c62f` |
| Supplied ZIP sidecar | Exact match |
| Internal `MANIFEST.json` | `b032e078b7fce8d313dc6225d2878584712e95350e47ab42b174756896f12226`; sidecar match |
| Twelve internally manifested evidence files | Every SHA-256 and byte count matched |
| Archive path safety | PASS; no absolute path, drive prefix, parent traversal, or executable content |
| JSON parsing | 12/12 evidence JSON files PASS |

The ZIP uses Windows backslashes as separators. This produced a non-fatal warning in the Linux review environment; the names passed the path-safety check and were extracted without preserving directory traversal.

## 2. Collector and read-only evidence

The bundle reports collector `0.1.1`, policy `phase0-readonly-v1`, and a capture from `2026-08-09T23:53:55.209Z` through `23:53:58.336Z`. Its package provenance lists the same seven source hashes as the accepted `v0.1.1` package in the Phase 0 register. The bundle reports no collection errors.

The terminal reported:

- connected before and after;
- `tradeapi_disabled=true` before and after;
- `trade_allowed=false` before and after;
- no open orders or positions;
- no upload performed.

This is objective evidence that the required MT5 external-Python trading protection remained enabled during this run. It does not establish that unrelated software or a human could not trade independently, and it does not prove the legal permission to automate.

## 3. Separate identity/provenance fields

| Canonical field | Value | Provenance | Status |
|---|---|---|---|
| Contracting legal entity | `Exness (SC) Ltd` | Owner-reported Personal Area footer | Recorded, but the account-linked redacted document/agreement hash remains pending |
| Personal Area account label | `Pro — MT5 Demo — USD` | Owner-reported PA account card | Partially corroborated by MT5 evidence |
| MT5 account-serving company | `Exness Technologies Ltd` | Hashed `ACCOUNT.json:company` | Verified from bundle |
| MT5 trade server | `Exness-MT5Trial15` | Hashed `ACCOUNT.json:server` | Verified from bundle |
| MT5 terminal vendor/company | `MetaQuotes Ltd.` | Hashed `TERMINAL.json`, before and after | Verified from bundle |

These fields are not synonyms. MetaQuotes defines `ACCOUNT_COMPANY` as the company that serves the account; it does not define that field as the client's contracting legal entity. The terminal's own company field is separately `MetaQuotes Ltd.` No legal relationship among these names is inferred from the capture.

Official Exness material confirms that Exness (SC) Ltd is one of the Exness contracting entities and provides a separate Client Agreement and General Business Terms for it. That confirms the entity exists, but not that this specific account is governed by a particular version without an account-linked Personal Area/document record. [Exness legal documents](https://www.exness.com/legal-documents/)

## 4. Account and symbol facts observed

- Demo account: raw `trade_mode=0`; MetaQuotes identifies that enum value as demo.
- USD balance/equity: `10,000.00`; no current margin or exposure.
- Leverage: `1:2000`.
- Margin mode: raw `2`, mapped to `ACCOUNT_MARGIN_MODE_RETAIL_HEDGING`, where multiple individual positions can exist for one symbol. [MetaQuotes account properties](https://www.mql5.com/en/docs/constants/environment_state/accountinformation)
- Technical flags: account trading and Expert Advisor trading `true`; terminal trading `false`; external-Python trading disabled `true`; selected symbol trade mode raw `4`.
- Selected visible symbol: `XAUUSD` on path `Pro\Forex\XAUUSD`; five other XAU-containing candidates were recorded but not selected.
- Contract: 100 units; point/tick size `0.001`; tick value `USD 0.10` per lot-tick; minimum/step `0.01`; maximum `200` lots.
- Static stop/freeze fields: both raw `0`. These are point-in-time observations and do not justify hard-coding or skipping later runtime validation.

The PA label is consistent with Exness's current Pro documentation: no suffix, automated strategies supported generally, 0.01 minimum, and 1,024 pending orders for MT5 demo. Consistency is corroboration, not account-specific contractual authorization. [Exness Pro account](https://get.exness.help/hc/en-us/articles/17537794560540-Pro-account)

## 5. Independent data and calculation checks

| Check | Result |
|---|---|
| Six bar series | 512 rows each; 3,072 total |
| Bar ordering/shape | 0 duplicate timestamps, 0 non-monotonic transitions, 0 invalid positive-OHLC rows |
| Tick sample | 2,000 rows; 0 backwards transitions; 0 crossed/non-positive quotes; 11 rows share an exact millisecond timestamp |
| Current tick freshness | 3.857 seconds old at collector completion |
| Broker calculation vectors | 8/8 agree with independent contract/leverage math within USD 0.0050001 |
| Maximum profit-vector absolute error | Less than `0.000000000001` USD |
| Maximum margin-vector absolute error | `0.002119` USD, explained by broker result rounding to cents |

The independent oracle used the captured 100-unit contract, lot volume, price distance, and 1:2000 leverage. This validates the captured vectors; it does not prove future broker calculations or fills.

## 6. Material limitations and blockers

The 2,000-row tick array is not a latest-tail sample. It starts at `22:53:59.705Z` and ends at `23:18:48.001Z`, 2,110.335 seconds before run completion, because the collector requested ticks starting one hour earlier and reached its count cap. MetaQuotes documents that `copy_ticks_from` returns ticks starting from the requested date. The separate current tick is fresh, but the tick array is not accepted for a full-hour/latest spread distribution. [MetaQuotes `copy_ticks_from`](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py)

The bundle also explicitly lacks the authoritative weekly symbol trading-session table. Remaining blockers include:

- account-linked redacted proof that the intended account is contracted with `Exness (SC) Ltd`;
- exact Client Agreement/General Business Terms version or effective date;
- country of residence, client classification, and applicable restrictions;
- explicit review of entity/account/jurisdiction-specific EA, Python API, VPS, and automated-trading terms;
- authoritative XAUUSD weekly sessions;
- manual/unrelated-position coexistence policy;
- 24-hour VPS soak, restart, reconnect, update, and clock-drift evidence;
- the other risk, data/news, OpenAI, execution, and validation decisions already listed in the Phase 0 specification.

## 7. Acceptance conclusion

The received bundle is accepted as reproducible point-in-time evidence that the approved read-only collector ran on the intended Windows VPS and observed a technically usable Exness Pro MT5 demo target while the external-Python trading block remained enabled. It partially resolves the account/VPS discovery stage.

It does not authorize automated trading, production code, a real account, or any risk-changing call. **Gate 0 remains incomplete.**
