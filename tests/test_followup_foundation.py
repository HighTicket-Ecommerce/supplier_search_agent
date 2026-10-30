"""Offline transport, isolation and identity-retry regression coverage."""
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from backend import directory_runner, job_store, public_fetch, research_runner, supplier_validator
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class FoundationFollowupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.tmp.name)/"jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden"))
        self.network.start()
        self.sequence = 0

    def tearDown(self):
        self.network.stop(); self.env.stop(); self.tmp.cleanup()

    def context(self, **kwargs):
        self.sequence += 1
        request = ResearchRequest(product="Sauna heaters", **kwargs)
        job_id = "followup-"+str(self.sequence)
        job_store.init_job(job_id, request.model_dump())
        return ResearchContext(job_id, request)

    def test_transport_and_http_failures_fall_back_without_policy_bypass(self):
        errors = [public_fetch.urllib3.exceptions.NewConnectionError(None, "refused"),
                  public_fetch.urllib3.exceptions.ReadTimeoutError(None, "/", "timeout"),
                  public_fetch.urllib3.exceptions.SSLError("TLS")]
        for error in errors + [403, 500]:
            with self.subTest(error=error):
                context = self.context(allow_browser_fallback=True)
                pool = MagicMock()
                if isinstance(error, int):
                    pool.urlopen.return_value = MagicMock(status=error, headers={})
                else:
                    pool.urlopen.side_effect = error
                source = {"url": "https://example.com/brands", "text": "public brands", "retrieved_at": 1, "body_sha256": "fixture"}
                rows = [{"supplier_name": "Example", "source_url": source["url"], "directory_entry_url": "/brands/example"}]
                with patch.object(public_fetch, "check_public_url", return_value="93.184.216.34"), \
                     patch.object(public_fetch, "_connection", return_value=pool), \
                     patch.object(directory_runner, "fetch_browser_directory", return_value=source) as browser, \
                     patch.object(directory_runner, "extract_html_brands", return_value=rows):
                    result, coverage = directory_runner.fetch_directory(source["url"], context, limit=5)
                browser.assert_called_once()
                self.assertEqual(len(result), 1)
                self.assertEqual(coverage["adapter"], "browser_brand_links")

    def test_policy_rejections_are_fatal_even_when_browser_is_enabled(self):
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
        for url in ("http://localhost/brands", "http://127.0.0.1/brands", "ftp://example.com/brands", "https://user:password@example.com/brands"):
            with self.subTest(url=url), patch.object(socket, "getaddrinfo", return_value=addresses), \
                 patch.object(directory_runner, "fetch_browser_directory") as browser:
                with self.assertRaises(ValueError):
                    directory_runner.fetch_directory(url, self.context(allow_browser_fallback=True), limit=1)
                browser.assert_not_called()

    def test_disabled_fallback_preserves_failure_cause(self):
        error = public_fetch.urllib3.exceptions.ReadTimeoutError(None, "/", "timeout")
        pool = MagicMock(); pool.urlopen.side_effect = error
        with patch.object(public_fetch, "check_public_url", return_value="93.184.216.34"), \
             patch.object(public_fetch, "_connection", return_value=pool), \
             patch.object(directory_runner, "fetch_browser_directory") as browser:
            with self.assertRaises(ValueError) as raised:
                directory_runner.fetch_directory("https://example.com/brands", self.context(), limit=1)
        self.assertIs(raised.exception.__cause__, error)
        browser.assert_not_called()
