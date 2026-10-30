import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import job_store, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import ResearchContext, LimitReached


class RawCaptureReviewTests(unittest.TestCase):
    def test_raw_actor_output_survives_page_rejection_and_conversion(self):
        path = Path(__file__).resolve().parents[1]/"docs/benchmarks/cold-plunge-discovery-2026-10-28/run_discovery_check.py"
        spec = importlib.util.spec_from_file_location("review_discovery", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for failure in (False, True):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp, \
                 patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(tmp)/"jobs.sqlite")}):
                request = ResearchRequest(product="Sauna heaters")
                job_store.init_job("raw", request.model_dump()); context = ResearchContext("raw", request)
                records, saves = [], []
                raw = [{"html": "<p>"+"Raw supplier content. "*9000+"</p>", "headers": {"Authorization": "omit"},
                        "crawl": {"httpStatusCode": 500 if failure else 200}}]
                def provider(actor, data, ctx, **kwargs):
                    ctx.reserve("apify", .5, run_id="mock-run", dataset_id="mock-dataset")
                    return raw
                traced = module.trace_actor(provider, records, lambda name, value: saves.append(json.loads(json.dumps(value))), "raw.json")
                web_fetcher._CACHE.clear()
                with patch.object(web_fetcher, "run_actor", side_effect=traced):
                    page = web_fetcher._read_page("https://example.com", context, "raw-http")
                self.assertEqual(records[0]["items"][0]["html"], raw[0]["html"])
                self.assertNotIn("headers", records[0]["items"][0])
                self.assertEqual(saves[0][0]["status"], "started")
                self.assertEqual(records[0]["status"], "returned")
                self.assertEqual(records[0]["input"]["scrapingTool"], "raw-http")
                self.assertEqual(records[0]["actor_runs"][0]["run_id"], "mock-run")
                self.assertEqual(page is None, failure)
                if page:
                    self.assertLess(len(page["text"]), len(raw[0]["html"]))
                def interrupted(*a, **k): raise LimitReached("page_limit")
                traced = module.trace_actor(interrupted, records, lambda *a: None, "raw.json")
                with self.assertRaises(LimitReached): traced("actor", {}, context)
                self.assertEqual((records[-1]["status"], records[-1]["error_type"]), ("error", "LimitReached"))
