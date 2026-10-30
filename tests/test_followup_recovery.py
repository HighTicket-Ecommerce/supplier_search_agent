import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import job_store

class RecoveryFollowupTests(unittest.TestCase):
    def test_stopped_jobs_finalize_stale_ledger_rows_once_and_preserve_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'SUPPLIER_JOB_DB':str(Path(tmp)/'jobs.sqlite')}):
            rows=[{'record_id':str(i),'verification_status':status,'detail':'preserve'} for i,status in enumerate(['checking','pending','qualified','review','excluded','not_checked'])]
            expected=copy.deepcopy(rows)
            for row,status in zip(expected,['interrupted','not_checked']):
                row.update(verification_status=status,verification_stop_reason='backend_restarted')
            for status in ['stopped','completed','failed']:
                job_store.init_job(status,{}); job_store.update_job(status,status=status,discovery_candidates=rows)
            job_store.recover_interrupted_jobs()
            stopped=job_store.get_job('stopped')
            self.assertEqual(stopped['status'],'stopped'); self.assertEqual(stopped['discovery_candidates'],expected)
            for status in ['completed','failed']:
                self.assertEqual(job_store.get_job(status)['discovery_candidates'],rows)
            job_store.recover_interrupted_jobs(); self.assertEqual(job_store.get_job('stopped'),stopped)
