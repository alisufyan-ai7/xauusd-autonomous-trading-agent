# ADR-2026-10-22-002 — V2 engineering priorities authorized, broker activation not authorized

**Status:** Owner-accepted ENGINEERING WORK ORDER with known unfinished work. Not a policy/risk amendment, strategy performance admission, DEMO broker order or LIVE approval.
**Owner instruction (2026-10-22 local):** proceed with five engineering priorities: (1) establish exact Python3.12 CI, (2) extend read-only W1/D1/M5/M1 on top of existing H4/H1/M15, (3) create real objective trading candidates rather than manual predicate injection, (4) integrate existing non-authoritative AI Analyst and Event Guard, (5) build and validate a DEMO execution/position management lifecycle as path to eventual 48h autonomous DEMO.

## Interpretation / WHY

- User wants fast progress toward a genuine autonomous XAUUSD agent running on Exness **Pro**, without screenshots or manually provided trade directions.
- The previous v2 specification PR31 was approved and merged `main=95875ccf1bddc43491ced1dd4358057b62b7800e` and is the scope baseline.
- Earlier PR32 only contains execution-disabled context/selector and authored synthetic tests; CI jobs report failure before steps. We must fix testing instead of falsely claiming the source is validated.
- Engineering authority permits isolated implementation, synthetic tests and documentation in draft GitHub PRs. It does **not** automatically grant merging untested code into production, changing installed VPS tasks, enabling terminal Python trading, making billable AI production requests, or sending DEMO/LIVE broker orders.

## Recorded dispositions at this checkpoint

| Priority | Status | Evidence |
|---|---|---|
| 1 Python3.12 CI | **BLOCKED/UNDETERMINED** | PR32 Actions `39758170391` and `39758170378` failed in seconds with missing steps/logs; local execution environment only Python3.13 and cannot download 3.12 due DNS isolation. Cause must be established from account UI or native Windows run; do not assume account quota or code defect. |
| 2 Seven-frame read-only MT5 ingestion | **CODE PREPARED / NOT BROKER TESTED** | Child implementation adds exact-admitted DEMO fingerprint, company, server, USD and raw mode=0 guard, plus W1/D1/M5/M1 source and H4/H1/M15 reuse. Five synthetic tests authored. No VPS connection or live quote/source proof. |
| 3 Objective strategy detection | **NARROW TPB RESEARCH HYPOTHESIS PREPARED / NOT FROZEN STRATEGY** | Technical Zone A subset from H4/H1/M15 completed bars, EMA/ADX, ATR and confirmed swings. No full first-touch, all locations, expiry, costs, OOS or profitable edge. Always research only, never order. |
| 4 AI/Event Guard | **SHADOW BRIDGE PREPARED / REAL SOURCES DISCONNECTED** | Calls accepted local pure Event Guard on externally acquired official observations and strict default-disabled AnalystClient. Synthetic offline tests, no cloud call and no source-healthy default. |
| 5 DEMO execution/management | **PAPER LIFECYCLE ONLY / REAL RUNTIME UNBUILT** | Synthetic in-memory finite state with single-known-position, no stop widening, known exit, ambiguous-result quarantine. Seven synthetic tests; no actual broker order, journal persistency or risk-based sizing. |

## Decision boundaries retained

- Current frozen risk Policy A (including 0.25% planned loss and 0.01 lot maximum, M1, daily/weekly and drawdown) remains unchanged; all alternative higher fractions were research-only suggestions.
- Exness **Pro only**; never Standard Cent. Only formerly approved dedicated Pro DEMO account fingerprint; no Pro LIVE identity admitted.
- `pcr3-execution-disabled-e0383a50e2cc` scheduled task, staging S2 PR24/26, experimental PR29 and PR32 remain unchanged and unmerged. All historic Gate0 R4/R34/R35 fails preserved.
- No direct ChatGPT VPS/RDP control or verified 24/7 broker monitoring at present; 48h DEMO operational trial has **not started**.
- No broker trading-action permissions, no Python external-trading toggle, no LIVE funding, no production OpenAI call approved in this ADR.

## Next review/implementation gate

Use the child's source and review tests strictly as unverified until Python3.12 native exact-head PASS evidence exists. Require independent real read-only Exness Pro profile session proof and official Event Guard provider source health; complete P0-SETUPS-001 technical predicates, replay/OOS and cost calibration; implement broker Policy A, durable transactional journal and known-position manager behind a separately sealed executor. Explicit owner APC is required before any DEMO or LIVE broker action. Only after admitted execution release and monitoring do we begin the 48h DEMO clock.

**Cross-links:** v2 spec PR31 merged, parent draft PR32, child implementation document `phase0/roadmap/AUTONOMOUS_PRO_V2_PRIORITIES_2_TO_5_IMPLEMENTATION_2026-10-22.md`. Append later corrections; never overwrite the original trial or failed CI status.
