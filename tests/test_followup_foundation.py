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

    def test_supplier_failures_are_scoped_and_survive_only_their_own_cache_hit(self):
        context = self.context()
        failure = {"url": "https://a.example/about", "error_type": "RuntimeError"}
        def fetch(url, ctx):
            if "a.example" in url:
                ctx.fetch_failures.append(failure)
            return [{"url": url, "text": "Supplier evidence"}]
        with patch.object(supplier_validator, "fetch_website_pages", side_effect=fetch) as fetcher, \
             patch.object(supplier_validator, "analyze_supplier_with_llm", return_value={"error": "offline"}):
            a = supplier_validator.process_supplier("Sauna heaters", "https://a.example", context)
            b = supplier_validator.process_supplier("Sauna heaters", "https://b.example", context)
            a_again = supplier_validator.process_supplier("Sauna heaters", "https://a.example", context)
        self.assertEqual(a.get("collection_failures"), [failure])
        self.assertEqual(b.get("collection_failures", []), [])
        self.assertEqual(a_again.get("collection_failures"), [failure])
        self.assertEqual(fetcher.call_count, 2)

    def test_directory_identity_retry_reuses_pages_and_counts_each_check(self):
        context = self.context(research_mode="distributor_brands", directory_urls=["https://directory.example"],
                               verify_directory_brands=True, allowed_countries=[], max_candidate_domains=2)
        url = "https://brand-b.example"
        source = "We manufacture sauna heaters.\nWe supply sauna heaters.\nBrand B"
        pages = [{"url": url, "text": source}]
        entries = [{"supplier_name": name, "source_url": "https://directory.example", "observation_id": name}
                   for name in ["Brand A", "Brand B", "Brand C"]]
        def analysis(product, pages, ctx, brand_hint=None):
            return {"is_product_company": True, "company_name": "Brand B", "supplier_type": "Manufacturer", "owns_brand": True,
                    "product_match": "supported", "product_kind": "primary", "matched_product_urls": [url], "country": None,
                    "country_basis": "unknown", "identity_match": "supported" if brand_hint == "Brand B" else "not_established",
                    "email": None, "phone": None, "confidence": .99, "notes": "offline", "evidence": [
                        {"claim": "role", "source_url": url, "quote": "We manufacture sauna heaters"},
                        {"claim": "product_match", "source_url": url, "quote": "We supply sauna heaters"},
                        {"claim": "identity", "source_url": url, "quote": "Brand B"}]}
        def lookup(*args, **kwargs):
            return [] if "brand-b.example" in kwargs.get("seen_domains", set()) else [{"url": url}]
        with patch.object(research_runner, "fetch_directory", return_value=(entries, {})), \
             patch.object(research_runner, "run_serp_brand_lookup", side_effect=lookup) as search, \
             patch.object(supplier_validator, "fetch_website_pages", return_value=pages) as fetch, \
             patch.object(supplier_validator, "analyze_supplier_with_llm", side_effect=analysis) as model:
            research_runner.run_research_job(context.job_id, context.request)
        job = job_store.get_job(context.job_id)
        self.assertEqual(len(job["accepted"]), 1)
        self.assertEqual(job["review"][0]["reason"], "shopping_identity_not_established")
        self.assertEqual(job["processed"], 2)
        self.assertEqual(search.call_count, 2)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(fetch.call_count, 1)

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

    def test_international_domains_use_one_ascii_identity_for_dns_host_and_tls(self):
        for scheme in ("http", "https"):
            with self.subTest(scheme=scheme):
                context = self.context()
                response = MagicMock(status=200, headers={})
                response.stream.return_value = [b"brands"]
                pool = MagicMock(); pool.urlopen.return_value = response
                addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
                pool_type = "HTTPSConnectionPool" if scheme == "https" else "HTTPConnectionPool"
                with patch.object(socket, "getaddrinfo", return_value=addresses) as dns, \
                     patch.object(public_fetch.urllib3, pool_type, return_value=pool) as connection:
                    public_fetch.fetch_public(scheme+"://пример.рф/brands", context)
                expected = "xn--e1afmkfd.xn--p1ai"
                self.assertEqual(dns.call_args.args[0], expected)
                self.assertEqual(pool.urlopen.call_args.kwargs["headers"]["Host"], expected)
                self.assertEqual(connection.call_args.kwargs["host"], "93.184.216.34")
                if scheme == "https":
                    self.assertEqual(connection.call_args.kwargs["server_hostname"], expected)
                    self.assertEqual(connection.call_args.kwargs["assert_hostname"], expected)
