# Exness (SC) Ltd Legal and Applicability Evidence Review

**Review date:** 2026-08-11 UTC  
**Status:** Phase 0 documentary review; not legal advice  
**Account context:** Pakistan resident; Exness (SC) Ltd Personal Area; Pro - MT5 Demo - USD  
**Gate 0:** INCOMPLETE; no production or trading-capable implementation authorized

## 1. Evidentiary conclusion

The five new owner-supplied screenshots materially narrow the automation issue. The Personal Area screenshot shows the intended Demo-Pro MT5 USD 10,000 account on the same page as the Exness (SC) Ltd footer. The support exchange states that Exness does not currently provide clients a proprietary API for trading-data retrieval or trading, and identifies Expert Advisors and the MT5 Python API as auto-trading alternatives. It separately states that compatible EAs, scripts and indicators may be installed on MT4/MT5.

The Client Agreement v038 identifies Exness (SC) Ltd as the contracting company (Part A 1.1, PDF p.5) and states that clients are classified by default as **Retail Clients** unless Exness gives written notice otherwise (Part A 3.1-3.3, PDF p.14). This legal classification is separate from MT5 `ACCOUNT_MARGIN_MODE_RETAIL_HEDGING`.

Part D 4.1 (PDF p.60) expressly contemplates Expert Advisors and other automated processes, places responsibility on the client, and reserves Exness's discretion to accept or reject them. It is therefore evidence that automation is contemplated, **not** an unconditional authorization.

Material ambiguity remains because Part C 2.3(A) and 2.3(G) (PDF p.50) prohibit, respectively, software applying AI analysis to the Company's system/trading platform and software automating access to information through the platform. Part C 2.2 also limits platform use to the client's own account. Part A's API definitions and provisions state that Company API use is governed by separate **API Terms of Use**. Those Terms are now clause-verified as Version 15 July 2026 / 001; clauses 1.1-1.2 tie scope/effectiveness to Exness API/API Keys and key generation through Exness's Website. They are therefore not treated as governing the present no-key MT5 Python channel absent contrary authoritative evidence. Part D 6.6 (PDF p.61) separately restricts Exness Custom Indicators and related platform data from bots, external systems/APIs, machine decisions, and extraction unless expressly authorized; this clause appears scoped to the Custom Indicator feature and must not be generalized to all MT5 market data without confirmation.

Consequently, basic MT5 Python automation on the client's own account is no longer a broad unresolved blocker. This is account-specific operational support evidence, subject to the contract and any later contradictory authoritative evidence; it is not a contract amendment. Under D-0049, the remaining external-AI/data-use uncertainty is an owner-accepted residual ambiguity rather than a Gate 0 blocker. Exness has not explicitly approved external OpenAI processing.

The architecture distinguishes (A) raw broker/platform data—ticks, quotes, history/feed and large broker-derived datasets—from (B) locally derived/minimized analytical information—price, OHLC indicators, ATR, RSI, ADX, EMA relationships, levels, regime, volatility, spread and normalized risk/exposure state. The design prefers category B, but neither category is treated as authorized for external transmission until the applicable terms/rights are resolved.

## 2. Document register and classification

Dates below are document-face dates unless explicitly marked as PDF metadata. An absent effective date is not inferred.

