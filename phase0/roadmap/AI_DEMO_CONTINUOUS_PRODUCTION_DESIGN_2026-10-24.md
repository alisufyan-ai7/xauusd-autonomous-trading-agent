# V2 AI-powered autonomous Exness Pro DEMO — complete delivery design

Updated: 2026-10-24, after verified VPS cutover. Start with [AGENT_START_HERE](../../AGENT_START_HERE.md), [current machine status](CURRENT_DEMO_RUNTIME_STATUS.json), [operational next steps](DEMO_RUNTIME_HANDOFF_AND_NEXT_STEPS_2026-10-24.md) and the original Oct21–23 ADRs. **Do not rewrite the original owner requirements or historical Gate0 failures.**

## Product and hard distinctions

The owner wants a continuously running Exness **Pro MT5 DEMO-server** XAUUSD trader (genuine broker orders, virtual account funds), not one attended test order or paper-only signal. It must seek opportunities whenever the broker market is genuinely tradable, choose BUY/SELL/NO_TRADE, manage only its own observed positions, keep local evidence, improve through controlled research, and ultimately demonstrate positive *net-of-cost* out-of-sample expectancy. Profit is not guaranteed. LIVE real-money account is excluded from this release.

**No arbitrary 10:45–11:30 New York time window.** The original 45-minute timer was the validity/expiration of a single *pending STOP setup*, NOT permission to operate the service 45 minutes/day. Use fresh broker quotes, actual session status, order geometry, stop-level constraints, and spread/liquidity checks at ANY hour. Avoid exceptional economic data windows when verified official event data is available; a coarse unverified clock proxy cannot be represented as official news coverage.

## Continuous state machine

| Frequency / trigger | Deterministic operational work | AI role |
|---|---|---|
| Every 5 seconds | Verify exact DEMO terminal, reconcile one known pending order or filled position, enforce kill/exposure and watchdog; update small health snapshot | No OpenAI request |
| Near a newly completed M15 candle | Collect W1/D1/H4/H1/M15/M5/M1 closed bars; reject stale quote, incomplete history, unattractive structure, risk/cost | GPT-5.6 Luna structured BUY/SELL/NO_TRADE for qualified candidate, using owner-key verified model on a qualified objective TPB candidate; disagreement rejects, never invent order prices |
| After AI approved candidate | Recalculate the exact broker cash loss to structural SL, current margin, stress/cost, day/week/drawdown, max 0.01 lot, uniqueness and session eligibility | AI CANNOT bypass hard broker/risk checks |
| MT5 pending order accepted | Store real ticket, expiry, entry, broker SL/TP and durable prepared/ack states; reconcile every 5 seconds | No AI repetition |
| Actual broker fill | Authenticate deal/position ID, volume, SL, TP and cash/fee records | Optional post-trade research, never substitute broker records |
| Known position OPEN | Reobserve position and deal history, move protective SL to break-even on sufficient favorable movement and trail strictly to reduce risk; journal SLTP intents before send, confirm broker receipts | Later controlled research may propose structural exit/TP adjustments, never widen risk |
| Order/position closed | Store broker result and realized all-cost cash P/L; next eligible M15 candidate allowed | Research notes, regime analysis and challenger experiments |
| Each UTC day | Compact broker deal aggregation and research reports | No automatic model self-modification or release promotion |

## OpenAI API and model behavior

Runtime calls OpenAI Responses API over TLS with **`gpt-5.6-luna`** selected and verified against the current Windows user API key on 2026-10-24; the owner's allowed candidate list is `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`. Selection is project-entitlement dependent, and non-luna models must pass a real strict-Responses preflight before cutover. Use JSON-schema strict response and `store:false`. One review per deterministic setup key, persisted in SQLite; no arbitrary review-count cap; configurable daily USD spending budget (default $2.00, conservative per-call reserve and actual token usage accounting), no request for every 5s poll. AI returns only a direction approval/veto with a regime and bounded reason. Model outage, missing API key, disagreement or malformed response -> NO_TRADE. API credentials exist **on the VPS only**, not in GitHub or logs. The API key is already present in the current Windows user's **user-level environment variable** `OPENAI_API_KEY`. The revised installer reads that key without prompting for a second copy; legacy DPAPI file is fallback only. Never put the key in GitHub or console logs. Exness session credentials remain in the terminal.

