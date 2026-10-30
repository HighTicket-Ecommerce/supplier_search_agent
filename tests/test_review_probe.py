import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import web_fetcher
from backend.research_context import LimitReached


class ProbeReviewTests(unittest.TestCase):
    def test_reproducible_probe_modes_have_one_browser_leg_and_no_qualification(self):
        root = Path(__file__).resolve().parents[1]
        path = root/"docs/benchmarks/cold-plunge-2026-10-27/run_fallback_probe.py"
        spec = importlib.util.spec_from_file_location("review_probe", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        raw = json.loads(module.RAW_FIXTURE.read_text())["items"]
        for mode in ("fixture", "live_mock", "failure", "limit"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                def provider(actor, data, context, **options):
                    self.assertEqual(data["scrapingTool"], "browser-playwright")
                    self.assertEqual(options["memory_mb"], 2048)
                    self.assertEqual(options["timeout_seconds"], 60)
                    if mode == "limit":
                        raise LimitReached("external_call_limit")
                    context.reserve("apify", .5, run_id="offline")
                    if mode == "failure":
                        raise RuntimeError("offline provider failure")
                    return [{"text": "Product evidence. "*50}]
                with patch.object(web_fetcher, "run_actor", side_effect=provider) as actor, \
                     patch("backend.model_client.request_structured", side_effect=AssertionError("No model")):
                    result = module.run_probe("https://example.com", Path(tmp)/"probe", raw,
                        browser_items=[{"text": "Offline browser. "*50}] if mode == "fixture" else None)
                self.assertEqual(actor.call_count, 0 if mode == "fixture" else 1)
                self.assertEqual(result["limits"]["pages"], 2)
                self.assertLessEqual(result["limits"]["external_calls"], 1)
                self.assertEqual(result["accepted"], [])
                self.assertEqual(result["exports"], {})
                self.assertEqual(result["status"], "failed" if mode in {"failure", "limit"} else "completed")
                with self.assertRaises(FileExistsError):
                    module.run_probe("https://example.com", Path(tmp)/"probe", raw, browser_items=[])
