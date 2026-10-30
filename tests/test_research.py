import copy
import json
import os
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
import httpx
from openai import OpenAI
import pandas as pd
import requests
from unittest.mock import MagicMock, patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"
os.environ["OPENAI_MODEL"] = "gpt-5.2-2025-12-11"
os.environ["SUPPLIER_API_KEY"] = "offline-test-api-key"
os.environ["SUPPLIER_UI_PASSWORD"] = ""

from fastapi.testclient import TestClient
from backend import main, config, job_store, research_runner, supplier_validator, web_fetcher, actor_client, apify_runner, utils, model_client, filters
from backend.google_shopping_runner import normalize_shopping_items
from backend.models import ResearchRequest, SupplierAnalysis
from backend.research_context import ResearchContext, LimitReached, JobStopped

FIXTURES = Path(__file__).parent / "fixtures"
CASES = json.loads((FIXTURES / "supplier_cases.json").read_text())["cases"]


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name) / "jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()
        self.client = TestClient(main.app, headers={"X-API-Key": "offline-test-api-key"})
        web_fetcher._CACHE.clear()

    def tearDown(self):
        self.client.close()
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def context(self, name="test", **values):
        request = ResearchRequest(product="Sauna heaters", **values)
        job_store.init_job(name, request.model_dump())
        return ResearchContext(name, request)

    @staticmethod
    def decision(**kwargs):
        return {"status": "qualified", "url": kwargs.get("url", "https://homecraftsaunas.com/"),
                "supplier_name": "Homecraft", "evidence": []}

    def test_request_validation_and_preview_defaults(self):
        for values in [{"max_candidate_domains": 0}, {"target_suppliers": -1}, {"max_pages": 0},
                       {"product": "  "},
                       {"candidate_urls": ["javascript:alert(1)"]}, {"allowed_countries": ["Atlantis"]}]:
            with self.subTest(values=values):
                self.assertEqual(self.client.post("/research/start", json={"product": "Sauna", **values}).status_code, 422)
        with self.assertRaises(ValueError):
            ResearchRequest(product="Sauna", max_execution_cost_usd=float("nan"))
        self.assertEqual(self.client.post("/research/start", content='{"product":"Sauna","max_execution_cost_usd":NaN}',
                                         headers={"Content-Type":"application/json"}).status_code, 422)
        request = ResearchRequest(product=" Sauna ", candidate_urls=["homecraftsaunas.com"], allowed_countries=["CA"])
        self.assertTrue(request.preview_only)
        self.assertFalse(request.use_shopping)
        self.assertEqual(request.candidate_urls, ["https://homecraftsaunas.com"])
        self.assertEqual(request.allowed_countries, ["Canada"])

    def test_api_key_is_checked_before_body_parsing_except_health(self):
        anonymous = TestClient(main.app)
        self.addCleanup(anonymous.close)
        self.assertEqual(anonymous.get("/health").status_code, 200)
        for headers in [{}, {"X-API-Key": ""}, {"X-API-Key": "wrong"}]:
            with self.subTest(headers=headers):
                self.assertEqual(anonymous.get("/research/status/test", headers=headers).status_code, 401)
                self.assertEqual(anonymous.post("/research/start", content="{",
                                                headers={**headers, "Content-Type": "application/json"}).status_code, 401)
        self.assertEqual(anonymous.get("/docs").status_code, 401)
        self.assertEqual(self.client.post("/research/start", content="{", headers={"Content-Type": "application/json"}).status_code, 422)
        with patch.object(config, "SUPPLIER_API_KEY", ""):
            self.assertEqual(self.client.get("/research/status/test").status_code, 503)

    def test_spreadsheet_formulas_are_neutralized_in_csv_downloads(self):
        for value in ['=HYPERLINK("https://evil.example")', "+1 604 555 0100", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd"]:
            self.assertEqual(utils.spreadsheet_safe(value), "'" + value)
        for value in ["Homecraft", "", -1, 2.5, None, ["=x"]]:
            self.assertEqual(utils.spreadsheet_safe(value), value)
        frame = pd.DataFrame([{"supplier_name": "=1+1", "score": -1}])
        self.assertEqual(frame.map(utils.spreadsheet_safe).to_csv(index=False).splitlines()[1], "'=1+1,-1")

    def test_seed_only_api_run_never_calls_discovery_or_sheets(self):
        with patch.object(research_runner, "run_serp_discovery") as serp, \
             patch.object(research_runner, "run_google_shopping_discovery") as shopping, \
             patch.object(research_runner, "process_supplier", return_value=self.decision()) as supplier, \
             patch.object(main, "append_supplier_row") as sheet:
            started = self.client.post("/research/start", json={"product": "Sauna heaters", "use_apify": False,
                "use_shopping": True, "candidate_urls": ["https://homecraftsaunas.com/", "https://www.homecraftsaunas.com/about/"]}).json()
            result = self.client.get("/research/result/"+started["job_id"]).json()
            self.assertEqual(result["accepted_count"], 1)
            self.assertEqual(supplier.call_count, 1)
            serp.assert_not_called(); shopping.assert_not_called(); sheet.assert_not_called()
            blocked = self.client.post("/research/export/"+started["job_id"], json={"selected_urls": ["https://homecraftsaunas.com/"]})
            self.assertEqual(blocked.status_code, 403)
            sheet.assert_not_called()

    def test_one_candidate_limit_across_seeds_and_search(self):
        context = self.context(candidate_urls=["https://seed.example"], max_candidate_domains=3)
        rows = [{"url": "https://seed.example/about"}, {"url": "https://www.google.com/search?q=sauna"}]
        rows += [{"url": f"https://supplier-{i}.example"} for i in range(8)]
        with patch.object(research_runner, "run_serp_discovery", return_value=rows) as discovery, \
             patch.object(research_runner, "process_supplier", return_value={"status": "review", "url": "https://fixture.example"}) as supplier:
            research_runner.run_research_job("test", context.request)
        self.assertEqual(supplier.call_count, 3)
        self.assertEqual(discovery.call_count, 1)
        self.assertEqual(job_store.get_job("test")["processed"], 3)

    def test_review_candidates_do_not_count_towards_target(self):
        context = self.context(use_apify=False, candidate_urls=["https://a.example", "https://b.example"], target_suppliers=1)
        with patch.object(research_runner, "process_supplier", side_effect=[{"status":"review","url":"https://a.example"}, {"status":"qualified","url":"https://b.example"}]):
            research_runner.run_research_job("test", context.request)
        self.assertEqual(len(job_store.get_job("test")["accepted"]), 1)
        self.assertEqual(len(job_store.get_job("test")["review"]), 1)
        self.assertEqual(job_store.get_job("test")["processed"], 2)

    def test_shopping_output_is_hints_and_never_official_domains(self):
        raw = json.loads((FIXTURES / "shopping.json").read_text())["rows"]
        result = normalize_shopping_items(raw)
        self.assertEqual(len(result), 10)
        self.assertTrue(all(r["title"] and r["lookup_hint"] for r in result))
        self.assertTrue(all(r["official_company_url"] is None for r in result))
        self.assertTrue(all(r["brand"] is None for r in result))

    def test_shopping_candidates_use_lookup_results_not_product_urls(self):
        context = self.context(allowed_countries=["Canada"], use_shopping=True, target_suppliers=1)
        with patch.object(research_runner, "run_serp_discovery", return_value=[]), \
             patch.object(research_runner, "run_google_shopping_discovery", return_value=[{"lookup_hint":"Coldture", "example_product_url":"https://google.com/search?q=plunge"}]), \
             patch.object(research_runner, "run_serp_brand_lookup", return_value=[{"url":"https://coldture.com/"}]) as lookup, \
             patch.object(research_runner, "process_supplier", return_value={"status":"qualified", "url":"https://coldture.com/"}) as supplier:
            research_runner.run_research_job("test", context.request)
        self.assertEqual(supplier.call_args.args[1], "https://coldture.com/")
        self.assertEqual(supplier.call_args.kwargs["brand_hint"], "Coldture")
        self.assertEqual(lookup.call_args.kwargs["country"], "Canada")

    def test_search_market_navigation_filter_and_limit(self):
        context = self.context()
        pages = [{"organicResults":[{"url":"https://google.ca/search?q=sauna"}, {"url":"https://a.example/a"},
                  {"url":"https://www.a.example/b"}, {"url":"https://b.example"}]}]
        with patch.object(apify_runner, "run_actor", return_value=pages) as actor:
            rows = apify_runner.run_serp_discovery("Sauna", context, country="Canada", limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["domain"], "a.example")
        self.assertEqual(actor.call_args.args[1]["countryCode"], "ca")
        self.assertEqual(actor.call_args.args[1]["maxPagesPerQuery"], 1)
        with patch.object(apify_runner, "run_actor", return_value=[]) as actor:
            apify_runner.run_serp_discovery("Sauna", context, country="United Kingdom", limit=1)
        self.assertEqual(actor.call_args.args[1]["countryCode"], "gb")

    def test_blocklist_matches_labels_not_substrings(self):
        self.assertFalse(hasattr(filters, "TLD_COUNTRY"))
        kept = ["fellowes.com", "championtarget.com", "betsy.com", "abbc.com", "notlowes.com"]
        blocked = ["lowes.com", "www.lowes.com", "target.com", "amazon.co.uk", "wikipedia.org",
                   "en.wikipedia.org", "bbc.co.uk"]
        self.assertEqual([d for d in kept if filters.is_blocked_domain(d)], [])
        self.assertEqual([d for d in blocked if not filters.is_blocked_domain(d)], [])

    def test_serp_flags_blocked_hosts_without_counting_them(self):
        context = self.context()
        pages = [{"organicResults": [{"url": "https://www.amazon.com/plunge"},
                                     {"url": "https://fellowes.com/about"}, {"url": "https://b.example"}]}]
        with patch.object(apify_runner, "run_actor", return_value=pages):
            rows = apify_runner.run_serp_discovery("Sauna", context, country="Canada", limit=1)
        self.assertEqual([r["domain"] for r in rows], ["amazon.com", "fellowes.com"])
        self.assertEqual(rows[0]["skip_reason"], "blocked_domain")
        self.assertNotIn("skip_reason", rows[1])

    def test_captured_supplier_cases_against_real_qualification_gates(self):
        for i, fixture in enumerate(CASES):
            with self.subTest(fixture=fixture["id"]):
                context = self.context(name=str(i))
                with patch.object(supplier_validator,"fetch_website_pages",return_value=fixture["pages"]), \
                     patch.object(supplier_validator,"analyze_supplier_with_llm",return_value=fixture["analysis"]):
                    result = supplier_validator.process_supplier(fixture["product"],fixture["pages"][0]["url"],context)
                self.assertEqual(result["status"], fixture["expected"])
                self.assertIsNone(result["estimated_price_min"])
                self.assertTrue(result["sources"])

    def test_bad_citations_boolean_country_and_identity_stay_in_review(self):
        fixture = CASES[0]
        changes = [{"is_product_company":"false"}, {"country":None}, {"country_basis":"market"},
                   {"matched_product_urls":["https://unrelated.example/product"]}]
        bad = copy.deepcopy(fixture["analysis"])
        bad["evidence"][0]["quote"] = "An invented source quote."
        changes.append(bad)
        for i, change in enumerate(changes):
            with self.subTest(change=change):
                context = self.context(name=str(i))
                analysis = dict(copy.deepcopy(fixture["analysis"]), **change)
                with patch.object(supplier_validator,"fetch_website_pages",return_value=fixture["pages"]), \
                     patch.object(supplier_validator,"analyze_supplier_with_llm",return_value=analysis):
                    result = supplier_validator.process_supplier(fixture["product"],fixture["pages"][0]["url"],context)
                self.assertEqual(result["status"], "review")
        context = self.context(name="hint")
        with patch.object(supplier_validator,"fetch_website_pages",return_value=fixture["pages"]), \
             patch.object(supplier_validator,"analyze_supplier_with_llm",return_value=fixture["analysis"]):
            result = supplier_validator.process_supplier(fixture["product"],fixture["pages"][0]["url"],context,brand_hint="Unrelated Brand")
        self.assertEqual(result["reason"], "shopping_identity_not_established")
        misleading = copy.deepcopy(fixture["analysis"])
        misleading["identity_match"] = "supported"
        misleading["evidence"].append(dict(misleading["evidence"][0], claim="identity"))
        with patch.object(supplier_validator,"fetch_website_pages",return_value=fixture["pages"]), \
             patch.object(supplier_validator,"analyze_supplier_with_llm",return_value=misleading):
            result = supplier_validator.process_supplier(fixture["product"],fixture["pages"][0]["url"],context,brand_hint="Unrelated Brand")
        self.assertEqual(result["reason"], "shopping_identity_not_established")

    def test_empty_page_is_retryable(self):
        context = self.context()
        with patch.object(supplier_validator, "fetch_website_pages", return_value=[]):
            result = supplier_validator.process_supplier("Sauna", "https://homecraftsaunas.com", context)
        self.assertEqual(result["status"], "retry_needed")

    def test_actual_model_request_contains_brief_strict_schema_and_token_cap(self):
        context = self.context()
        response = SimpleNamespace(id="response-fixture", usage=SimpleNamespace(prompt_tokens=50,completion_tokens=100),
            choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=json.dumps(CASES[0]["analysis"])))])
        with patch.object(supplier_validator.client.chat.completions,"create",return_value=response) as create:
            supplier_validator.analyze_supplier_with_llm("Complete cold plunge systems", CASES[0]["pages"], context)
        kwargs = create.call_args.kwargs
        self.assertIn("Complete cold plunge systems", kwargs["messages"][1]["content"])
        self.assertTrue(kwargs["response_format"]["json_schema"]["strict"])
        self.assertEqual(kwargs["extra_body"]["max_completion_tokens"], 1800)
        self.assertGreater(context.exposure, 0)
        self.assertEqual(context.operations[0]["status"], "completed")

    def test_openai_sdk_round_trip_parses_structured_output(self):
        context = self.context()
        sent = []
        def handler(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={"id": "chatcmpl-fixture", "object": "chat.completion", "created": 0,
                "model": config.OPENAI_MODEL, "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
                "choices": [{"index": 0, "finish_reason": "stop", "logprobs": None,
                             "message": {"role": "assistant", "content": json.dumps(CASES[0]["analysis"]), "refusal": None}}]})
        sdk = OpenAI(api_key="offline-test-key", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with patch.object(model_client, "client", sdk):
            result = model_client.request_structured([{"role": "user", "content": "fixture"}], SupplierAnalysis, context,
                                                     schema_name="supplier_analysis")
        self.assertEqual(result, SupplierAnalysis.model_validate(CASES[0]["analysis"]).model_dump())
        self.assertTrue(sent[0]["response_format"]["json_schema"]["strict"])
        self.assertEqual(sent[0]["max_completion_tokens"], config.OPENAI_MAX_OUTPUT_TOKENS)
        self.assertFalse(sent[0]["store"])

    def test_excerpts_preserve_late_email(self):
        pages = [{"url":"https://fixture.example", "text":"Navigation "*1000+" sales@fixture.example"}]
        result = web_fetcher.prompt_pages(pages, "Sauna")
        self.assertTrue(any("sales@fixture.example" in text for text in result[0]["excerpts"]))

    def test_targeted_pages_include_products_and_count_failed_attempts(self):
        context = self.context(max_pages_per_supplier=3)
        first = {"url":"https://fixture.example/", "text":"[Privacy](/privacy) [Product](/products/sauna) [About](/about) [Contact](/contact)"}
        with patch.object(web_fetcher,"fetch_page",side_effect=[first,None,None]) as fetch:
            result = web_fetcher.fetch_website_pages("https://fixture.example/",context)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(fetch.call_args_list[1].args[0], "https://fixture.example/products/sauna")
        self.assertEqual(len(result), 1)

    def test_limits_stop_before_paid_calls(self):
        context = self.context(max_execution_cost_usd=0.5, max_external_calls=1, max_pages=1)
        context.reserve("apify",0.5)
        with self.assertRaises(LimitReached): context.reserve("openai",0.01)
        context.take_page()
        with self.assertRaises(LimitReached): context.take_page()
        context.started -= 301
        with self.assertRaises(LimitReached): context.checkpoint()
        budget = self.context(name="budget", max_execution_cost_usd=0.5)
        budget.reserve("apify", 0.5)
        with self.assertRaisesRegex(LimitReached, "execution_budget_limit"):
            budget.reserve("openai", 0.01)

    def test_queued_stop_survives_worker_start(self):
        context = self.context(candidate_urls=["https://fixture.example"],use_apify=False)
        job_store.update_job("test",status="stopped")
        with patch.object(research_runner,"process_supplier") as supplier:
            research_runner.run_research_job("test",context.request)
        supplier.assert_not_called()
        self.assertEqual(job_store.get_job("test")["status"], "stopped")
        job_store.update_job("test", status="completed")
        self.assertEqual(job_store.get_job("test")["status"], "stopped")

    @staticmethod
    def response(data):
        result = MagicMock();result.ok=True;result.json.return_value=data;return result

    def test_actor_run_uses_server_caps_and_records_run_provenance(self):
        context = self.context()
        session = MagicMock()
        session.request.side_effect = [self.response({"data":{"pricingInfos":[{"pricingModel":"PAY_PER_EVENT"}]}}),
            self.response({"data":{"id":"run-test","buildId":"build-test","status":"SUCCEEDED","defaultDatasetId":"dataset-test"}}), self.response([{"title":"fixture"}])]
        with patch.object(actor_client.requests,"Session",return_value=session):
            rows = actor_client.run_actor("apify/google-search-scraper",{},context)
        self.assertEqual(len(rows),1)
        params = session.request.call_args_list[1].kwargs["params"]
        self.assertEqual(params["maxTotalChargeUsd"],0.5)
        self.assertLessEqual(params["timeout"],90)
        self.assertEqual(context.operations[0]["run_id"],"run-test")
        self.assertEqual(context.exposure,0.5)

    def test_stop_aborts_actor_without_new_paid_run(self):
        context = self.context()
        session = MagicMock()
        session.post.return_value = self.response({"data":{"status":"ABORTED"}})
        session.request.side_effect = [self.response({"data":{"pricingInfos":[{"pricingModel":"PAY_PER_EVENT"}]}}),
            self.response({"data":{"id":"running-test","status":"RUNNING","defaultDatasetId":"dataset-test"}})]
        with patch.object(actor_client.requests,"Session",return_value=session), \
             patch.object(actor_client.time,"sleep",side_effect=lambda _:job_store.update_job("test",status="stopped")):
            with self.assertRaises(JobStopped):actor_client.run_actor("apify/rag-web-browser",{},context)
        session.post.assert_called_once()
        self.assertIn("/running-test/abort",session.post.call_args.args[0])
        self.assertEqual(session.request.call_count,2)
        self.assertEqual(context.operations[0]["abort_status"], "ABORTED")

    def test_unsupported_actor_pricing_rejected_before_start(self):
        context = self.context()
        session=MagicMock();session.request.return_value=self.response({"data":{"pricingInfos":[{"pricingModel":"FREE"}]}})
        with patch.object(actor_client.requests,"Session",return_value=session):
            with self.assertRaises(RuntimeError):actor_client.run_actor("custom/compute-priced",{},context)
        self.assertEqual(session.request.call_count,1)
        self.assertEqual(context.calls,0)

    def test_uncertain_actor_start_is_not_retried(self):
        context = self.context()
        session = MagicMock()
        session.request.side_effect = [self.response({"data":{"pricingInfos":[{"pricingModel":"PAY_PER_EVENT"}]}}), requests.Timeout()]
        with patch.object(actor_client.requests,"Session",return_value=session):
            with self.assertRaises(requests.Timeout):
                actor_client.run_actor("apify/rag-web-browser", {}, context)
        self.assertEqual(session.request.call_count, 2)
        self.assertTrue(context.operations[0]["charge_uncertain"])
        self.assertEqual(context.exposure, 0.5)

    def test_jobs_survive_reopen_and_startup_marks_interruption(self):
        self.context()
        job_store.update_job("test",status="running",review=[{"url":"https://fixture.example"}])
        job_store.recover_interrupted_jobs()
        job=job_store.get_job("test")
        self.assertEqual(job["status"],"interrupted")
        self.assertEqual(len(job["review"]),1)

    def test_explicit_selected_export_is_idempotent_and_uncertain_writes_stay_claimed(self):
        self.context(preview_only=False)
        row={"status":"qualified","url":"https://qualified.example"}
        job_store.update_job("test",status="completed",accepted=[row])
        with patch.object(main,"append_supplier_row",side_effect=TimeoutError) as sheet:
            for _ in range(2):
                response=self.client.post("/research/export/test",json={"selected_urls":[row["url"]]})
                self.assertEqual(response.status_code,200)
            sheet.assert_called_once()
        self.assertEqual(job_store.get_job("test")["exports"][row["url"]],"uncertain_check_sheet_before_retry")
        self.assertEqual(self.client.post("/research/export/test",json={"selected_urls":["https://not-qualified.example"]}).status_code,422)

    def test_successful_selected_export_happens_once_after_research_stops(self):
        self.context(preview_only=False)
        row={"status":"qualified","url":"https://qualified.example"}
        job_store.update_job("test",status="running",accepted=[row])
        payload={"selected_urls":[row["url"],row["url"]]}
        with patch.object(main,"append_supplier_row") as sheet:
            self.assertEqual(self.client.post("/research/export/test",json=payload).status_code,409)
            sheet.assert_not_called()
            job_store.update_job("test",status="completed")
            for _ in range(2):
                self.assertEqual(self.client.post("/research/export/test",json=payload).status_code,200)
            sheet.assert_called_once()
        self.assertEqual(job_store.get_job("test")["exports"][row["url"]],"exported")

    def test_streamlit_seed_preview_flow(self):
        from streamlit.testing.v1 import AppTest
        payloads=[]
        headers=[]
        result={"job_id":"ui-job","status":"completed","accepted":[],"review":[{"url":"https://fixture.example","reason":"requested_product_not_established"}],"rejected":[],"preview_only":True,"limits":{}}
        def request(method,url,**kwargs):
            headers.append(kwargs.get("headers"))
            response=MagicMock()
            if method=="POST":
                payloads.append(kwargs["json"]);response.json.return_value={"job_id":"ui-job"}
            elif "/status/" in url:
                response.json.return_value={"status":"completed","accepted_count":0,"review_count":1,"processed":1,"limits":{}}
            else:response.json.return_value=result
            return response
        with patch("requests.request",side_effect=request):
            ui=AppTest.from_file(str(Path(__file__).parents[1]/"ui"/"streamlit_app.py")).run(timeout=10)
            next(x for x in ui.text_input if x.label=="Product").set_value("Sauna heaters")
            ui.text_area[0].set_value("https://fixture.example")
            next(x for x in ui.checkbox if x.label=="Discover additional suppliers").uncheck()
            next(x for x in ui.button if x.label=="Run research").click().run(timeout=10)
        self.assertFalse(ui.exception)
        self.assertTrue(payloads[0]["preview_only"])
        self.assertFalse(payloads[0]["use_apify"])
        self.assertEqual(payloads[0]["candidate_urls"],["https://fixture.example"])
        self.assertTrue(headers)
        self.assertTrue(all(h=={"X-API-Key":"offline-test-api-key"} for h in headers))

    def test_streamlit_password_gate_blocks_until_correct(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict(os.environ,{"SUPPLIER_UI_PASSWORD":"correct horse battery"}), patch("requests.request") as request:
            ui=AppTest.from_file(str(Path(__file__).parents[1]/"ui"/"streamlit_app.py")).run(timeout=10)
            self.assertEqual([w.label for w in ui.selectbox],[])
            ui.text_input[0].set_value("wrong").run(timeout=10)
            self.assertIn("Incorrect password.",[e.value for e in ui.error])
            ui.text_input[0].set_value("correct horse battery").run(timeout=10)
            self.assertIn("Workflow",[w.label for w in ui.selectbox])
            request.assert_not_called()
        self.assertFalse(ui.exception)

    def test_streamlit_reports_rejected_api_key(self):
        from streamlit.testing.v1 import AppTest
        def request(method,url,**kwargs):
            response=requests.Response();response.status_code=401;response.url=url
            return response
        with patch("requests.request",side_effect=request):
            ui=AppTest.from_file(str(Path(__file__).parents[1]/"ui"/"streamlit_app.py")).run(timeout=10)
            next(b for b in ui.button if b.label=="Load saved master lists").click().run(timeout=10)
        self.assertFalse(ui.exception)
        self.assertTrue(any("rejected the API key" in e.value for e in ui.error))


if __name__ == "__main__":
    unittest.main()