**Training means evidence-based research**, not claiming the foundation model retrains itself after each loss. The agent records net broker outcomes; separate prospective strategy challengers are tested with chronological splits, costs and adverse regimes. Only an independently admitted version changes the champion. Do not optimize against today's winning streak.

## Money and broker authority

- One independent S2 Python MT5 executor, original Exness Pro DEMO account fingerprint (never LIVE), XAUUSD only, initial 0.01 lots.
- Existing all-cost Policy A still applies until an explicitly accepted, calibrated successor replaces it; its 0.25% historical cash cap is NOT fixed SL price distance.
- One outstanding unfilled order OR one broker-known filled position; never close an unknown position, average down, widen risk or blindly repeat uncertain MT5 writes.
- Protective broker SL/TP required on opening order. A protected known position may move its SL **strictly toward smaller risk**, with broker stop-level/freeze-level and quote freshness enforcement, durable intent, verified post-write receipt. An ambiguous result means no repeat.
- AI early exits and conservative inward TP refinements are implemented in the successor source through broker-authenticated known-position write-ahead intents and post-send reconciliation; the broader adaptive strategy continues to require research; a broker-owned known stop-management implementation is not evidence that all of these are live.

## VPS operational storage, alerts, and continuity

- `cycles.jsonl`: append **on state change or 15-minute heartbeat**, not on every 5s poll; rotate at 4MiB through 3 backups, approx 16MiB upper operational bound.
- `health.json`: overwritten approximately every 30 seconds, compact state and NO_TRADE reason.
- `research/YYYY-MM-DD.json`: broker-deal-derived daily result; 45-day operator report retention; underlying SQLite deal/order receipts remain durable and auditable.
- SQLite control/cash/coordinator/AI/protection journals: retain exact risk/order/position evidence; never delete these to save trivial disk space.
- Console log: rotate by deployment supervisor; avoid logging secrets/raw OpenAI prompts/private broker account IDs.
- Alert transports: SMTP and Telegram are environment-based and require actual provider credentials/chat ID and delivery verification; without those, alerts remain queued locally. Never claim provider delivery otherwise.
- Scheduled Task: existing interactive Exness terminal account, hidden console, one task/process writer, same owner; RDP disconnect okay, complete Windows logoff can terminate the task. A later service-account architecture would need independently qualified MT5 terminal access.

## Release / acceptance / next chat

**Actual owner VPS deployment 2026-10-24 16:48 UTC:** One existing hidden Windows scheduled task successfully switched to exact **`dfd193a4c9a6db00da81b806f2b160892eae30c9`** (PR40 now merged, VPS pin unchanged); verified account and flat broker twice, `OPENAI_MODEL_READY:gpt-5.6-luna` via genuine non-trading Responses probe, task Running and first health `ACTIVE / NO_ORDER / WAIT_FOR_NEXT_COMPLETED_M15_BAR`. New AI/all-session/log/position features are now present in the installed source. **No accepted DEMO broker order, position lifecycle, AI market inference or actual SLTP update was observed yet**. Do not claim those steps completed. One pinned Windows upgrade command must first verify flat DEMO broker state, preserved journal, actual OpenAI key, source hashes, and account identity; stop existing task **once**, verify no old Python writer, switch existing task action, start new version, verify fresh health and logs; on any failure, keep trading stopped or restore the old known-good version without duplicating orders.