| File | Exact title / entity | Version or date | SHA-256 | Classification | Project relevance |
|---|---|---|---|---|---|
| `exness_sc_client_agreement.pdf` | Client Agreement / Exness (SC) Ltd | v038; 24 Jul 2026; Exness announcement says effective after five business days, exact timestamp not stated | `ae02ca31a9e2ba1d8ef81cc973caa169e901aa6d802b4f9949a05e3cb1217ddc` | Applicable, primary | Entity, agreement composition, retail default, automation discretion, prohibited actions, credentials, execution, margin, termination, platform/data rights |
| `exness_sc_general_business_terms.pdf` | General Business Terms / Exness (SC) Ltd | v021; 12 Aug 2025 | `a8e8e0942d402c415770943283ef2f44b4d680339530d28b167fc79928174b11` | Applicable, primary | Quote/order procedures, prohibited techniques, EA request load, execution disputes, margin and slippage |
| `risk_disclosure_and_warning_notice.pdf` | Risk Disclosure and Warning Notice / entity not stated on document face | No visible revision/date | `dee4506a0215f6e5c54d314e57a85f8ad1ed1871274118d901fdd7ee8369754a` | Applicable disclosure; entity linkage inherited from Client Agreement 1.3 remains to be confirmed | Leverage, volatility, technical failure, sequential submissions, slippage, government-law responsibility, margin liquidation |
| `key_facts_statement.pdf` | Exness Key Facts Statement - Contracts for Difference / Company not separately identified | Embedded PDF title says October 2024; no visible version | `62530c93b8096431e34c5aa615830fd24117cf25ef4ac3b10518655e8d196ae1` | Applicable disclosure | CFD counterparty model, leverage/margin, XAUUSD example, costs, stop-out caveats |
| `privacy_agreement.pdf` | Privacy Policy / multiple Exness entities including Exness (SC) Ltd | v006; 3 May 2026 | `a38aafcbb00d48b1b90fa3c97260a73abee6c4377b8f03101153a742dee46026` | Applicable to personal-data processing | Data handling and third parties; does not license market/news data or automation |
| `confidentiality_policy.pdf` | Confidentiality Policy / Exness (SC) Ltd | v2; 30 Jun 2025 | `e21ab51363e8ea7c7000ec0e992840d238c668e9857385921d4d1fd0e679365a` | Applicable consumer-data policy | Confidentiality of non-public consumer data; supports secret/redaction controls |
| `summary_of_conflicts_of_interest_policy.pdf` | Summary of Conflicts of Interest Policy / “EXNESS”; exact entity and revision absent | No visible revision/date | `2ef50f03efb7e1756fb34cf795f60411b525eb482bc09af9fb310c146ad9832f` | Informational pending entity/version confirmation | Company may be counterparty and use affiliates; conflict controls and consent |
| `preventing_money_laundering.pdf` | Preventing Money Laundering / “Exness Group” | v001; 28 May 2019 | `cc6c2db4f097b8b86a13aeba340c56fc141986d1ea31f325497b0fa5c3f2a7a8` | Informational | Generic KYC/AML explanation; not a trading-agent permission source |
| `exness_sc_bonus_terms_and_conditions.pdf` | Bonus Terms and Conditions / Exness (SC) Ltd | v05; 30 Sep 2024 | `38b868bc55b5a83281e151d62ca235164436b0393bed54716af1ec05f2e0f7da` | Conditionally applicable only if a bonus/program is granted or published as applicable | Bonus eligibility and account/jurisdiction conditions; no bonus evidence supplied |
| `exness_sc_partnership_agreement.pdf` | Partnership Agreement / Exness (SC) Ltd | v029; 17 Jun 2026 | `b8ba05e21b0472151592487e76d05592b97f42acf820fe8ed75af156fe9e9f16` | Not applicable on current evidence | Governs partners/referrals; no partnership status or activity is proposed |

## 3. Clause findings that constrain the design

