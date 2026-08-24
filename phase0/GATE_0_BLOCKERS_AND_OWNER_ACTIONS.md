# Gate 0 Blockers and Owner Actions

**Status:** INCOMPLETE; production and trading implementation prohibited  
**Exness/API direction:** sufficiently complete for Phase 0 under D-0043, D-0048 and D-0049

## Remaining blockers by class

| Class | Remaining evidence/work |
|---|---|
| Owner decision | OpenAI model selection is closed under D-0073. Operational policy is closed under D-0075 for specification/testing: V1, M1, E1, P1, A1, `NO` automatic closure, email primary, Telegram push secondary and the owner-designated acknowledger role are frozen. Reopen only for a concrete test defect or new explicit owner decision. No-purchase provider outreach remains non-binding; purchase, charging/auto-renewing trials and binding terms remain prohibited. |
| Research | Dukascopy rights and immutable data admission are closed under D-0105/D-0106. The private bundle contains 10,619 H4, 39,269 H1 and 157,019 M15 rows at root `138749c9c4c89104a115a25ba4854f61dd4baef04694075602e09494b889ea97`. R1 validation, R2 holdout and fresh-extension R3 holdout rejected the absolute-tail spread/gap/cost model, so no constants, performance replay or Sol chronology were admitted. D-0108 prospectively freezes the regime-adaptive R4 trial; its future 2026-08-25 through 2026-09-23 window is sealed and may not be opened early. Real Event Guard transitions remain pending. |
| Diagnostic | Current official Exness instrument-hours and holiday URLs are source-allow-listed with a seven-day freshness bound. The R21 private baseline remains accepted. R31 adds bounded, read-only zero-exposure pre/post checks, prefix/final matrix verification and append-only dual-channel receipt/acknowledgement recording; focused packet controls pass 31/31. G0-07 and G0-09 are approved but remain pending until genuine private evidence passes. Rendered session boundaries also remain open. |
| Engineering specification/validation | The operational-policy and Sol runtime locks are unchanged. R31 adds ten regressions without changing the frozen fault or A1 acceptance rules; aggregate controlled tests are 338/338 across twenty-three groups. The final matrix remains 6 PASS / 8 PENDING. Registered replay preflight remains fail-closed and no OpenAI API call occurred. |

The following are **not** Gate 0 blockers now: generic Exness automation permission, proprietary Exness API availability, API Terms capture, dedicated-account coexistence, Policy A selection, or further Exness support contact about OpenAI processing.

## Exact owner actions now

Keep **Disable automated trading via external Python API** enabled and do not fund, enable or run automated demo/live trading.

No additional owner policy choice is requested now. Dukascopy rights and data
admission are closed; do not contact the provider again absent a new technical
integrity issue. Provider purchase/trial activation remains prohibited.

The approved G0-07 and G0-09 packets require only their exact execution inputs:
verified out-of-band VPS control and the accepted private baseline path; exact
email and Telegram targets. No raw private output is to be committed, emailed
or published.

No password, identity document, unredacted account number or funds transfer is required.
