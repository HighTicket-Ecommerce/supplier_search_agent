import copy
from html import escape
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"
os.environ["OPENAI_MODEL"] = "gpt-5.2-2025-12-11"
os.environ["SUPPLIER_API_KEY"] = "offline-test-api-key"
os.environ["SUPPLIER_UI_PASSWORD"] = ""

from fastapi.testclient import TestClient
from backend import catalogue_runner, directory_runner, job_store, main, master_index, research_runner, supplier_validator, web_fetcher, public_fetch
from backend.models import ResearchRequest
from backend.research_context import ResearchContext, LimitReached, JobStopped

FIXTURES = Path(__file__).parent / "fixtures"
SHOPIFY = json.loads((FIXTURES / "shopify_catalogue.json").read_text())["items"]


class CatalogueAndMatchingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name) / "jobs.sqlite"),
                                          "SUPPLIER_REFERENCE_DIR": str(Path(self.directory.name) / "references")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()
        self.client = TestClient(main.app, headers={"X-API-Key": "offline-test-api-key"})
        web_fetcher._CACHE.clear()
        self.reference = master_index.import_reference((FIXTURES / "master_sample.csv").read_text(), "master_sample.csv")
        self.index = master_index.MasterIndex(master_index.load_reference(self.reference["id"]))

    def tearDown(self):
        self.client.close()
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def context(self, name="test", **values):
        request = ResearchRequest(product="Complete cold plunge systems", **values)
        job_store.init_job(name, request.model_dump())
        return ResearchContext(name, request)

    @staticmethod
    def products():
        return catalogue_runner.normalize_shopify_products(SHOPIFY, "https://coldture.com/", 50)[0]

    def test_reference_import_is_immutable_minimal_and_reusable(self):
        content = "Supplier,Website,Country,Private Contact\nExample,https://example.com,Canada,private@example.com\n"
        first = self.client.post("/references/master", json={"filename":"../../master.csv", "csv_content":content})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["filename"], "master.csv")
        second = self.client.post("/references/master", json={"csv_content":content}).json()
        self.assertEqual(first.json()["id"], second["id"])
        stored = master_index.load_reference(second["id"])
        self.assertNotIn("private@example.com", json.dumps(stored))
        self.assertEqual(len(self.client.get("/references/master").json()["references"]), 2)
        self.assertEqual(self.client.post("/references/master", json={"csv_content":"wrong,columns\na,b"}).status_code, 422)

    def test_master_identity_traps_are_not_auto_merged(self):
        cases = [
            ("Homecraft", "https://www.homecraftsaunas.com/about", "existing_domain_match"),
            ("Harman", "https://harmanstoves.com", "unmatched"),
            ("Summit", "", "unmatched"),
            ("SaunaSpace", "", "ambiguous"),
            ("Fire Magic", "", "name_match_needs_verification"),
            ("Canadian Spa Company", "https://canadianspacompany.ca/", "existing_domain_match"),
            ("Sunfire", "https://sunfiregrills.com/", "domain_match_name_conflict"),
        ]
        for name, url, expected in cases:
            with self.subTest(name=name, url=url):
                result = self.index.match(name, url)
                self.assertEqual(result["status"], expected)
                self.assertFalse(result["confirmed_new_supplier"])
                self.assertFalse(result["company_identity_verified"])
        brands = self.index.match("Fire Magic", "")
        self.assertEqual(len(brands["matches"]), 1)
        self.assertNotEqual(brands["matches"][0]["supplier_name"], "Real Fyre")
        same_host = self.index.match("Homecraft Inc.", "https://homecraftsaunas.com")
        self.assertEqual(same_host["status"], "existing_domain_match")
        self.assertEqual(same_host["name_relation"], "legal_suffix")
        related = self.index.match("Homecraft", "https://shop.homecraftsaunas.com")
        self.assertEqual(related["status"], "related_domain_needs_verification")
        self.assertEqual(related["basis"], "related_registrable_domain")
        other_site = self.index.match("Fire Magic", "https://unrelated.example")
        self.assertEqual(other_site["status"], "name_match_different_website")
        redirected = self.index.match("Homecraft", "https://old.example",
                                      alternate_urls=("https://www.homecraftsaunas.com/about",))
        self.assertEqual(redirected["status"], "existing_domain_match")
        self.assertEqual(redirected["matched_url"], "https://www.homecraftsaunas.com/about")

    def test_conflicting_names_on_one_host_are_ambiguous(self):
        reference = master_index.import_reference("Supplier,Website\nOne,https://example.com\nTwo,https://www.example.com/about\n")
        index = master_index.MasterIndex(master_index.load_reference(reference["id"]))
        self.assertEqual(index.match("One", "https://example.com")["status"], "ambiguous")

    def test_list_compare_mode_uses_no_providers_or_sheets(self):
        with patch.object(research_runner, "process_supplier") as supplier, \
             patch.object(research_runner, "run_serp_discovery") as search, \
             patch.object(main, "append_supplier_row") as sheet:
            result = self.client.post("/research/start", json={"product":"Supplier comparison", "research_mode":"list_compare",
                "master_reference_id":self.reference["id"], "comparison_rows":[{"supplier_name":"Homecraft", "url":"https://homecraftsaunas.com"},
                {"supplier_name":"Harman"}, {"supplier_name":"SaunaSpace"}]}).json()
            job = self.client.get("/research/result/"+result["job_id"]).json()
        self.assertEqual(job["status"], "completed")
        self.assertEqual([r["master_match"]["status"] for r in job["observations"]], ["existing_domain_match","unmatched","ambiguous"])
        self.assertEqual(job["operations"], [])
        self.assertEqual(job["accepted_count"], 0)
        supplier.assert_not_called(); search.assert_not_called(); sheet.assert_not_called()

    def test_discovery_skips_known_and_blocked_hosts_but_checks_seeds(self):
        context = self.context(use_apify=True, candidate_urls=["https://homecraftsaunas.com"],
                               master_reference_id=self.reference["id"], max_candidate_domains=5)
        discovered = [{"url": "https://canadianspacompany.ca", "discovery_source": "serp"},
                      {"url": "https://www.amazon.com/plunge", "discovery_source": "serp", "skip_reason": "blocked_domain"},
                      {"url": "https://new-plunge.example", "discovery_source": "serp"}]
        with patch.object(research_runner, "run_serp_discovery", return_value=discovered), \
             patch.object(research_runner, "process_supplier",
                          return_value={"status": "review", "supplier_name": "Homecraft",
                                        "url": "https://homecraftsaunas.com"}) as supplier:
            research_runner.run_research_job("test", context.request)
        job = job_store.get_job("test")
        self.assertEqual(supplier.call_count, 2)
        self.assertEqual([c.args[1] for c in supplier.call_args_list],
                         ["https://homecraftsaunas.com", "https://new-plunge.example"])
        self.assertEqual({row["reason"] for row in job["skipped"]}, {"already_in_master", "blocked_domain"})
        self.assertTrue(all(row["reason"] for row in job["skipped"]))

    def test_missing_reference_and_invalid_mode_inputs_fail_before_work(self):
        for payload in [{"research_mode":"list_compare"}, {"research_mode":"distributor_brands"},
                        {"master_reference_id":"a"*64}, {"max_catalogue_products":0}, {"max_directory_entries":0}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/research/start", json={"product":"Saunas", **payload}).status_code, 422)
        with self.assertRaises(ValueError): master_index.load_reference("../../other")

    def test_supplier_result_contains_master_match_using_resolved_url(self):
        context = self.context(use_apify=False, candidate_urls=["https://old.example"], master_reference_id=self.reference["id"])
        with patch.object(research_runner, "process_supplier", return_value={"status":"qualified", "supplier_name":"Homecraft", "url":"https://homecraftsaunas.com"}):
            research_runner.run_research_job("test", context.request)
        self.assertEqual(job_store.get_job("test")["accepted"][0]["master_match"]["status"], "existing_domain_match")

    def test_redirected_duplicate_sites_do_not_inflate_target(self):
        context = self.context(use_apify=False, candidate_urls=["https://old.example", "https://other.example"], target_suppliers=2)
        with patch.object(research_runner, "process_supplier", return_value={"status":"qualified", "url":"https://homecraftsaunas.com"}):
            research_runner.run_research_job("test", context.request)
        job = job_store.get_job("test")
        self.assertEqual(len(job["accepted"]), 1)
        self.assertEqual(job["review"][0]["reason"], "duplicate_resolved_website")

    def test_captured_brand_links_deduplicate_and_keep_aliases_separate(self):
        fixture = json.loads((FIXTURES / "directory_links.json").read_text())
        html = "".join('<a href="'+escape(link["url"])+'">'+escape(link["text"])+"</a>" for link in fixture["brand_links"])
        html += '<a href="https://other.example/brands/incorrect">Wrong host</a>'
        rows = directory_runner.extract_html_brands(html, fixture["source_url"])
        self.assertEqual(len(rows), 120)
        names = {r["supplier_name"] for r in rows}
        self.assertIn("NAVAC", names); self.assertIn("NAVAC Inc", names)
        self.assertNotIn("Clearance", names); self.assertNotIn("Miscellaneous", names); self.assertNotIn("Wrong host", names)

    def test_captured_arizona_facet_is_brands_not_all_products(self):
        payload = json.loads((FIXTURES / "arizona_brands.json").read_text())
        rows, total = directory_runner.extract_arizona_brands(payload, "https://www.shop.arizonafireplaces.com/api/graph")
        self.assertEqual(len(rows), 37)
        self.assertEqual(total, 1708)
        self.assertTrue(all(r["directory_entry_url"] is None for r in rows))

    def test_directory_mode_caps_entries_and_does_not_verify_by_default(self):
        context = self.context(research_mode="distributor_brands", directory_urls=["https://directory.example/brands"], max_directory_entries=2)
        payload = {"data":{"catalog":{"products":{"totalCount":10,"facets":{"facets":[{"name":"U_GL_Brand","values":[{"title":name,"count":1} for name in ["One","Two","Three"]]}]}}}}}
        context.request.directory_urls = ["https://www.shop.arizonafireplaces.com/"]
        source = {"url":"https://www.shop.arizonafireplaces.com/api/graph", "text":json.dumps(payload), "retrieved_at":1, "body_sha256":"fixture"}
        with patch.object(directory_runner, "fetch_public", return_value=source), \
             patch.object(research_runner, "run_serp_brand_lookup") as lookup, patch.object(research_runner, "process_supplier") as supplier:
            research_runner.run_research_job("test", context.request)
        job = job_store.get_job("test")
        self.assertEqual(len(job["observations"]), 2)
        self.assertTrue(job["directory_coverage"][0]["truncated"])
        self.assertEqual(job["directory_coverage"][0]["products_extracted"], 0)
        self.assertEqual(len(job["accepted"]), 0)
        lookup.assert_not_called(); supplier.assert_not_called()

    def test_directory_lookup_supplies_identity_hint_and_source(self):
        context = self.context(research_mode="distributor_brands", directory_urls=["https://directory.example"], verify_directory_brands=True, target_suppliers=1)
        row={"supplier_name":"Fire Magic", "source_url":"https://directory.example", "observation_id":"fixture"}
        with patch.object(research_runner,"fetch_directory",return_value=([row],{})), \
             patch.object(research_runner,"run_serp_brand_lookup",return_value=[{"url":"https://firemagicgrills.com"}]), \
             patch.object(research_runner,"process_supplier",return_value={"status":"review", "url":"https://firemagicgrills.com"}) as supplier:
            research_runner.run_research_job("test", context.request)
        self.assertEqual(supplier.call_args.kwargs["brand_hint"], "Fire Magic")
        self.assertEqual(job_store.get_job("test")["review"][0]["discovery"]["directory_source_url"], row["source_url"])

    def test_unrecognized_directory_is_an_explicit_failure(self):
        context = self.context(research_mode="distributor_brands", directory_urls=["https://directory.example"])
        with patch.object(research_runner,"fetch_directory",side_effect=ValueError("Unsupported")):
            research_runner.run_research_job("test", context.request)
        job=job_store.get_job("test")
        self.assertEqual(job["status"], "failed")
        self.assertTrue(job["warnings"])

    def test_directory_browser_fallback_retains_caps_and_provenance(self):
        context=self.context(allow_browser_fallback=True)
        fixture=json.loads((FIXTURES/"directory_links.json").read_text())
        html="".join('<a href="'+escape(link["url"])+'">'+escape(link["text"])+"</a>" for link in fixture["brand_links"])
        def actor(*args,**kwargs):
            context.reserve("apify",.5,run_id="browser-fixture",dataset_id="dataset-fixture")
            return [{"html":html}]
        with patch.object(directory_runner,"fetch_public",side_effect=public_fetch.PublicFetchError("timeout")), \
             patch.object(directory_runner,"run_actor",side_effect=actor) as run:
            rows,coverage=directory_runner.fetch_directory(fixture["source_url"],context,limit=200)
        self.assertEqual(len(rows),120)
        self.assertEqual(coverage["adapter"],"browser_brand_links")
        self.assertEqual(coverage["actor_run_id"],"browser-fixture")
        self.assertEqual(run.call_args.args[1]["outputFormats"],["html"])
        self.assertEqual(run.call_args.kwargs["result_limit"],1)
        self.assertEqual(run.call_args.kwargs["memory_mb"],2048)

    def test_shopify_major_units_and_unknown_currency(self):
        products = self.products()
        by_id={p["product_id"]:p for p in products}
        vent=by_id["10328014487798"]
        self.assertEqual(vent["currency"], "CAD")
        self.assertEqual(vent["variants"][0]["price"], 39.99)
        changed=copy.deepcopy(SHOPIFY[:1]);changed[0]["currency"]="$";changed[0]["variants"][0]["price"]=float("nan")
        normalized,_=catalogue_runner.normalize_shopify_products(changed,"https://coldture.com",1)
        self.assertIsNone(normalized[0]["currency"]);self.assertIsNone(normalized[0]["variants"][0]["price"])
        self.assertIsNone(catalogue_runner.money("1e999"))
        wrong_schema=[{"id":1,"title":"Other actor cents","price":3999}]
        self.assertEqual(catalogue_runner.normalize_shopify_products(wrong_schema,"https://coldture.com",1)[0], [])

    def test_catalogue_actor_receives_product_cap_and_no_enrichment(self):
        context=self.context(max_catalogue_products=2)
        def actor(*args, **kwargs):
            context.reserve("apify",.5,run_id="fixture-run",dataset_id="fixture-dataset")
            return SHOPIFY[:2]
        with patch.object(catalogue_runner,"run_actor",side_effect=actor) as run:
            sample=catalogue_runner.fetch_shopify_catalogue("https://coldture.com",context)
        self.assertEqual(run.call_args.args[1]["maxProducts"],2)
        self.assertFalse(run.call_args.args[1]["includeInventoryDetails"])
        self.assertEqual(run.call_args.kwargs["result_limit"],2)
        self.assertEqual(sample["source"]["actor_run_id"],"fixture-run")
        self.assertFalse(sample["coverage"]["complete_catalogue"])
        self.assertEqual(context.pages,1)

    @staticmethod
    def decision(product, **changes):
        return {"product_id":product["product_id"],"status":"eligible","product_kind":"primary",
                "eligible_variant_ids":[v["variant_id"] for v in product["variants"]], "quote":product["title"], "reason":"fixture", **changes}

    def test_unknown_product_or_variant_and_fabricated_quotes_stay_review(self):
        product=self.products()[0]
        for change in [{"product_id":"invented"},{"eligible_variant_ids":["invented"]}, {"quote":"This is invented"},
                       {"product_kind":"accessory"},{"eligible_variant_ids":[]}]:
            result=catalogue_runner.validate_product_decisions([product],{"products":[self.decision(product,**change)]})
            self.assertEqual(result[0]["status"],"review")
            self.assertEqual(catalogue_runner.observed_price_ranges(result),[])
        decision=self.decision(product)
        self.assertEqual(catalogue_runner.validate_product_decisions([product],{"products":[decision,decision]})[0]["status"],"review")

    def test_accessories_services_unknown_bundles_and_currency_are_separated(self):
        products=self.products()
        complete={"9304102240502","9211401011446"}
        decisions=[self.decision(p, status="eligible" if p["product_id"] in complete else "review",
                                  product_kind="primary" if p["product_id"] in complete else "unknown") for p in products]
        result=catalogue_runner.validate_product_decisions(products,{"products":decisions})
        ranges=catalogue_runner.observed_price_ranges(result)
        self.assertEqual([(r["currency"],r["minimum"],r["maximum"]) for r in ranges],[("CAD",4499.0,12999.0)])
        self.assertEqual(ranges[0]["product_count"],2)
        usd=copy.deepcopy(next(p for p in result if p["status"]=="eligible"));usd["currency"]="USD"
        usd["variants"][0]["price"]=100.0
        currencies={r["currency"] for r in catalogue_runner.observed_price_ranges(result+[usd])}
        self.assertEqual(currencies,{"CAD","USD"})
        self.assertNotIn(39.99,[v["price"] for r in ranges for v in r["observations"]])

    def test_cheaper_tub_only_variant_does_not_set_complete_system_price(self):
        product={"product_id":"system","url":"https://example.com/system","title":"Tub with chiller bundle", "description":"Includes tub and chiller.",
                 "currency":"CAD","variants":[{"variant_id":"tub","title":"Tub only","price":499,"available":True},
                 {"variant_id":"bundle","title":"Tub and chiller","price":4499,"available":True}]}
        result=catalogue_runner.validate_product_decisions([product],{"products":[self.decision(product,eligible_variant_ids=["bundle"])]})
        self.assertEqual(catalogue_runner.observed_price_ranges(result)[0]["minimum"],4499)
        result[0]["variants"][1]["available"]=False
        self.assertEqual(catalogue_runner.observed_price_ranges(result),[])

    def test_catalogue_classification_partial_results_survive_later_limit(self):
        context=self.context()
        products=self.products()[:6]
        catalogue={"website_url":"https://coldture.com","products":products,"source":{},"coverage":{"complete_catalogue":False}}
        first={"products":[self.decision(p,status="review",product_kind="unknown") for p in products[:5]]}
        with patch.object(catalogue_runner,"request_structured",side_effect=[first,LimitReached("execution_budget_limit")]):
            with self.assertRaises(LimitReached):catalogue_runner.analyze_catalogue(catalogue,context)
        saved=job_store.get_job("test")["catalogues"]["https://coldture.com"]
        self.assertEqual(len(saved["products"]),6)
        self.assertEqual(saved["products"][-1]["reason"],"classification_pending")

    def test_browser_fallback_is_conditional_and_counts_both_attempts(self):
        context=self.context(allow_browser_fallback=True,max_pages_per_supplier=2,max_pages=2)
        def actor(*args, **kwargs):
            context.reserve("apify",.5,run_id="fixture",dataset_id="fixture")
            text="Enable JavaScript" if args[1]["scrapingTool"]=="raw-http" else "Supplier product evidence "*30
            return [{"text":text}]
        with patch.object(web_fetcher,"run_actor",side_effect=actor) as run:
            pages=web_fetcher.fetch_website_pages("https://example.com",context)
        self.assertTrue(pages[0]["browser_fallback"])
        self.assertEqual(context.pages,2)
        self.assertEqual([call.args[1]["scrapingTool"] for call in run.call_args_list],["raw-http","browser-playwright"])
        other=self.context(name="off",allow_browser_fallback=False)
        with patch.object(web_fetcher,"run_actor",return_value=[]) as run:
            self.assertEqual(web_fetcher.fetch_page("https://other.example",other),None)
        self.assertEqual(run.call_count,1)

    def test_browser_fallback_respects_per_supplier_limit(self):
        context=self.context(allow_browser_fallback=True,max_pages_per_supplier=1)
        with patch.object(web_fetcher,"run_actor",return_value=[]) as run:
            self.assertEqual(web_fetcher.fetch_website_pages("https://example.com",context),[])
        self.assertEqual(run.call_count,1)

    def test_contacts_keep_sources_and_reject_year_ranges(self):
        pages=[{"url":"https://example.com/contact", "text":"Sales@Example.com +1 (604) 555-1234. Since 1960-2026."}]
        contacts=supplier_validator.verified_contacts(pages,"sales@example.com","+1 (604) 555-1234")
        self.assertEqual(len(contacts),2)
        self.assertEqual(contacts[1]["normalized_value"],"16045551234")
        self.assertEqual(contacts[0]["source_urls"],[pages[0]["url"]])
        self.assertEqual(supplier_validator.verified_contacts(pages,None,"1960-2026"),[])

    def test_accessory_only_evidence_does_not_rule_out_supplier(self):
        fixture=json.loads((FIXTURES/"supplier_cases.json").read_text())["cases"][0]
        analysis=dict(fixture["analysis"],product_kind="accessory")
        context=self.context()
        with patch.object(supplier_validator,"fetch_website_pages",return_value=fixture["pages"]), \
             patch.object(supplier_validator,"analyze_supplier_with_llm",return_value=analysis):
            result=supplier_validator.process_supplier("Complete cold plunge systems",fixture["pages"][0]["url"],context)
        self.assertEqual(result["status"],"review")
        self.assertEqual(result["reason"],"accessory_or_service_evidence_does_not_establish_primary_product")

    def test_public_directory_fetch_rejects_local_network_and_body_limit(self):
        addresses=[(socket.AF_INET,socket.SOCK_STREAM,6,"",("127.0.0.1",443))]
        with patch.object(socket,"getaddrinfo",return_value=addresses):
            with self.assertRaises(ValueError):public_fetch.check_public_url("https://localhost")
        context=self.context()
        response=MagicMock();response.status=200;response.stream.return_value=[b"0123456789"]
        pool=MagicMock();pool.urlopen.return_value=response
        with patch.object(public_fetch,"check_public_url",return_value="93.184.216.34"),patch.object(public_fetch,"_connection",return_value=pool):
            with self.assertRaises(ValueError):public_fetch.fetch_public("https://example.com",context,max_bytes=5)
        self.assertEqual(context.pages,1);self.assertEqual(context.calls,1);self.assertEqual(context.exposure,0)

    def test_streamlit_list_compare_and_directory_payloads(self):
        from streamlit.testing.v1 import AppTest
        for mode in ["list_compare", "distributor_brands"]:
            calls=[]
            def request(method, url, **kwargs):
                if method == "POST":
                    calls.append(kwargs["json"])
                    payload={"job_id":"ui-fixture","status":"queued"}
                elif "/status/" in url:
                    payload={"status":"completed","accepted_count":0,"review_count":0,"processed":0,"limits":{}}
                else:
                    payload={"job_id":"ui-fixture","status":"completed","accepted":[],"review":[],"rejected":[],"preview_only":True,"limits":{}}
                response=MagicMock();response.json.return_value=payload;return response
            with patch("requests.request",side_effect=request):
                app=AppTest.from_file(str(Path(__file__).parents[1]/"ui"/"streamlit_app.py")).run()
                next(w for w in app.selectbox if w.label=="Workflow").set_value(mode).run()
                if mode == "list_compare":
                    app.session_state.master_references=[self.reference]
                    app.run()
                    next(w for w in app.selectbox if w.label=="Compare against").set_value(self.reference["id"]).run()
                    next(w for w in app.text_area if w.label=="Or supplier names, one per line").set_value("Homecraft\nHarman").run()
                else:
                    next(w for w in app.text_input if w.label=="Product").set_value("Gas logs").run()
                    next(w for w in app.text_area if w.label=="Distributor brand directories").set_value("https://directory.example/brands").run()
                next(w for w in app.button if w.label=="Run research").click().run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(calls[0]["research_mode"],mode)
            self.assertTrue(calls[0]["preview_only"])
            if mode == "list_compare":
                self.assertEqual(len(calls[0]["comparison_rows"]),2)
                self.assertEqual(calls[0]["master_reference_id"],self.reference["id"])
            else:
                self.assertFalse(calls[0]["verify_directory_brands"])
                self.assertEqual(calls[0]["directory_urls"],["https://directory.example/brands"])


if __name__ == "__main__":
    unittest.main()
