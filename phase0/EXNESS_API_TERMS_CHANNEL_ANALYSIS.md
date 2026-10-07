# Exness API Terms — Channel Applicability Analysis

**Date:** 2026-08-11 UTC  
**Status:** Phase 0 clause-level review complete; raw PDF byte hash not captured  
**Gate 0:** INCOMPLETE; no trading authorized

## Finding

The official Exness legal-documents page links a seven-page PDF titled **API Terms of Use**, **Version 15 July 2026 / 001**. The official PDF was independently reviewed on 2026-08-11 UTC. The authoritative source URL is:

`https://www.exness.com/cdn/media/docs/exness-api-terms-of-use.pdf`

The document's version, page count and clauses are verified. The CDN denied direct raw-byte retrieval in this environment, so no SHA-256 is asserted for the PDF bytes. This is an evidence-capture limitation, not a missing-document or missing-clause limitation.

Account-specific Exness live support states that clients currently do not have a proprietary Exness API for retrieving trading data or executing trades, and directs auto-trading users to Expert Advisors or the MT5 Python API. The project therefore does not assume an Exness-issued API key, endpoint or direct Exness API execution channel.

## Architecture consequence

- Proprietary Exness client API path: unavailable unless later written evidence establishes one.
- Intended broker channel: owner-controlled MT5 terminal and local MT5 Python integration.
- The API Terms are preserved as legal evidence, but direct applicability to the current no-key MT5 Python channel is not established.
- Uncertain API-Term applicability is not, by itself, a blocker to MT5/Python specification work.
- It remains prohibited to enable risk-changing Python trading until a later gate.

## Clause-level channel mapping

| Clause | Verified effect | Project interpretation |
|---|---|---|
| 1.1 | Terms apply to client access to and use of Exness API and associated API Keys. | Express subject is the Exness API/API-Key channel. |
| 1.2 | Terms become legally effective when the client creates or generates API Keys through Exness's Website. | No key creation means the stated activation event has not occurred for the present architecture. |
| 1.3 | Terms supplement the Client Agreement and prevail for programmatic/automated/algorithmic access where operationally conflicting. | Precedence is material when this API-Key channel applies; it is not proof that all programmatic access through an independent platform vendor is the defined Exness API. |
| 2.1, 2.4-2.5 | Define API Keys/tokens and client responsibility for instructions authenticated with them. | These credential rules do not describe the local MT5 Python terminal login path. |
| 3.1-3.2 | License Exness API-Key use and prohibit reverse engineering, abuse, latency exploitation and other listed conduct. | Normative if the Exness API-Key channel is enabled; relevant principles remain useful but are not silently transplanted as governing MT5-Python terms. |
| 4.2-4.3 | State that eligible clients can generate individualized API Keys through Exness's Website. | This conflicts operationally with current account-specific support saying no proprietary client API is currently offered; no endpoint/key path may be designed from the Terms alone. |
| 4.5 | Expressly permits automated and algorithmic trading via the API, subject to restrictions. | Confirms automation for the defined API channel, not availability of that channel for this account. |
| 4.6(A)-(C) | Allocates risk for AI-assisted code/instructions and third-party systems; permits integration only within the Terms and without unauthorized API-Key disclosure. | It contemplates AI tools and external systems for the API-Key channel but is not an affirmative authorization to transmit raw or derived broker data to OpenAI. |
| 5-10 | Allocate technical/security risk, recommend least privilege, authorize key-linked instructions, allow suspension, disclaim warranties and permit amendments. | Supports strict credential isolation, fail-closed design and version monitoring if a future Exness API is ever enabled. |

## Result

The direct Exness API-Key architecture remains **unavailable** on current evidence. These Terms are not a reason to block local MT5 Python specification or non-trading testing because their own activation and operational provisions are tied to Exness-issued API Keys. This is an architecture-specific interpretation, not legal advice and not a finding that the Client Agreement is inapplicable.

The Client Agreement/platform-data question remains ambiguous, but D-0049 records the owner's acceptance of that residual ambiguity for Phase 0. This is not an inference that Exness authorized OpenAI processing. The architecture permits only the minimum locally derived analytical features required for setup evaluation and prohibits credentials, account/server identifiers, ticket IDs, exact account/risk/margin state and unnecessary raw/bulk feeds.

## Remaining evidence

1. Written/authoritative answer concerning external processing of raw versus derived/minimized broker data.
2. Reassess the Terms only if Exness later exposes an API-Key feature to this account or supplies contrary channel-applicability evidence.
3. Optional evidence hardening: capture the exact official PDF bytes and SHA-256 outside this environment or from an owner-supplied file. This is no longer a Gate 0 blocker.
