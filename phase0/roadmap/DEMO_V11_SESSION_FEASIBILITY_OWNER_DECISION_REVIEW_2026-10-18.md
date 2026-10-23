# v1.1 session feasibility: owner-gated disposition (offline 2026-10-18)

**Disposition: CANNOT ADMIT a four-hour entirely London–New York center overlap using Exness's currently published generic table.** This does **not** prove actual XAUUSD is open or liquid at any specific time, nor that all independent calendar and Event Guard requirements pass. No owner method revision has been selected.

## Authoritative public source versus not-yet-proven broker facts

Source A: [Exness, Instrument trading hours](https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours), search surfaced update **2026-09-29 07:18**. States server UTC+0, warns XAUUSD usually closed during rollover and that the dynamically generated date/instrument-specific schedule reflects maintenance, holidays and DST. **Generic international trading-center table only**, not the required XAUUSD-specific schedule:

| Regime | London UTC | New York UTC | Overlap | Minutes |
| --- | --- | --- | --- | --- |
| Summer | 08:00–16:30 | 13:30–20:00 | 13:30–16:30 | **180** |
| Winter | 08:00–16:30 | 14:30–21:00 | 14:30–16:30 | **120** |

Thus the presently frozen literal reading that a **single 240-minute window must be wholly inside the published London–NY center overlap** is mechanically infeasible for either regime; it **cannot be cured by waiting for another day**. The original owner wording accepted “one qualifying contiguous 4-hour liquid-market window,” and an overlap-derived condition was subsequently frozen in the v1.1 engineering preregistration. Changing that frozen scope requires an explicit prospective owner choice, not implicit reinterpretation.

