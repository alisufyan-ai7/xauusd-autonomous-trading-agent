"""Offline or GitHub Actions only: HTTPS original-body provenance for public sources.

No broker connection, MT5, VPS, credentials, session/window qualification,
trading, or authority changes. Stores ORIGINAL HTTP response bytes untouched
as an ephemeral private Actions artifact, not a hash of web snippets.
Artifact retention does not establish permanent admissible provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PUBLIC_ORIGINS = {
    "get.exness.help",
    "www.bls.gov",
    "www.bea.gov",
    "www.federalreserve.gov",
    "www.census.gov",
    "www.dol.gov",
    "oui.doleta.gov",
    "www.gov.uk",
}
SOURCES = {
    "exness_instrument_general_not_generated_xauusd":
        "https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours",
    "exness_holidays_general":
        "https://get.exness.help/hc/en-us/articles/17923046759836-Holiday-trading-hours",
    "bls_october": "https://www.bls.gov/schedule/2026/10_sched.htm",
    "bls_november": "https://www.bls.gov/schedule/2026/11_sched.htm",
    "bea_schedule": "https://www.bea.gov/news/schedule/",
    "fed_october": "https://www.federalreserve.gov/newsevents/2026-october.htm",
    "fed_november": "https://www.federalreserve.gov/newsevents/2026-november.htm",
    "census_advance": "https://www.census.gov/econ/indicators/release_schedule.html",
    "dol_claims": "https://www.dol.gov/agencies/eta/ui-claims",
    "dol_official_claims_release_schedule":
        "https://oui.doleta.gov/unemploy/archive.asp",
    "uk_dst": "https://www.gov.uk/when-do-the-clocks-change",
}
MAX_BODY_BYTES = 3_000_000


class OriginRetrievalError(ValueError):
    pass


def _origin(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in PUBLIC_ORIGINS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise OriginRetrievalError("unapproved or unauthenticated origin")
    return parsed.hostname


class StrictPublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: urllib.request.Request, fp: Any, code: int,
        msg: str, headers: Any, newurl: str,
    ) -> urllib.request.Request | None:
        if _origin(newurl) != _origin(req.full_url):
            raise OriginRetrievalError("cross-origin redirect forbidden")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_original(url: str) -> tuple[bytes, dict[str, Any]]:
    _origin(url)
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        StrictPublicRedirect(),
    )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "XAUUSD-Research-Source-Archive/1.0 (no broker activity)",
            "Accept-Encoding": "identity",
            "Accept": "text/html,application/pdf,application/json,*/*",
        },
        method="GET",
    )
    with opener.open(request, timeout=20) as response:
        url_final = response.geturl()
        if _origin(url_final) != _origin(url):
            raise OriginRetrievalError("final URL left approved origin")
        if response.status != 200:
            raise OriginRetrievalError("non-200 source")
        encoding = response.headers.get("Content-Encoding", "identity").lower()
        if encoding not in ("", "identity"):
            raise OriginRetrievalError("HTTP body automatically transformed")
        raw = response.read(MAX_BODY_BYTES + 1)
        if not raw or len(raw) > MAX_BODY_BYTES:
            raise OriginRetrievalError("source empty or excessively large")
        return raw, {
            "requested_url": url,
            "final_url": url_final,
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "source_authority_hostname": _origin(url_final),
            "http_status": int(response.status),
            "content_type": response.headers.get("Content-Type"),
            "content_length_header": response.headers.get("Content-Length"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "server_date": response.headers.get("Date"),
            "ssl_verification": "PYTHON_DEFAULT_TRUST_STORE__NOT_INDEPENDENT_PROVIDER_ATTESTATION",
            "content_encoding": encoding,
            "body_bytes_length": len(raw),
            "exact_original_http_entity_sha256": hashlib.sha256(raw).hexdigest(),
            "source_role": "SCREENING_ONLY_NO_DATE_SPECIFIC_XAUUSD_OR_EVENT_GUARD_HEALTH",
            "accepted_for_capture_registration": False,
        }


def capture(output: Path) -> dict[str, Any]:
    if output.exists():
        raise OriginRetrievalError("existing output directory cannot be overwritten")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    records: dict[str, Any] = {}
    for name, url in SOURCES.items():
        try:
            raw, meta = fetch_original(url)
            (output / (name + ".original-body")).write_bytes(raw)
            records[name] = {"status": "HTTPS_ORIGINAL_BODY_RETRIEVED", **meta}
        except (OSError, ValueError, urllib.error.URLError) as exc:
            status_code = int(exc.code) if isinstance(
                exc, urllib.error.HTTPError
            ) else None
            records[name] = {
                "status": "ORIGINAL_BODY_UNAVAILABLE",
                "requested_url": url,
                "reason_type": type(exc).__name__,
                "http_status_when_available": status_code,
                "failed_at_utc": datetime.now(UTC).isoformat(),
                "exact_original_http_entity_sha256": None,
                "accepted_for_capture_registration": False,
            }
    result = {
        "scope": "PUBLIC_AUTHORITIES_ONLY_GITHUB_ACTIONS_NO_MT5_NO_VPS",
        "artifact_retention_not_immutable": True,
        "captured_utc": datetime.now(UTC).isoformat(),
        "github_only_ephemeral_original_http_bytes": True,
        "date_specific_exness_xauusd_tradability_proven": False,
        "live_event_guard_health_proven": False,
        "actual_broker_costs_and_account_proven": False,
        "real_4h_window_frozen": False,
        "first_vps_run_permitted": False,
        "sources": records,
    }
    (output / "source-fetch-report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Public authoritative-source bytes ONLY")
    parser.add_argument("--ephemeral-output", type=Path, required=True)
    args = parser.parse_args()
    result = capture(args.ephemeral_output)
    summary = {
        "status": "SCREENING_NOT_QUALIFIED",
        "retrieved_count": sum(
            item["status"] == "HTTPS_ORIGINAL_BODY_RETRIEVED"
            for item in result["sources"].values()
        ),
        "failed_count": sum(
            item["status"] != "HTTPS_ORIGINAL_BODY_RETRIEVED"
            for item in result["sources"].values()
        ),
        "source_hashes": {
            k: v["exact_original_http_entity_sha256"]
            for k, v in result["sources"].items()
        },
    }
    print(json.dumps(summary, sort_keys=True))
    # Log public HTTP metadata and timestamps for durable cross-chat GitHub
    # review. NEVER log body bytes, cookies, API keys or private broker data.
    print("PUBLIC_HTTPS_SOURCE_ORIGIN_REPORT=" + json.dumps(
        result["sources"], sort_keys=True, separators=(",", ":"),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