**Still necessary before a fully qualified autonomous release:** one end-to-end VPS check for AI API, real broker pending/fill/SLTP lifecycle, reliable news/holiday feed and alerts, robust unexpected process termination/restart behavior, commission/swap/tick slippage calibration and rollback. No step falsely marks a missing broker receipt PASS.

**One owner-visible handoff:** exact PR HEAD, changed files, native CI result, on-VPS source pin, task state, broker order tickets / known positions (sanitized), current health and real pending work. A code commit alone must not be called actual VPS trading evidence.

## 2026-10-24 implementation correction (newer than original summary)

**Historical incident (superseded by successful later upgrade):** The earlier upgrade at source `067b529…` failed **before stopping the old service**. `ConvertTo-SecureString` rejected a DPAPI ciphertext read with `Get-Content -Raw` (trailing line ending was not removed). The corrected same-user encrypted-key loading trims only the ciphertext wrapper; it immediately verifies decryption, and reprompts locally if the old file is invalid. Never put API keys in chat/GitHub. That older hidden Exness DEMO service was later **replaced successfully** by the same task running at `dfd193a…`, as evidenced by the owner on 2026-10-24.

The arbitrary 32 API reviews/day restriction is replaced by `XAUUSD_OPENAI_DAILY_BUDGET_USD` (default `2.00`). The reviewer stores durable per-request liabilities **before network calls**, caches each setup/position M15-bar decision, bills based on provider token usage when returned, and avoids re-requesting an uncertain request after a process crash. There is no fixed review-count limit. A cost budget is not a broker trading limit.

Known-position AI may propose `HOLD`, `EARLY_EXIT` or `TIGHTEN_TP` only after actual broker/deal authentication. It provides no unconstrained price or size; the deterministic manager checks stop/freeze geometry, sends a single known-position-only MT5 modification/close, and requires a broker response plus position/deal reconciliation. An unknown result freezes resubmission. Historical learning remains controlled research rather than automatic unsafe model weight changes or strategy promotion.


## Current verified runtime and outstanding acceptance — appended 2026-10-24

**Runtime activated (not a broker trade):** see [2026-10-24 ADR](../decisions/ADR-2026-10-24-001-CONTINUOUS-DEMO-VPS-ACTIVATION.md) and [machine record](CURRENT_DEMO_RUNTIME_STATUS.json), exact source `dfd193a4c9a6db00da81b806f2b160892eae30c9`. One hidden task Running, `gpt-5.6-luna` Responses key/model preflight PASS, real DEMO account verified and flat at deployment. New initial health was `ACTIVE/NO_ORDER` on Saturday. **Full live-market decision/order/fill/management and P/L are still unobserved.**

**Built-in bound:** 3 new pending submissions per UTC day remains in the runtime *order gate*, independent of the rejected 32 OpenAI requests/day. Keep this distinction explicit. Broker-side pending setup expiration 45 minutes is also not a daily session window. Reconsider limits prospectively only through versioned code/risk analysis, never to force a broker order.

**Disk:** `cycles.jsonl` is compact/rotated (4 MiB + 3 backups), `health.json` atomic overwrite; core SQLite and API budgets persist. A console log under a continuously running process can still grow until its next runner startup; inspect size and design safe live rotation rather than claiming all storage is capped. Email/Telegram adapter presence is not proof of delivered alerts. Controlled research is not foundation-model fine-tuning.

**Next:** actual broker open-session M15/AI evidence, pending→fill receipts, known-position broker SLTP/TP/exit confirmation, 24–48h operations review, non-destructive watchdog/alert/disk inspection, then reproducible OOS research. Do not reinstall or automatically move to LIVE. PR40 was merged into main at `0c525c8bce8cc13182dd455cf05dd3c7ce3afb3d` following explicit owner approval; this was GitHub-only, not a VPS redeployment. See [the ordered plan](DEMO_RUNTIME_HANDOFF_AND_NEXT_STEPS_2026-10-24.md).
