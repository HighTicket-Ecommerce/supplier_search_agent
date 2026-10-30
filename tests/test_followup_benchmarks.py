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

    def test_distributor_main_survives_unavailable_git_comparison(self):
        import os, shutil, sys
        from backend import research_runner, job_store
        helper=load_helper('docs/benchmarks/distributors-2026-10-28/run_preview.py','preview_missing_git')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ), patch.object(sys,'argv',['preview','--round','offline']):
            root=Path(tmp).resolve(); source=root/'docs/benchmarks/distributors-2026-10-28'; source.mkdir(parents=True)
            for name in ['run_preview.py','cases.json','brief.md']:
                shutil.copyfile(ROOT/'docs/benchmarks/distributors-2026-10-28'/name,source/name)
            helper.ROOT=root; helper.__file__=str(source/'run_preview.py')
            with patch.object(helper.subprocess,'check_output',side_effect=subprocess.CalledProcessError(128,['git'])), \
                 patch.object(research_runner,'run_research_job',side_effect=lambda job_id,request:job_store.update_job(job_id,status='completed')):
                helper.main()
            manifest=json.loads(next(root.glob('var/eval/*/offline/manifest.json')).read_text())
            self.assertIsNone(manifest['code_commit']); self.assertIsNone(manifest['production_changes_since_feasibility'])
            self.assertEqual(manifest['comparison']['status'],'unavailable')
            self.assertEqual(manifest['comparison']['baseline_ref'],'docs/distributor-feasibility')

    def test_discovery_main_captures_raw_website_items_before_page_rejection(self):
        import os, shutil, sys
        from backend import master_index, research_runner, supplier_validator, web_fetcher
        helper=load_helper('docs/benchmarks/cold-plunge-discovery-2026-10-28/run_discovery_check.py','discovery_main')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ):
            root=Path(tmp).resolve(); source=root/'docs/benchmarks/cold-plunge-discovery-2026-10-28'; source.mkdir(parents=True)
            for name in ['run_discovery_check.py','brief.md']:
                shutil.copyfile(ROOT/'docs/benchmarks/cold-plunge-discovery-2026-10-28'/name,source/name)
            helper.ROOT=root; helper.__file__=str(source/'run_discovery_check.py')
            os.environ['SUPPLIER_REFERENCE_DIR']=str(root/'references')
            reference=master_index.import_reference('Supplier,Website\nKnown,https://known.example\n')
            argv=['discovery','--round','offline','--master-reference-id',reference['id']]
            candidates=[{'url':'https://candidate'+str(i)+'.example','title':'Candidate '+str(i)} for i in range(3)]
            raw_html='<p>'+('Raw supplier content. '*9000)+'</p>'
            def actor(actor_id,data,context,**kwargs):
                context.reserve('apify',.5,run_id='mock-run',dataset_id='mock-dataset')
                return [{'html':raw_html,'headers':{'Authorization':'secret'},'metadata':{'url':data['query']},
                         'crawl':{'httpStatusCode':500 if 'candidate0' in data['query'] else 200}}]
            with patch.object(sys,'argv',argv), patch.object(helper.subprocess,'check_output',return_value='mock-commit\n'), \
                 patch.object(research_runner,'run_serp_discovery',return_value=candidates), \
                 patch.object(web_fetcher,'run_actor',side_effect=actor), \
                 patch.object(supplier_validator,'analyze_supplier_with_llm',return_value={'error':'offline-fixture'}) as model:
                helper.main()
            output=root/'var/eval/cold-plunge-discovery-2026-10-28/offline'
            records=json.loads((output/'website_actor_records.json').read_text())
            self.assertEqual(len(records),3)
            self.assertEqual(records[0]['items'][0]['crawl']['httpStatusCode'],500)
            self.assertEqual(records[0]['items'][0]['html'],raw_html)
            self.assertNotIn('headers',records[0]['items'][0])
            pages=json.loads((output/'captured_pages.json').read_text())
            self.assertEqual(len(pages),2); self.assertTrue(model.called)
            self.assertTrue(all(len(p['text'])<len(raw_html) for p in pages))
            self.assertEqual(records[0]['actor_runs'][0]['run_id'],'mock-run')

    def test_discovery_audit_accepts_current_items_and_legacy_pages(self):
        import hashlib, os, sys
        from backend import master_index
        helper=load_helper('docs/benchmarks/cold-plunge-discovery-2026-10-28/audit_discovery.py','discovery_audit')
        for field in ['items','pages']:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ):
                root=Path(tmp).resolve(); helper.ROOT=root
                os.environ['SUPPLIER_REFERENCE_DIR']=str(root/'references')
                reference=master_index.import_reference('Supplier,Website\nKnown,https://known.example\n')
                master_path=root/'references'/(reference['id']+'.json')
                labels=root/'docs/benchmarks/cold-plunge-2026-10-27/labels.json'; labels.parent.mkdir(parents=True); labels.write_text('{"cases":[]}')
                output=root/'var/eval/cold-plunge-discovery-2026-10-28/offline'; output.mkdir(parents=True)
                ledger=[{'record_id':'one','domain':'candidate.example','decision':'selected','verification_status':'review'},
                        {'record_id':'two','domain':'candidate.example','decision':'duplicate','duplicate_of':'one','verification_status':'not_checked'}]
                result={'job_id':'offline','accepted':[],'rejected':[],'skipped':[],
                        'review':[{'url':'https://candidate.example','status':'review','reason':'fixture','discovery':{'record_id':'one'}}],
                        'operations':[],'discovery_candidates':ledger,'discovery_coverage':[{'retained_rows':2,'omitted_rows':0}]}
                manifest={'settings':{'master_reference_id':reference['id']},'code_commit':'mock',
                          'source_sha256':{'backend/mock.py':hashlib.sha256(b'mock source').hexdigest()},
                          'master_sha256':hashlib.sha256(master_path.read_bytes()).hexdigest()}
                serp=[{'input':{'countryCode':'us'},field:[{'organicResults':[{'url':'https://candidate.example'},{'url':'https://candidate.example/about'}]}]}]
                for name,value in [('result.json',result),('manifest.json',manifest),('serp.json',serp)]:
                    (output/name).write_text(json.dumps(value))
                with patch.object(sys,'argv',['audit','--round','offline']), patch.object(helper.subprocess,'check_output',return_value=b'mock source'):
                    helper.main()
                audit=json.loads((output/'validation.json').read_text())
                self.assertEqual(audit['raw_organic_rows'],2)
                self.assertTrue(audit['selection_checks']['no_unreported_pool_loss'])
                self.assertFalse(audit['provider_rechecked'])
