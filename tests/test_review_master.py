import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import job_store, main, master_index


class MasterReviewTests(unittest.TestCase):
    def test_unicode_names_keep_their_identity_when_legal_suffixes_are_removed(self):
        self.assertNotEqual(master_index.core_name_key("北方 Tools Ltd"), master_index.core_name_key("南方 Tools Ltd"))
        self.assertEqual(master_index.core_name_key("北方 Tools Ltd"), master_index.core_name_key("北方 Tools"))
        self.assertEqual(master_index.core_name_key("Café GmbH"), master_index.core_name_key("Cafe"))

    def test_progress_counts_skips_without_consuming_verifications(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(tmp)/"jobs.sqlite")}):
            job_store.init_job("progress")
            job_store.update_job("progress", status="completed", total=2, processed=1, skipped=[{"url": "https://known.example"}])
            status = main.research_status("progress")
        self.assertEqual(status["progress_pct"], 100)
        self.assertEqual(status["processed"], 1)
        self.assertEqual(status["completed_count"], 2)

    def test_benchmark_import_needs_no_reference_and_invalid_reference_never_runs(self):
        path = Path(__file__).resolve().parents[1]/"docs/benchmarks/cold-plunge-2026-10-27/run_batch.py"
        spec = importlib.util.spec_from_file_location("review_batch", path)
        module = importlib.util.module_from_spec(spec)
        with patch.object(master_index, "list_references", side_effect=AssertionError("Implicit reference selection")):
            spec.loader.exec_module(module)
        with patch.object(module, "load_reference", side_effect=ValueError("Missing reference")), \
             patch.object(module, "run_research_job") as run:
            with self.assertRaises(ValueError):
                module.run(["any"], master_reference_id="a"*64)
        run.assert_not_called()
