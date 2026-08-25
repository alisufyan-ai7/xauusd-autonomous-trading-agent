# Gate 0 Blockers and Owner Actions

**Status:** INCOMPLETE; production and trading implementation prohibited  
**Exness/API direction:** sufficiently complete for Phase 0 under D-0043, D-0048 and D-0049

## Remaining blockers by class

| Class | Remaining evidence/work |
|---|---|
| Owner decision | OpenAI model selection is closed under D-0073. Operational policy is closed under D-0075 for specification/testing: V1, M1, E1, P1, A1, `NO` automatic closure, email primary, Telegram push secondary and the owner-designated acknowledger role are frozen. Reopen only for a concrete test defect or new explicit owner decision. No-purchase provider outreach remains non-binding; purchase, charging/auto-renewing trials and binding terms remain prohibited. |
| Research | Dukascopy rights and immutable data admission are closed under D-0105/D-0106. The private bundle contains 10,619 H4, 39,269 H1 and 157,019 M15 rows at root `138749c9c4c89104a115a25ba4854f61dd4baef04694075602e09494b889ea97`. R1 validation, R2 holdout and fresh-extension R3 holdout rejected the absolute-tail spread/gap/cost model, so no constants, performance replay or Sol chronology were admitted. D-0108 prospectively freezes the regime-adaptive R4 trial; its future 2026-08-25 through 2026-09-23 window is sealed and may not be opened early. Real Event Guard transitions remain pending. |
| Diagnostic | Current official Exness instrument-hours and holiday URLs are source-allow-listed with a seven-day freshness bound. The R21 private baseline remains accepted. R34 and the single authorized corrected R35 G0-07 attempt both failed closed before `DISCONNECT` evidence was appended. R35 proved the selected adapter entered `Disabled`, but the read-only MT5 observer did not produce the required disconnected state within 150 seconds. The restore path completed without a reported error and no later fault began. No third retry is authorized. Two G0-09 setup attempts also failed closed at Telegram `getMe` before binding or sending; TCP 443 was reachable and Gmail preflight passed by control-flow evidence, but R34 discarded the bounded transport cause. G0-07 and G0-09 remain pending. Rendered session boundaries also remain open. |
| Engineering specification/validation | The operational-policy and Sol runtime locks are unchanged. R35 controls passed 358/358 across twenty-five groups and the VPS G0-07 subset passed 30/30 before the operational rejection. R37 changes only Telegram setup diagnostics: HTTP rejection, TLS, DNS, timeout, connection and proxy/network categories are rendered without exception details, token values or token-bearing URLs. Focused alert controls pass 24/24. The final matrix remains 6 PASS / 8 PENDING. Registered replay preflight remains fail-closed and no OpenAI API call occurred. |

The following are **not** Gate 0 blockers now: generic Exness automation permission, proprietary Exness API availability, API Terms capture, dedicated-account coexistence, Policy A selection, or further Exness support contact about OpenAI processing.

## Exact owner actions now

Keep **Disable automated trading via external Python API** enabled and do not fund, enable or run automated demo/live trading.

No additional owner policy choice is requested now. Dukascopy rights and data
admission are closed; do not contact the provider again absent a new technical
integrity issue. Provider purchase/trial activation remains prohibited.

G0-07 requires no owner action now. Preserve both failed attempts; do not run a
third retry or expand the scenario set. G0-09 setup must not be retried until
the R37 bounded diagnostic correction is published. The corrected setup remains
non-delivery; the canary still requires a fresh acknowledgement window.
No secret, recipient identifier or raw private output is to be committed,
chatted or published.

No password, identity document, unredacted account number or funds transfer is required.
