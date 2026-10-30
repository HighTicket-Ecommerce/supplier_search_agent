import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import job_store, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class TradeReviewTests(unittest.TestCase):
    def test_distinct_policy_remains_after_generic_or_failed_dealer_page(self):
        for failure in (False, True):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp, \
                 patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(tmp)/"jobs.sqlite")}):
                request = ResearchRequest(product="Gas grills", allowed_supplier_types=["Distributor"], allowed_countries=[],
                                          max_pages_per_supplier=4, max_pages=4)
                job_store.init_job("trade", request.model_dump()); context = ResearchContext("trade", request)
                calls = []
                def fetch(url, ctx, **kwargs):
                    ctx.take_page(); calls.append(url)
                    if len(calls) == 1:
                        return {"url": url, "text": "[Dealers](/dealers) [Wholesale](/wholesale)"}
                    if url.endswith("/dealers"):
                        if failure: raise RuntimeError("Provider failed")
                        return {"url": url, "text": "Find a local dealer."}
                    return {"url": url, "text": "We are a wholesale distributor. Trade customers only."}
                with patch.object(web_fetcher, "fetch_page", side_effect=fetch):
                    pages = web_fetcher.fetch_website_pages("https://example.com", context)
                self.assertEqual(calls, ["https://example.com", "https://example.com/dealers", "https://example.com/wholesale"])
                self.assertIn("Trade customers only", pages[-1]["text"])
                self.assertLessEqual(context.pages, 4)

    def test_only_one_account_entry_is_attempted_without_discarding_policy(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(tmp)/"jobs.sqlite")}):
            request = ResearchRequest(product="Gas grills", allowed_supplier_types=["Distributor"], allowed_countries=[], max_pages_per_supplier=4)
            job_store.init_job("trade", request.model_dump()); context = ResearchContext("trade", request)
            calls = []
            def fetch(url, ctx, **kwargs):
                ctx.take_page(); calls.append(url)
                return {"url": url, "text": "[Login](/login) [Register](/register) [Wholesale](/wholesale)" if len(calls) == 1 else "Public page"}
            with patch.object(web_fetcher, "fetch_page", side_effect=fetch):
                web_fetcher.fetch_website_pages("https://example.com", context)
            self.assertEqual(len([u for u in calls if web_fetcher._public_trade_entry(u)]), 1)
            self.assertIn("https://example.com/wholesale", calls)
