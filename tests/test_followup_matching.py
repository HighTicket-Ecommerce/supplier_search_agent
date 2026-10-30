import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import job_store, main, master_index


class MatchingFollowupTests(unittest.TestCase):
    def test_completed_observation_jobs_finish_without_inventing_paid_checks(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(tmp)/"jobs.sqlite")}):
            for status, expected in [("completed", 100), ("running", 0), ("limited", 0)]:
                job_store.init_job(status, {"research_mode": "distributor_brands", "verify_directory_brands": False})
                job_store.update_job(status, status=status, observations=[{"supplier_name": "A"}], total=1, processed=0)
                result = main.research_status(status)
                self.assertEqual(result["progress_pct"], expected)
                self.assertEqual(result["processed"], 0)

    def test_non_latin_marks_preserve_identity_through_master_matching(self):
        for stored, candidate, expected in [
            ("クリーン Tools", "グリーン Tools", "domain_match_name_conflict"),
            ("クリーン Tools Ltd", "グリーン Tools", "domain_match_name_conflict"),
            ("कमल Tools Ltd", "कोमल Tools", "domain_match_name_conflict"),
            ("Café Ltd", "Cafe", "existing_domain_match"),
            ("北方 Tools Ltd", "北方 Tools", "existing_domain_match"),
            ("北方 Tools Ltd", "南方 Tools", "domain_match_name_conflict")]:
            with self.subTest(stored=stored, candidate=candidate):
                index = master_index.MasterIndex({"id": "x"*64, "records": [{
                    "supplier_name": stored, "url": "https://example.com", "domain": "example.com",
                    "country": "", "source_row": 2}]})
                self.assertEqual(index.match(candidate, "https://example.com")["status"], expected)
