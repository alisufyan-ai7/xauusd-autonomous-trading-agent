# Exness (SC) Ltd Legal and Applicability Evidence Review

**Review date:** 2026-08-10 UTC  
**Status:** Phase 0 documentary review; not legal advice  
**Account context:** Pakistan resident; Exness (SC) Ltd Personal Area; Pro - MT5 Demo - USD  
**Gate 0:** INCOMPLETE; no production or trading-capable implementation authorized

## 1. Evidentiary conclusion

The package materially strengthens the entity and client-classification record, but it does **not** establish unconditional permission for the intended external-Python/OpenAI autonomous agent.

The Client Agreement v038 identifies Exness (SC) Ltd as the contracting company (Part A 1.1, PDF p.5) and states that clients are classified by default as **Retail Clients** unless Exness gives written notice otherwise (Part A 3.1-3.3, PDF p.14). This legal classification is separate from MT5 `ACCOUNT_MARGIN_MODE_RETAIL_HEDGING`.

Part D 4.1 (PDF p.60) expressly contemplates Expert Advisors and other automated processes, places responsibility on the client, and reserves Exness's discretion to accept or reject them. It is therefore evidence that automation is contemplated, **not** an unconditional authorization.

Material ambiguity remains because Part C 2.3(A) and 2.3(G) (PDF p.50) prohibit, respectively, software applying AI analysis to the Company's system/trading platform and software automating access to information through the platform. Part C 2.2 also limits platform use to the client's own account. Part A's API definitions and provisions state that Company API use is governed by separate **API Terms of Use**, which were not included. Part D 6.6 (PDF p.61) separately restricts Exness Custom Indicators and related platform data from bots, external systems/APIs, machine decisions, and extraction unless expressly authorized; this clause appears scoped to the Custom Indicator feature and must not be generalized to all MT5 market data without confirmation.

Consequently, later autonomous trading remains blocked until Exness gives account/entity/jurisdiction-specific written clarification covering: MT5 external Python, automated reading of terminal/account/price data, external AI analysis, VPS use, and whether the API Terms apply to the MT5 Python integration.

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
| AI and automated information access | Client Agreement Part C 2.3(A),(G), PDF p.50 | Broad wording creates a direct ambiguity for OpenAI analysis and external Python market/account reads. Written clarification required. |
| Custom Indicator data | Client Agreement Part D 6.1-6.9, PDF pp.60-62 | Exness Custom Indicator outputs/data cannot be used for bots/external systems without written authorization. Project must not use that feature absent permission. |
| API | Client Agreement definitions and API provisions, PDF pp.6, 13-14 | API Terms of Use are part of the agreement and were not supplied. Missing-document blocker. |
| Credentials | Client Agreement Part C 3.1-3.11, PDF pp.54-55; Risk Disclosure PDF p.4 | Credentials stay owner-controlled and secret; no chat, model prompt, source, logs, support bundle, or third-party disclosure. A locally running owner-controlled service is not silently treated as authorized credential sharing. |
| Platform/data rights | Client Agreement Part C 4.1-4.4, PDF p.55 | Personal storage/display/analysis/reformatting is permitted; publication/transmission/reproduction to third parties needs consent. Whether sending derived broker data to OpenAI is “transmission” must be resolved or inputs must exclude it. |
| Prohibited techniques | Client Agreement Part C 2.4-2.8, PDF pp.50-53; GBT 2.2 and 2.7, PDF pp.7-8, 14-16 | No latency/error exploitation, abusive request rates, off-market-price exploitation, manipulative or economically unreasonable traffic. Rate limiting and intent-to-market-exposure controls are mandatory. |
| VPS | Client Agreement Part C 2.9, PDF p.53 | Exness-provided VPS may be disabled; our intended third-party Windows VPS is not expressly authorized or prohibited by this clause. Written clarification remains prudent. |
| Execution uncertainty | Client Agreement Part D 1-2, PDF pp.56-57; GBT 2.7-2.9, PDF pp.14-17; Risk Disclosure pp.4-6 | Orders may reject/delay/slip; repeated submission before result can create unintended operations. State machine must reconcile before retry. |
| Margin/news | Client Agreement Part D 3.1-3.5, PDF pp.58-59 | Margin can change, including around news, breaks, weekends and holidays; runtime broker calculation and conservative buffers are required. |
| Jurisdiction | Client Agreement Part A 3.4, PDF p.14; Risk Disclosure PDF p.6 | Exness may impose country-specific diligence; client bears responsibility for local restrictions. Pakistan eligibility is not proven merely by demo access. |
| Suspension/termination | Client Agreement Parts A 10-12, PDF pp.22-29 and Part D 1.5, PDF p.56 | Service/access/conditions may change or terminate; fail closed, reconcile, and retain independent records. |
| News/HFT/scalping | No blanket ban found; unreasonable request traffic, abusive latency/error exploitation, and high-volatility conditions are restricted/operationally constrained | Silence is not affirmative permission. Strategy specifications must avoid exploitative mechanics and remain within published and observed constraints. |

## 4. Missing or insufficient evidence

1. The **API Terms of Use** expressly incorporated by the Client Agreement.
2. A redacted Personal Area screenshot binding the Exness (SC) Ltd footer and intended Pro demo account on the same page.
3. Any Personal Area notice showing the accepted agreement/revision or lack thereof.
4. Written Exness clarification for this entity, Pakistan residence, Pro MT5 account, external Python, third-party VPS, automated platform-data access, and external AI analysis.
5. Confirmation that no written Professional Client recategorization notice exists; absent such notice, v038 says Retail Client is the default.
6. Pakistan-specific legal advice if the owner intends real-money operation; this review is contractual evidence analysis, not a determination of Pakistani law.

## 5. Safe interim rule

Keep **Disable automated trading via external Python API** enabled. No broker/platform data may be sent to an external model and no risk-changing MT5 operation may be enabled until the ambiguity above is resolved, the data-transmission design is approved, and a later gate expressly authorizes demo execution.

