# Owner declaration — XAUUSD Exness MT5 DEMO account/profile isolation

**Recorded:** 2026-10-21. **Classification:** `OWNER_DEMO_ACCOUNT_PROFILE_ISOLATION_ATTESTED_2026_10_21`.
**Source:** explicit owner declaration in this project's conversation, preserved without raw credentials as [post-merge owner attestation on PR #8](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/8#issuecomment-6318453695).
**Nature of evidence:** owner self-attestation, not independently verifiable historical credential inventory or broker order authorization.

## Exact semantic scope of sanitized owner declaration

- The currently admitted Exness MT5 DEMO account is **dedicated exclusively to the XAU/USD Autonomous Trading Agent project**.
- It will **not be shared** with unrelated projects or manual trading workflows.
- **No live-account credentials have ever been stored in or used by this project's MT5 profile/configuration.**
- **No historical live-account credentials were saved for this project.**
- **The project has never been given live-account login credentials through this demo profile.**
- This is the owner's explicit account-isolation attestation for **DEMO-ADMIT only**.
- The attestation does **not** authorize DEMO broker order/action, DEMO external-Python trading activation, any login/account switch, and **never** LIVE/real-money exposure.
- Future broker/execution requests must bind to the *exact* admitted fingerprint/server/broker/currency/DEMO trade mode, and **fail closed on any mismatch**. Continue full Policy A stop-loss, margin, known-exposure and safety checks at time of any separately owner-authorized action.

## Sanitized allowed account binding

- Company/broker: `Exness Technologies Ltd`
- Broker/server: `Exness-MT5Trial15`
- Currency: `USD`
- MT5 trade mode: `DEMO`
- Admitted project symbol: `XAUUSD`
- Admitted identity SHA256 fingerprint: `9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91`
- Raw MT5 login/account number: **NOT STORED**
- Passwords, investor credentials, API secrets and raw account screenshots: **NOT STORED**

## Distinguish attestation from runtime proof

The prior owner GUI Navigator attestation said only the intended Demo-Pro account was visible and no LIVE entry was visible; the current, broader owner declaration adds a meaningful *historical no-live-credentials* claim for **this project's MT5 profile/configuration**. It does not independently establish the credential state of every other profile/Windows account. It does not expressly promise that no human or unattended software actor could switch accounts *during* the future supervised canary. Confirm exclusive live-session control with the attending owner and recheck exact DEMO fingerprint and zero exposure at order time.

Last separately owner-reported **READ-ONLY** Exness DEMO snapshot and sealed S2 runtime verification on Oct21: stage `%LOCALAPPDATA%\XAUUSD-APC-DEMO-CANARY-S2` hash-deep PASS and durable `KILLED/UNUSED` at inspection; active approved broker fingerprint, DEMO trade mode, zero positions/zero pending orders, Python trading disabled, no order API calls. Source [PR26 verified stdout](https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent/pull/26#issuecomment-6317356391). This broker snapshot decays in time and is **not** prospective order authorization.

## Preserve exact historical decisions and restrictions

- PR #8 restricted-session v1.1 method remains **MERGED** with immutable original head `8c3b83ba5edf83a8d4e5cc18096070fadf5c52e9` and merge commit `29fe3786128cc2a19e8afdf241dbc3defa272282`; this new attestation is a **prospective post-merge clarification** rather than an edit to the preregistration or method.
- Latest reconciled production `main` at record time `2848c98940def262459fd89d5897c6f63dd6aadb`.
- Separate S2 source PR24 `89711065a3a2d38fe02282fff3ad1782aabda0d2` and S2 staging PR26 `ab98292dde5c6bda9fc63a85eb36aaac36ed605d` remain DRAFT, OPEN and UNMERGED.
- Historic Gate0 R4/R34/R35, S2 first stage FAIL and later separate staged PASS, Oct21 V11 four-hour capture FAIL_CLOSED, and two assistant-verifier typo failures remain immutable. PCR3 `pcr3-execution-disabled-e0383a50e2cc`, unrelated scheduled tasks and sources unchanged.
- Under current existing S2 DEMO-canary plan, full 4-hour/five-day calibration is not required for a **single narrowly supervised** owner-specified DEMO canary. No resulting permission for unattended autonomous DEMO trading, broader DEMO-ADMIT PASS, or real money.
- Remaining pre-APC gates include owner-selected exact BUY/SELL, stop-loss and BUY ceiling/SELL floor from a fresh strategy/test rationale, short activation ID/UTC expiry, owner control of the terminal/account throughout supervision, valid quote and broker cash/margin/Policy A checks, and **fresh separate one-trade grant** for temporary Python enable, one attended entry, known-close and disable. No automatic unknown-exposure closing, retries or silent risk changes.

**Result:** durable owner DEMO-only credential-history attestation recorded without secrets; authority for broker orders/trading remains **NONE**.
