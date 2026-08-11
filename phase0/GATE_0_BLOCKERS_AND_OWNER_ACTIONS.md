# Gate 0 Blockers and Owner Actions

**Status:** INCOMPLETE; production implementation prohibited

## Ranked blockers

| Priority | Category | Blocker | Completion evidence |
|---:|---|---|---|
| 1 | Owner input | Exness automation/API/AI ambiguity | Written Exness answer covering external Python, automated terminal-data access, external AI analysis, third-party VPS, Pakistan residence, and whether API Terms apply to MT5 Python. |
| 2 | Owner input | Missing account-linked evidence | Redacted screenshot showing intended Pro demo account and Exness (SC) Ltd footer together; no number/name/email/address. |
| 3 | Research | Missing API Terms of Use | Current Exness (SC) applicable API Terms captured, hashed, reviewed, and linked to the account/use case. |
| 4 | Owner input | Risk policy | Explicit selection/edits on `OWNER_RISK_DECISION_SHEET.md`; automatic unknown-position closure remains separately open. |
| 5 | Diagnostic | Authoritative XAUUSD sessions | Read-only, objectively verified session probe plus broker-published schedule; UTC/DST/holiday exceptions reconciled. |
| 6 | Diagnostic | VPS reliability | Non-trading 24-hour soak and restart/reconnect/network/clock/build ambiguity evidence with external-Python trading disabled. |
| 7 | Engineering specification | Execution/reconciliation state machine | Frozen `UNKNOWN`, `QUARANTINED`, `INCIDENT`, idempotency, partial-fill, uncertain-submission, OCO, restart and emergency rules. |
| 8 | Engineering specification | OpenAI Analyst contract | Frozen input/output schemas, semantic validation, freshness binding, reason enums, injection tests, pinned model, corpus, latency/cost and hashes. |
| 9 | Research + owner input | News/data provider and rights | Candidate comparison, protected events, SLA/outage rules, exact license/provenance including model transmission; no purchase without approval. |
| 10 | Engineering specification | Setup families | Mathematical definitions and acceptance/rejection tests for the five families; Zone B always a fresh trade, never recovery/averaging. |
| 11 | Engineering specification | Research governance | Dataset/version plan, chronological splits, realistic costs/fills, all-trial registry, predeclared PBO/DSR or alternative thresholds. |

## Exact next actions for the owner

1. Upload the promised **redacted Personal Area screenshot**. Hide account number, name, email, address and all identifiers; leave the account type and Exness (SC) Ltd footer visible.
2. Download and upload the **API Terms of Use** currently linked from Exness Legal Documents or your Personal Area.
3. Send Exness Support this question and return their written reply:

   > For my Exness (SC) Ltd account, country of residence Pakistan, Pro MT5 account, may I use (a) MetaTrader 5's external Python integration on my own third-party Windows VPS to read account/symbol/price data and later place trades, and (b) an external AI analysis service whose output cannot bypass deterministic risk controls? Please clarify whether Client Agreement Part C 2.3(A)/(G), Part D 4.1, the API Terms of Use, or any Pakistan/account-specific restriction applies. Please also confirm whether transmitting minimized or derived MT5 market data to that service is permitted.

4. Read `OWNER_RISK_DECISION_SHEET.md` and reply with “Approve A,” “Approve B,” “Approve C,” or your changes. This approves a specification baseline only, not trading.

No password, identity document, address, unredacted account number, or funds transfer is required.

