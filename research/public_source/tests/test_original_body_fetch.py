"""No-network adversarial unit tests of official original-body source retrieval."""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from original_body_fetch import (  # noqa: E402
    OriginRetrievalError, StrictPublicRedirect, _origin, capture, fetch_original,
)


class FakeHeaders(dict):
    def get(self, key: str, default: str | None = None) -> str | None:
        return super().get(key, default)


class FakeResponse:
    status = 200
    headers = FakeHeaders({"Content-Encoding": "identity", "Content-Type": "text/html",
                           "Date": "Tue, 20 Oct 2026 11:00:00 GMT"})

    def __init__(self, raw: bytes, url: str) -> None:
        self.raw = io.BytesIO(raw)
        self.url = url

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        return self.raw.read(size)

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class OriginTests(unittest.TestCase):
    def test_https_allowlist_rejects_http_unknown_credentials_port(self) -> None:
        for url in (
            "http://www.bls.gov/schedule",
            "https://evil.example.org/believe",
            "https://get.exness.help.evil.example.org/path",
            "https://user:password@www.bls.gov/path",
            "https://www.bls.gov:8443/path",
            "https://www.bls.gov/path#fragment",
        ):
            with self.subTest(url=url), self.assertRaises(OriginRetrievalError):
                _origin(url)

    def test_cross_host_redirect_fails(self) -> None:
        redirect = StrictPublicRedirect()
        import urllib.request
        req = urllib.request.Request("https://www.bls.gov/schedule/")
        with self.assertRaises(OriginRetrievalError):
            redirect.redirect_request(
                req, None, 302, "redirect", {}, "https://www.census.gov/test"
            )

    def test_original_bytes_sha256_not_transcribed_text(self) -> None:
        raw = b"<html>authoritative\r\nraw\xc3\xa9</html>"
        url = "https://www.bls.gov/schedule/2026/11_sched.htm"

        class FakeOpener:
            def open(self, req: object, timeout: int) -> FakeResponse:
                self.request = req
                return FakeResponse(raw, url)

        with patch("original_body_fetch.urllib.request.build_opener", return_value=FakeOpener()):
            body, meta = fetch_original(url)
        self.assertEqual(body, raw)
        self.assertEqual(meta["exact_original_http_entity_sha256"],
                         hashlib.sha256(raw).hexdigest())
        self.assertFalse(meta["accepted_for_capture_registration"])
        self.assertEqual(meta["source_authority_hostname"], "www.bls.gov")

    def test_capture_failure_retains_null_no_fabrication(self) -> None:
        from original_body_fetch import SOURCES
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "fresh"
            with patch("original_body_fetch.fetch_original",
                       side_effect=OriginRetrievalError("blocked")):
                report = capture(target)
            self.assertTrue(report["sources"])
            self.assertEqual(set(report["sources"]), set(SOURCES))
            self.assertTrue(all(
                value["exact_original_http_entity_sha256"] is None
                for value in report["sources"].values()
            ))
            self.assertFalse(report["real_4h_window_frozen"])
            self.assertFalse(report["first_vps_run_permitted"])
            original = json.loads((target / "source-fetch-report.json").read_text())
            self.assertEqual(report["sources"].keys(), original["sources"].keys())
            with self.assertRaises(OriginRetrievalError):
                capture(target)


if __name__ == "__main__":
    unittest.main()
