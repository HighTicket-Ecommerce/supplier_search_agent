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

    def test_distributor_main_writes_effective_sanitized_model_settings(self):
        import os, shutil, sys
        from backend import config, model_client, research_runner, job_store
        helper=load_helper('docs/benchmarks/distributors-2026-10-28/run_preview.py','distributor_preview')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ), patch.object(sys,'argv',['preview','--round','offline']):
            root=Path(tmp).resolve(); source=root/'docs/benchmarks/distributors-2026-10-28'; source.mkdir(parents=True)
            for name in ['run_preview.py','cases.json','brief.md']:
                shutil.copyfile(ROOT/'docs/benchmarks/distributors-2026-10-28'/name,source/name)
            helper.ROOT=root; helper.__file__=str(source/'run_preview.py')
            with patch.multiple(config,OPENAI_MODEL='effective-test-model',OPENAI_MAX_OUTPUT_TOKENS=2048,
                                OPENAI_INPUT_USD_PER_MILLION=2.0,OPENAI_OUTPUT_USD_PER_MILLION=10.0), \
                 patch.object(model_client,'client',__import__('types').SimpleNamespace(base_url='https://user:secret@proxy.example/v1/?token=secret#secret')), \
                 patch.object(helper.subprocess,'check_output',return_value='fake-commit\n'), \
                 patch.object(research_runner,'run_research_job',side_effect=lambda job_id,request:job_store.update_job(job_id,status='completed')):
                helper.main()
            manifest=json.loads(next(root.glob('var/eval/*/offline/manifest.json')).read_text())
            settings=manifest['model_settings']
            self.assertEqual(settings,{'model':'effective-test-model','max_output_tokens':2048,
                'input_usd_per_million':2.0,'output_usd_per_million':10.0,'base_url':'https://proxy.example/v1/'})
            self.assertNotIn('secret',json.dumps(manifest)); self.assertNotIn('user:',json.dumps(manifest))