The date-specific Exness **XAUUSD** open/close-only/quote-only calendar is interactive and was **not verified for any exact 2026-10-19+ four-hour date** by this review; a center table alone cannot fill that requirement. The public Exness [holiday page](https://get.exness.help/hc/en-us/articles/17923046759836-Holiday-trading-hours) includes calendar warnings but **does not attest to date-specific XAUUSD eligibility for this proposed window**. Source hash and independent verification: **MISSING**.

## Concrete event collisions and absent permissions

- [Census Survey of Construction monthly schedule](https://www.census.gov/construction/soc/schedule.html): New Residential Construction **Tuesday Oct 20 2026 at 08:30 US Eastern = 12:30 UTC**. Occurs at the start of a *hypothetical* 12:30–16:30 London+overlap demonstration, making that date **unqualified without verified blackout classification**.
- [BLS October 2026](https://www.bls.gov/schedule/2026/10_sched_list.htm): State Employment/Unemployment **Tuesday Oct 20 at 10:00 US Eastern = 14:00 UTC**, inside the same demonstration. This is a public schedule fact, **not** a claim that the project's Event Guard has classified the report high impact.
- [DOL weekly unemployment claims](https://www.dol.gov/ui/data.pdf) official release exemplars publish weekly **Thursday 08:30 US Eastern**; an independent forward calendar also lists **Thu Oct 22 08:30 EDT = 12:30 UTC**. Do NOT qualify Oct 22's illustrative 12:30–16:30 window as clear: it begins at a scheduled release, and an exact forward DOL source snapshot/Event Guard classification is still missing.
- [BEA upcoming schedule](https://bea.gov/news/schedule/) lists **Oct 29 08:30 US Eastern** GDP advance and personal income, and [Federal Reserve October calendar](https://www.federalreserve.gov/newsevents/2026-october.htm) lists the **Oct 27–28 FOMC meeting**. [Census indicators calendar](https://www.census.gov/economic-indicators/calendar-listview.html) contains additional scheduled releases. None can be treated as fully covered by the BLS calendar alone.
- Unscheduled events, verified source capture hashes, broker-session eligibility, live shock classification and healthy Event Guard are absent. No exact candidate is `READY` or `APPROVED`.

## Prospective owner options, not enacted

**A — Recommended: retain 240 minutes of contiguous broker-eligible, independently evidenced liquid-market *observation*; allow eventual demo entries solely in the validated London–NY intersection, not in an extra London-only observation hour.** Public generic summer *illustration* would be 12:30–16:30 observation, with demo-entry regime only 13:30–16:30, all subject to dates, DST, instrument-specific Exness source, high-impact blocking, and broader restrictions. Winter illustration would similarly contain only 14:30–16:30 overlap. The **entire four-hour quote evidence can contribute worst adverse costs** and the eventual runtime entry guard remains strictly the narrower, empirically supported overlap. This is **a deliberate prospective change to evidence-scope only**, not retroactive admission, session expansion for orders, or a reason to assume missing costs zero. An account position may cross the permitted entry window; held-position supervision/exit still requires distinct approval. Owner must explicitly adopt a separate successor registration BEFORE capture.

**B — Alternate: use only the published center overlap for data and potential entries** (180 minutes summer, 120 winter) but accept reduced coverage. This shortens the engineering observation target and requires a separately registered owner-approved method, continued cost evidentiary sufficiency, additional prospective evidence on any unknown component, and no statistical-confidence claims. Not recommended ahead of A without new source evidence.

**C — Preserve frozen literal four-hour all-overlap scope** and remain `NOT_QUALIFIED` until independently proven by new broker-specific session rules or a prospectively chosen replacement. The generic Exness center table is insufficient proof of a four-hour overlap; do not collect/activate based on it.

The proposed selection object is `phase0/roadmap/DEMO_V11_SESSION_SCOPE_OWNER_OPTIONS_2026-10-18.json` with **`selected_option=null`**. No earlier v1.0/v1.1 registration was rewritten. The owner may authorize a specific successor *design*, but that alone will not approve data capture, VPS access, MT5 actions, PR merges, broker activation, or any trading.

## Public fees: useful context, NOT account admission

[Exness commission article](https://get.exness.help/hc/en-us/articles/360012007919-Are-trading-accounts-charged-a-commission-fee) says Pro accounts are commission-free, and [Exness commodities specification](https://get.exness.help/hc/en-us/articles/17854173039388-Commodities) lists 100 troy ounces per lot, 0.01-lot minimum and XAUUSD swaps/Wednesday triple-swap warning. Those generic facts **cannot prove the actual MT5 account is a Pro account, its symbol metadata, an applicable commission waiver, swap or emergency overnight administration fees**. [Exness admin fees](https://get.exness.help/hc/en-us/articles/11415853845404-About-admin-fees-on-overnight-orders) additionally warns fees may be imposed on overnight positions. Treat commission/swap/holding/gap/conversion USD as **UNVERIFIED**, not automatically zero. No fee, quote, stop-loss USD, M1 stress, `current_adverse_cost` or `stressed_adverse_cost` is admitted.

## Immediate owner-independent work DONE; blockers unchanged

- `demo_adapter/scripts/v11_session_scope_feasibility.py` and synthetic tests compute and cross-check center-table overlap and explicitly return **no verified eligibility or authorization**.
- The prospective owner options preserve full frozen Policy A, 0.01 lot, no martingale, current/stressed 1000% margin and 90% free margin, per-trade USD cap and all period risk controls.
- Draft PR #12 is stacked on draft PR #11 only. `main`, v1.0 Git blob `3e6e0d19e70da5a02002615160e3f0c0a0367b77`, immutable Gate/PCR failures, the PR #9 hard QUARANTINE before `order_check/order_send`, and all other existing authority restrictions remain unchanged.

**Hard next gate:** an **explicit owner choice** between the prospective restricted observation/entry formulations is needed if the present full-four-hour-overlap method cannot be met. Still require date-specific official Exness XAUUSD schedule, event guard, DST and holiday source hashes before registering a real UTC capture window; separately approve any VPS, broker data retrieval or collector run. **No captures, demo orders, MT5 Python tradeapi toggle or PR merges occurred.**
