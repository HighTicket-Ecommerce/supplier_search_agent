import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import job_store


class RestartReviewTests(unittest.TestCase):
    def test_restart_finishes_only_unfinished_ledger_rows_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(tmp)/"jobs.sqlite")}):
            rows = [{"record_id": str(i), "verification_status": status} for i, status in enumerate(
                ["checking", "pending", "qualified", "review", "retry_needed", "not_checked", "interrupted"])]
            for status in ("running", "queued", "completed"):
                job_store.init_job(status)
                job_store.update_job(status, status=status, discovery_candidates=copy.deepcopy(rows))
            job_store.init_job("legacy")
            job_store.recover_interrupted_jobs()
            for status in ("running", "queued"):
                result = job_store.get_job(status)
                self.assertEqual(result["status"], "interrupted")
                actual = result["discovery_candidates"]
                self.assertEqual([r["verification_status"] for r in actual[:2]], ["interrupted", "not_checked"])
                self.assertTrue(all(r["verification_stop_reason"] == "backend_restarted" for r in actual[:2]))
                self.assertEqual(actual[2:], rows[2:])
            self.assertEqual(job_store.get_job("completed")["discovery_candidates"], rows)
            self.assertEqual(job_store.get_job("legacy")["status"], "interrupted")
            before = job_store.get_job("running")
            job_store.recover_interrupted_jobs()
            self.assertEqual(job_store.get_job("running"), before)
