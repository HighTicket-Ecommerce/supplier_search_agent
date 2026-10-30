import importlib.util
import io
import os
from contextlib import redirect_stderr
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"

from backend import job_store, supplier_validator, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import LimitReached, ResearchContext


class FetchFallbackTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name)/"jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()
        web_fetcher._CACHE.clear()

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def context(self, **kwargs):
        request = ResearchRequest(product="Complete cold plunge systems", allow_browser_fallback=True,
                                  max_pages_per_supplier=2, **kwargs)
        job_store.init_job("fallback", request.model_dump())
        return ResearchContext("fallback", request)

    def test_saved_provider_timeout_shape_triggers_one_bounded_browser_attempt(self):
        context = self.context(max_pages=2)
        def actor(actor_id, data, ctx, **options):
            ctx.reserve("apify", .5, run_id=data["scrapingTool"], status="SUCCEEDED")
            if data["scrapingTool"] == "raw-http":
                return [{"crawl": {"httpStatusCode": 500, "requestStatus": "failed",
                                   "httpStatusMessage": "request timed out after 30 seconds."},
                         "metadata": {"url": "https://example.com"}, "text": ""}]
            return [{"text": "A complete cold plunge with an integrated chiller. "*20}]
        with patch.object(web_fetcher, "run_actor", side_effect=actor) as run:
            pages = web_fetcher.fetch_website_pages("https://example.com", context)
        self.assertEqual(len(pages), 1)
        self.assertTrue(pages[0]["browser_fallback"])
        self.assertEqual(pages[0]["scraping_tool"], "browser-playwright")
        self.assertEqual(context.pages, 2)
        self.assertEqual(context.calls, 2)
        self.assertEqual(run.call_args_list[1].kwargs["memory_mb"], 2048)
        self.assertEqual(run.call_args_list[1].kwargs["timeout_seconds"], 60)
        self.assertTrue(all(c.args[1]["maxRequestRetries"] == 0 for c in run.call_args_list))

    def test_healthy_raw_response_does_not_launch_browser(self):
        context = self.context(max_pages=2)
        with patch.object(web_fetcher, "run_actor", return_value=[{"text": "Supplier product evidence. "*30}]) as run:
            pages = web_fetcher.fetch_website_pages("https://example.com", context)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(pages[0]["scraping_tool"], "raw-http")
        self.assertNotIn("browser_fallback", pages[0])

    def test_two_empty_attempts_stay_retry_needed_without_model_call(self):
        context = self.context(max_pages=2)
        with patch.object(web_fetcher, "run_actor", return_value=[]) as run, \
             patch.object(supplier_validator, "analyze_supplier_with_llm") as model:
            row = supplier_validator.process_supplier(context.request.product, "https://example.com", context)
        self.assertEqual((row["status"], row["reason"]), ("retry_needed", "website_evidence_unavailable"))
        self.assertEqual(run.call_count, 2)
        model.assert_not_called()

    def test_global_page_limit_prevents_browser_after_last_raw_attempt(self):
        context = self.context(max_pages=1)
        with patch.object(web_fetcher, "run_actor", return_value=[]) as run:
            self.assertEqual(web_fetcher.fetch_website_pages("https://example.com", context), [])
        self.assertEqual((run.call_count, context.pages), (1, 1))

    def test_browser_call_limit_is_propagated_without_retry_loop(self):
        context = self.context(max_pages=2, max_external_calls=1)
        def actor(actor_id, data, ctx, **options):
            ctx.reserve("apify", .5)
            return []
        with patch.object(web_fetcher, "run_actor", side_effect=actor) as run:
            with self.assertRaises(LimitReached):
                web_fetcher.fetch_website_pages("https://example.com", context)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(context.calls, 1)

    def test_preview_refuses_fallback_with_only_one_attempt_before_provider_calls(self):
        path = Path(__file__).parents[1]/"docs/benchmarks/cold-plunge-2026-10-27/run_evidence_check.py"
        spec = importlib.util.spec_from_file_location("fallback_preview_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys, "argv", [str(path), "--cases", "dev-redwood", "--round", "guard-only",
                                      "--pages-per-site", "1", "--browser-fallback"]), \
             patch.object(web_fetcher, "run_actor") as actor, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                module.main()
        self.assertEqual(stopped.exception.code, 2)
        actor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
