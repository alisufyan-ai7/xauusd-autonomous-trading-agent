# ADR-2026-10-22-003 — Sparse crossframe buckets are not evidence of corrupt data or approved closures

**Status:** engineering diagnosis/review decision, pending independent session metadata and real read-only forensic evidence. Does not amend frozen strategy, Gate 0, Risk Policy A or broker permissions.

## Immutable new observation

At 2026-10-22T13:32:33.856256Z the owner-attended read-only XAUUSD DEMO PR34 probe (wrapper source `a7114eff0649fb843095300042a0114933cd7033`, Python pin `48128c83130aa767b047d382f113d4510cb3ac4d`) examined **564 fully covered parent buckets**, with **no OHLC/volume disagreement reason** but refused parity due to `D1_H4_MISSING_OR_MISALIGNED_CHILD_BARS` and `H4_H1_MISSING_OR_MISALIGNED_CHILD_BARS`. Seven frame counts complete, XAUUSD Exness DEMO exact attested fingerprint matched, external-Python trading disabled, zero order API calls. Unclassified gap counts D1=30 H1=22 H4=9 M1=0 M15=11 M5=1 W1=0. Source and exact details in immutable `phase0/evidence/V2_PR34_CROSSFRAME_READONLY_FAIL_CLOSED_2026-10-22.json`, PR34 issuecomment `6342096032`.

## Why this is not automatically a market-data failure

The original pure oracle demands every nominal 4h child of a D1 and every nominal 1h child of a 4h parent. Under real XAUUSD trading sessions, daily rollover/weekends/holidays may contain legitimately **no candle** because no quote was generated; a parent bar need not have every nominal child slot, even if all observed lower candles aggregate to the same parent OHLC/volume. Official Exness [instrument trading hours](https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours) updated 2026-09-29 states that gold is usually closed during rollover, and DST/holidays/maintenance change schedules. This page is **context, not an independently admitted complete hour-by-hour Exness instrument calendar**. It does not establish why these specific missing buckets occurred, and no matching raw price series were retained in the owner-pasted output.

## Decision / intended code correction

**Preserve FAIL_CLOSED and strict oracle**. Add a separate non-authoritative read-only forensic inventory of up to six representative D1/H4 and H4/H1 parent open timestamps per pair, missing/misaligned child timestamps, expected and observed child counts, and whether existing child OHLC/volume would equal the parent aggregate (boolean only). Never emit prices, account IDs or credentials, assume missing time is officially CLOSED, manufacture bars, waive a cost/data gate, or permit trading. Keep `strict_crossframe_pass=false`, `session_classification_admitted=false`, `execution_permitted=false` in the independent forensic DTO. Before accepting any gap, acquire and hash broker-specific Exness Pro XAUUSD holiday/regular schedule for the **affected UTC windows** and check exact missing child timestamps against verified CLOSED intervals. A missing bar during a verified OPEN interval remains a fatal data-quality failure.

## Additional acceptance boundaries

- W1 Sunday UTC is a logical broker candle bucket, not proof Sunday 00:00 is a tradable time or the actual market closing boundary.
- Strict OHLC/volume parity among 564 full buckets is a real read-only observation **only for those complete buckets**; sparse buckets, missing bars and full session-gap admission remain unresolved.
- Source/test Python3.12 CI success is not real Exness forensic execution. New prospective diagnostic remains NOT_RUN on owner VPS until they run a separately pinned read-only script.
- PR32/PR33/PR34 all draft/unmerged. Production main untouched. External Python trading disabled; no DEMO/LIVE orders, no restart of installed PCR3, no real-money approval, no loosening Policy A. Keep R4/R34/R35 and earlier owner diagnostic fails immutable.

**Next:** after Windows+Ubuntu native source testing, perform one attended read-only forensic capture on the dedicated DEMO profile, review UTC buckets versus dated official broker schedule, and update a separately dated evidence packet and gate matrix. Do not call this a chronology PASS until all required source evidence is present.
