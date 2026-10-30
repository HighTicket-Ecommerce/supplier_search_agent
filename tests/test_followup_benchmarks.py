import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load_helper(relative,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class BenchmarkFollowupTests(unittest.TestCase):
    def test_fallback_probe_runs_without_git_metadata(self):
        helper=load_helper('docs/benchmarks/cold-plunge-2026-10-27/run_fallback_probe.py','fallback_probe')
        raw=json.loads((ROOT/'tests/fixtures/raw_fetch_timeout.json').read_text())['items']
        browser=[{'markdown':'Captured product page. '*80,'metadata':{'url':'https://example.com'}}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(helper.subprocess,'check_output',side_effect=subprocess.CalledProcessError(128,['git'])):
            output=Path(tmp)/'probe'; result=helper.run_probe('https://example.com',output,raw,browser_items=browser)
            self.assertEqual(result['status'],'completed')
            self.assertIsNone(json.loads((output/'manifest.json').read_text())['code_commit'])
            self.assertEqual(len(json.loads((output/'fetch_attempts.json').read_text())),2)
