"""Offline regressions for the foundational PR review findings."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from backend import job_store, public_fetch, research_runner, supplier_validator, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import ResearchContext, JobStopped, LimitReached


class FoundationReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.tmp.name) / "jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden"))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        self.tmp.cleanup()

    def context(self, **kwargs):
        req = ResearchRequest(product="Sauna heaters", **kwargs)
        job_store.init_job("review", req.model_dump())
        return ResearchContext("review", req)

    def test_checked_ip_is_the_connection_target_and_tls_uses_original_host(self):
        context = self.context()
        response = MagicMock(status=200, headers={})
        response.stream.return_value = [b"public page"]
        pool = MagicMock(); pool.urlopen.return_value = response
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch.object(socket, "getaddrinfo", side_effect=[addresses]) as dns, \
             patch.object(public_fetch.urllib3, "HTTPSConnectionPool", return_value=pool) as connection:
            self.assertEqual(public_fetch.fetch_public("https://example.com/about?q=1", context)["text"], "public page")
        self.assertEqual(dns.call_count, 1)
        self.assertEqual(connection.call_args.kwargs["host"], "93.184.216.34")
        self.assertEqual(connection.call_args.kwargs["server_hostname"], "example.com")
        self.assertEqual(connection.call_args.kwargs["assert_hostname"], "example.com")
        self.assertEqual(connection.call_args.kwargs["cert_reqs"], "CERT_REQUIRED")
        self.assertEqual(pool.urlopen.call_args.args[:2], ("GET", "/about?q=1"))
        self.assertEqual(pool.urlopen.call_args.kwargs["headers"]["Host"], "example.com")
        self.assertFalse(pool.urlopen.call_args.kwargs["retries"])
        response.close.assert_called_once(); pool.close.assert_called_once()

    def test_redirect_dns_is_rechecked_before_another_connection(self):
        context = self.context()
        response = MagicMock(status=302, headers={"Location": "http://internal.example"})
        pool = MagicMock(); pool.urlopen.return_value = response
        def addresses(host, port):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1" if host == "internal.example" else "93.184.216.34", port))]
        with patch.object(socket, "getaddrinfo", side_effect=addresses), \
             patch.object(public_fetch, "_connection", return_value=pool) as connection:
            with self.assertRaises(ValueError):
                public_fetch.fetch_public("https://example.com", context)
        self.assertEqual(connection.call_count, 1)
        self.assertEqual(context.pages, 1)

    def test_unconfigured_model_default_has_positive_pricing(self):
        # Test config in isolation so the test suite's explicit model cannot hide the default.
        env = dict(os.environ, OPENAI_MODEL="")
        code = "import os; os.environ.pop('OPENAI_MODEL'); from unittest.mock import patch; " \
               "p=patch('dotenv.load_dotenv');p.start();import backend.config as c;" \
               "assert c.OPENAI_MODEL=='gpt-5.2-2025-12-11';" \
               "assert c.OPENAI_INPUT_USD_PER_MILLION>0 and c.OPENAI_OUTPUT_USD_PER_MILLION>0"
        env.pop("OPENAI_INPUT_USD_PER_MILLION", None); env.pop("OPENAI_OUTPUT_USD_PER_MILLION", None)
        subprocess.run([os.sys.executable, "-c", code], env=env, check=True, capture_output=True)

    def test_supporting_failure_preserves_collected_pages_and_stop_propagates(self):
        context = self.context(max_pages_per_supplier=3)
        first = {"url": "https://example.com", "text": "[About](/about) [Contact](/contact)"}
        contact = {"url": "https://example.com/contact", "text": "Our office contact"}
        with patch.object(web_fetcher, "fetch_page", side_effect=[first, RuntimeError("provider"), contact]):
            self.assertEqual(web_fetcher.fetch_website_pages(first["url"], context), [first, contact])
        self.assertEqual(context.fetch_failures, [{"url": "https://example.com/about", "error_type": "RuntimeError"}])
        for error in (JobStopped("stop"), LimitReached("page_limit")):
            with patch.object(web_fetcher, "fetch_page", side_effect=[first, error]):
                with self.assertRaises(type(error)):
                    web_fetcher.fetch_website_pages(first["url"], context)

    def test_shopping_retains_all_countries_and_retries_a_different_identity(self):
        context = self.context(use_shopping=True, allowed_countries=["Canada", "United States"], max_candidate_domains=4)
        first = {"lookup_hint": "Brand A", "title": "A"}
        second = {"lookup_hint": "Brand B", "title": "B"}
        with patch.object(research_runner, "run_serp_discovery", return_value=[]), \
             patch.object(research_runner, "run_google_shopping_discovery", side_effect=[[first], [second]]), \
             patch.object(research_runner, "run_serp_brand_lookup", side_effect=lambda *a, **k: [{"url": "https://brand-b.example"}]), \
             patch.object(research_runner, "process_supplier", side_effect=[
                 {"url": "https://brand-b.example", "status": "review", "reason": "shopping_identity_not_established"},
                 {"url": "https://brand-b.example", "status": "qualified"}]) as process:
            research_runner.run_research_job("review", context.request)
        job = job_store.get_job("review")
        self.assertEqual(job["observations"], [first, second])
        self.assertEqual(process.call_count, 2)
        self.assertEqual(job["processed"], 2)
        self.assertEqual(len(job["accepted"]), 1)

    def test_identity_retry_reuses_only_job_local_website_pages(self):
        context = self.context()
        pages = [{"url": "https://example.com", "text": "Example"}]
        with patch.object(supplier_validator, "fetch_website_pages", return_value=pages) as fetch, \
             patch.object(supplier_validator, "analyze_supplier_with_llm", return_value={"error": "test"}):
            supplier_validator.process_supplier("Sauna heaters", pages[0]["url"], context, brand_hint="A")
            supplier_validator.process_supplier("Sauna heaters", pages[0]["url"], context, brand_hint="B")
        self.assertEqual(fetch.call_count, 1)


if __name__ == "__main__":
    unittest.main()