| Topic | Evidence | Phase 0 consequence |
|---|---|---|
| Agreement/entity | Client Agreement Part A 1.1-1.3, PDF p.5 | Supports Exness (SC) Ltd and incorporates named legal documents, but still needs account-linked screenshot/acceptance record. |
| Client class | Client Agreement Part A 3.1-3.3, PDF p.14 | Record `legal_client_classification=RETAIL_CLIENT_DEFAULT_BY_AGREEMENT`, pending absence/presence of written recategorization notice. Do not infer from MT5 mode. |
| EA/automation | Client Agreement Part D 4.1, PDF p.60 | Automation is contemplated but is client-risk and subject to Exness acceptance/rejection and platform-stability limits. |
| AI and automated information access | Client Agreement Part C 2.3(A),(G), PDF p.50 | Broad wording creates ambiguity for external OpenAI processing. D-0049 accepts this as residual owner risk with strict local derivation, minimization and execution isolation; no Exness approval is inferred. |
| Custom Indicator data | Client Agreement Part D 6.1-6.9, PDF pp.60-62 | Exness Custom Indicator outputs/data cannot be used for bots/external systems without written authorization. Project must not use that feature absent permission. |
| Proprietary Exness API | Account-specific support screenshots dated 2026-08-11 | Support states no proprietary client data/trading API is currently available. Do not design an Exness API-key broker path. |
| API Terms | Official Exness legal-documents page and linked seven-page PDF, Version 15 July 2026 / 001 | Clauses 1.1-1.2 and 4.2-4.3 define an Exness API/API-Key channel activated through Website key generation. Clause 4.5 permits automation via that API; clause 4.6 addresses AI tools and third-party systems without authorizing broker-data transmission. Applicability to no-key MT5 Python is not established and is not inferred. Raw byte hash is uncaptured, but version/date/page count and clauses are verified. |
| MT5 Python / EA operational support | Account-specific support screenshots | Support expressly identifies EAs and MT5 Python API as auto-trading alternatives and compatible EAs/scripts/indicators as installable. This narrows D-0037; contract restrictions still apply. |
| Credentials | Client Agreement Part C 3.1-3.11, PDF pp.54-55; Risk Disclosure PDF p.4 | Credentials stay owner-controlled and secret; no chat, model prompt, source, logs, support bundle, or third-party disclosure. A locally running owner-controlled service is not silently treated as authorized credential sharing. |
| Platform/data rights | Client Agreement Part C 4.1-4.4, PDF p.55 | Personal storage/display/analysis/reformatting is permitted; publication/transmission/reproduction to third parties needs consent. D-0049 accepts the residual ambiguity without claiming consent; only minimized derived features may be used under the frozen architecture. |
| Prohibited techniques | Client Agreement Part C 2.4-2.8, PDF pp.50-53; GBT 2.2 and 2.7, PDF pp.7-8, 14-16 | No latency/error exploitation, abusive request rates, off-market-price exploitation, manipulative or economically unreasonable traffic. Rate limiting and intent-to-market-exposure controls are mandatory. |
| VPS | Client Agreement Part C 2.9, PDF p.53 | Exness-provided VPS may be disabled; our intended third-party Windows VPS is not expressly authorized or prohibited by this clause. Written clarification remains prudent. |
| Execution uncertainty | Client Agreement Part D 1-2, PDF pp.56-57; GBT 2.7-2.9, PDF pp.14-17; Risk Disclosure pp.4-6 | Orders may reject/delay/slip; repeated submission before result can create unintended operations. State machine must reconcile before retry. |
| Margin/news | Client Agreement Part D 3.1-3.5, PDF pp.58-59 | Margin can change, including around news, breaks, weekends and holidays; runtime broker calculation and conservative buffers are required. |
| Jurisdiction | Client Agreement Part A 3.4, PDF p.14; Risk Disclosure PDF p.6 | Exness may impose country-specific diligence; client bears responsibility for local restrictions. Pakistan eligibility is not proven merely by demo access. |
| Suspension/termination | Client Agreement Parts A 10-12, PDF pp.22-29 and Part D 1.5, PDF p.56 | Service/access/conditions may change or terminate; fail closed, reconcile, and retain independent records. |
| News/HFT/scalping | No blanket ban found; unreasonable request traffic, abusive latency/error exploitation, and high-volatility conditions are restricted/operationally constrained | Silence is not affirmative permission. Strategy specifications must avoid exploitative mechanics and remain within published and observed constraints. |

## 4. Missing or insufficient evidence

1. Any Personal Area notice showing the accepted agreement/revision or lack thereof.
2. Data-minimization enforcement and field-level validation for any future OpenAI input; further Exness contact is not required unless contradictory evidence or architecture change appears.
3. Confirmation that no written Professional Client recategorization notice exists; absent such notice, v038 says Retail Client is the default.
4. Pakistan-specific legal advice if the owner intends real-money operation; this review is contractual evidence analysis, not a determination of Pakistani law.
5. Optional evidence hardening: obtain the raw official API Terms PDF bytes and SHA-256. Clause-level review is complete and this is not a Gate 0 blocker.

## 5. Safe interim rule

Keep **Disable automated trading via external Python API** enabled. No broker/platform-derived data—raw or minimized—may be sent to an external model and no risk-changing MT5 operation may be enabled until the remaining data-use issue is resolved, the minimized-input design is approved, and a later gate expressly authorizes demo execution.

## 6. Account-specific screenshot register

| Evidence | SHA-256 | Finding | Classification |
|---|---|---|---|
| Personal Area account/footer screenshot | `5314545229a580d161bafa59153842ebbf360dd882f8134b26e41d968969714d` | Demo, MT5, Pro, USD 10,000 and Exness (SC) Ltd footer appear on one page | Confidential; visible account number; hash/reference only |
| Support introduction | `a8b63d87b0b183d3cb8a5958718ac0ab141b85847a87607a8a857df0b7fc0ee2` | Context: live support agent Sangeeta; owner asks for trading APIs | Confidential support evidence |
| No proprietary API statement | `a8e4bca5f636addac941f9bffb87b2c959ae63465ea6540de73ec3765dc9a571` | No proprietary client API for data retrieval/trading | Confidential support evidence |
| MT5 Python/EA alternative statement | `63305ea87dff72657e7fd40f6c04c6f1d839883869fafe505f7ea6346bd7d428` | EAs or MT5 Python API identified as auto-trading alternatives | Confidential support evidence |
| EA/script/indicator installation statement | `848540ec6879acbe2232e6bf2022e055f4a1505d33f154b01a402d5aefc61a58` | Compatible EAs/scripts/indicators may be installed; Exness supplies no EA service | Confidential support evidence |
