import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"
os.environ["SUPPLIER_API_KEY"] = "offline-test-api-key"

from fastapi.testclient import TestClient
from backend import apify_runner, job_store, main, master_index, research_runner
from backend.discovery_selection import (MAX_ORGANIC_ROWS_PER_PAGE, MAX_SERP_PAGES,
                                         select_serp_candidates)
from backend.models import ResearchRequest
from backend.research_context import JobStopped, LimitReached, ResearchContext


def row(host, **extra):
    return dict(url="https://" + host, **extra)


def page(query, *rows):
    return {"searchQuery": {"term": query}, "organicResults": list(rows)}


def select(pages, **kwargs):
    return select_serp_candidates(pages, country="United States", limit=kwargs.pop("limit", 3), **kwargs)


class DiscoverySelectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name) / "jobs.sqlite"),
            "SUPPLIER_REFERENCE_DIR": str(Path(self.directory.name) / "references")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def context(self, name="test", **kwargs):
        request = ResearchRequest(product="Sauna heaters", allowed_countries=["United States"], **kwargs)
        job_store.init_job(name, request.model_dump())
        return ResearchContext(name, request)

    def master(self):
        return master_index.import_reference("Supplier,Website\nKnown,https://known.example\n")['id']

    @staticmethod
    def decision(product, url, context, **kwargs):
        return {"url": url, "supplier_name": "Candidate", "status": "review", "reason": "fixture_review"}

    def test_queries_take_turns_before_one_query_fills_the_limit(self):
        chosen, records, coverage = select([
            page("manufacturer", row("a.example"), row("b.example"), row("c.example")),
            page("brand", row("d.example"), row("e.example"))])
        self.assertEqual([r["domain"] for r in chosen], ["a.example", "d.example", "b.example"])
        self.assertEqual(coverage["query_count"], 2)
        self.assertEqual(len(records), 5)
        self.assertEqual(sum(r["decision"] == "not_selected" for r in records), 2)

    def test_known_and_seen_hosts_are_filtered_before_selecting_checks(self):
        chosen, records, _ = select([page("manufacturer", row("known.example"), row("seed.example"),
            row("fresh.example"))], limit=1, known_domains={"known.example"}, seen_domains={"seed.example"})
        self.assertEqual([r["domain"] for r in chosen], ["fresh.example"])
        self.assertEqual([r["reason"] for r in records[:2]], ["already_in_master", "already_seen"])

    def test_late_blocked_and_known_rows_are_recorded_after_check_limit(self):
        context = self.context()
        pages = [page("manufacturer", row("fresh.example"), row("amazon.com"), row("known.example")),
                 page("brand", row("youtube.com"), row("later.example"))]
        with patch.object(apify_runner, "run_actor", return_value=pages) as actor:
            chosen = apify_runner.run_serp_discovery("Sauna", context, limit=1, known_domains={"known.example"})
        self.assertEqual(actor.call_count, 1)
        self.assertEqual({r["domain"] for r in chosen if r.get("skip_reason")},
                         {"amazon.com", "known.example", "youtube.com"})
        self.assertEqual(len(job_store.get_job("test")["discovery_candidates"]), 5)
        self.assertEqual([r["domain"] for r in chosen if not r.get("skip_reason")], ["fresh.example"])

    def test_duplicate_domains_do_not_consume_query_turns_or_check_slots(self):
        chosen, records, _ = select([page("manufacturer", row("a.example"), row("b.example")),
            page("brand", row("www.a.example/path"), row("c.example"))])
        self.assertEqual([r["domain"] for r in chosen], ["a.example", "c.example", "b.example"])
        duplicate = records[2]
        self.assertEqual(duplicate["reason"], "duplicate_domain")
        self.assertEqual(duplicate["duplicate_of"], chosen[0]["record_id"])

    def test_better_occurrence_of_same_host_is_not_hidden_by_an_earlier_article(self):
        chosen, records, _ = select([page("manufacturer", row("same.example/blogs/best-models")),
            page("brand", row("same.example/products/heater"))], limit=1)
        self.assertEqual(chosen[0]["url"], "https://same.example/products/heater")
        self.assertEqual(records[0]["reason"], "duplicate_domain")
        self.assertEqual(records[0]["duplicate_of"], chosen[0]["record_id"])

    def test_search_hints_deprioritize_articles_and_comparisons_without_excluding_them(self):
        pages = [page("manufacturer", row("publisher.example/best-saunas", title="Best Saunas, Tested"),
            row("store.example", description="Compare technical specs and prices all in one place."),
            row("company.example", title="Our sauna heaters"))]
        chosen, _, _ = select(pages, limit=1)
        self.assertEqual(chosen[0]["domain"], "company.example")
        chosen, records, _ = select(pages, limit=3)
        self.assertEqual([r["domain"] for r in chosen], ["company.example", "store.example", "publisher.example"])
        self.assertTrue(all(r["decision"] == "selected" for r in records))
        self.assertFalse(any(r.get("status") == "qualified" for r in records))

    def test_support_pages_are_lower_priority_and_generic_best_marketing_is_not_editorial(self):
        chosen, _, _ = select([page("brand", row("help.company.example/hc/en/setup"),
            row("company.example/products/heater", title="The best sauna heater"))], limit=1)
        self.assertEqual(chosen[0]["domain"], "company.example")
        self.assertEqual(chosen[0]["source_hints"], [])

    def test_compact_hyphenated_and_year_prefixed_roundups_get_lower_priority(self):
        for path, title in [("/guide", "2026 Top10 Heater Brands Review"),
                            ("/guide", "Top-10 Sauna Heaters"),
                            ("/2025-top10-heater-brands-review", "Heater Guide"),
                            ("/2026_top_10_heaters", "Heater Guide")]:
            with self.subTest(path=path, title=title):
                chosen, records, _ = select([page("manufacturer", row("roundup.example" + path, title=title),
                    row("company.example"))], limit=1)
                self.assertEqual(chosen[0]["domain"], "company.example")
                self.assertIn("editorial_comparison", records[0]["source_hints"])
                self.assertEqual(records[0]["decision"], "not_selected")

    def test_top_quality_and_numbered_product_names_are_not_roundup_hints(self):
        for title in ["Top quality sauna heaters", "Desktop10 Heater", "Best selling heater"]:
            with self.subTest(title=title):
                chosen, _, _ = select([page("brand", row("company.example", title=title))], limit=1)
                self.assertEqual(chosen[0]["source_hints"], [])

    def test_identity_lookup_retains_organic_order_and_exact_query(self):
        context = self.context()
        pages = [page("identity", row("publisher.example/best-heaters"), row("company.example"))]
        with patch.object(apify_runner, "run_actor", return_value=pages) as actor:
            candidates = apify_runner.run_serp_brand_lookup("Brand", "Sauna", context, limit=1)
        self.assertEqual(candidates[0]["domain"], "publisher.example")
        self.assertEqual(actor.call_args.args[1]["queries"], "Brand Sauna official website")
        self.assertFalse(job_store.get_job("test")["discovery_coverage"][0]["source_hints_enabled"])

    def test_related_hosts_are_not_automatically_treated_as_exact_master_matches(self):
        chosen, _, _ = select([page("brand", row("shop.known.example"))],
                              known_domains={"known.example"}, limit=1)
        self.assertEqual(chosen[0]["domain"], "shop.known.example")

    def test_identity_lookup_filters_known_hosts_before_its_limit(self):
        context = self.context()
        with patch.object(apify_runner, "run_actor", return_value=[page("identity",
                row("known.example"), row("fresh.example"))]):
            candidates = apify_runner.run_serp_brand_lookup("Brand", "Sauna", context,
                limit=1, known_domains={"known.example"})
        self.assertEqual([r["domain"] for r in candidates if not r.get("skip_reason")], ["fresh.example"])
        self.assertEqual(candidates[0]["skip_reason"], "already_in_master")

    def test_processing_failure_keeps_a_join_to_its_selection_record(self):
        context = self.context(max_candidate_domains=1)
        with patch.object(apify_runner, "run_actor", return_value=[page("brand", row("a.example"))]), \
             patch.object(research_runner, "process_supplier", side_effect=ValueError("fixture")):
            research_runner.run_research_job("test", context.request)
        job = job_store.get_job("test")
        self.assertEqual(job["review"][0]["discovery"]["record_id"], job["discovery_candidates"][0]["record_id"])
        self.assertEqual(job["discovery_candidates"][0]["verification_status"], "retry_needed")

    def test_pool_bounds_report_omitted_rows_and_do_not_hide_a_check_limit_as_truncation(self):
        rows = [row(f"company-{n}.example") for n in range(MAX_ORGANIC_ROWS_PER_PAGE + 2)]
        pages = [page(str(n), *rows) for n in range(MAX_SERP_PAGES + 1)]
        chosen, records, coverage = select(pages, limit=1)
        self.assertEqual(len(chosen), 1)
        self.assertEqual(len(records), MAX_SERP_PAGES * MAX_ORGANIC_ROWS_PER_PAGE)
        self.assertEqual(coverage["omitted_rows"], 2 * MAX_SERP_PAGES + len(rows))
        self.assertTrue(coverage["pool_truncated"])
        self.assertFalse(select([page("one", *rows[:3])], limit=1)[2]["pool_truncated"])

    def test_zero_limit_and_invalid_navigation_rows_are_audited(self):
        chosen, records, _ = select([page("brand", {"url": ""}, row("google.com/search?q=x"),
            {"url": "javascript:alert(1)"}, row("valid.example", title=None, description=None))], limit=0)
        self.assertEqual(chosen, [])
        self.assertEqual([r["reason"] for r in records],
                         ["invalid_url", "search_destination", "invalid_url", "verification_candidate_limit"])

    def test_actual_job_known_first_trap_verifies_later_candidate(self):
        context = self.context(master_reference_id=self.master(), max_candidate_domains=1)
        pages = [page("manufacturer", row("known.example"), row("fresh.example"))]
        with patch.object(apify_runner, "run_actor", return_value=pages) as actor, \
             patch.object(research_runner, "process_supplier", side_effect=self.decision) as supplier:
            research_runner.run_research_job("test", context.request)
        result = job_store.get_job("test")
        self.assertEqual(actor.call_count, 1)
        self.assertEqual(supplier.call_args.args[1], "https://fresh.example")
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["skipped"][0]["reason"], "already_in_master")
        self.assertEqual(result["discovery_candidates"][1]["verification_status"], "review")

    def test_all_known_pool_never_verifies_a_website(self):
        context = self.context(master_reference_id=self.master())
        with patch.object(apify_runner, "run_actor", return_value=[page("brand", row("known.example"))]), \
             patch.object(research_runner, "process_supplier") as supplier:
            research_runner.run_research_job("test", context.request)
        supplier.assert_not_called()
        self.assertEqual(job_store.get_job("test")["processed"], 0)
        self.assertEqual(job_store.get_job("test")["discovery_candidates"][0]["reason"], "already_in_master")

    def test_seed_and_resolved_host_are_filtered_without_changing_seed_behavior(self):
        context = self.context(candidate_urls=["https://seed.example"], max_candidate_domains=2,
                               master_reference_id=self.master())
        def decide(product, url, context, **kwargs):
            return dict(self.decision(product, url, context), url="https://resolved.example" if "seed" in url else url)
        pages = [page("brand", row("seed.example"), row("resolved.example"), row("fresh.example"))]
        with patch.object(apify_runner, "run_actor", return_value=pages), \
             patch.object(research_runner, "process_supplier", side_effect=decide) as supplier:
            research_runner.run_research_job("test", context.request)
        self.assertEqual([c.args[1] for c in supplier.call_args_list], ["https://seed.example", "https://fresh.example"])
        self.assertEqual([r["reason"] for r in job_store.get_job("test")["discovery_candidates"][:2]],
                         ["already_seen", "already_seen"])

    def test_shared_cap_and_unique_record_ids_across_country_batches(self):
        request = ResearchRequest(product="Sauna", allowed_countries=["United States", "Canada"], max_candidate_domains=2)
        job_store.init_job("test", request.model_dump())
        def search(actor, run_input, context, **kwargs):
            rows = [row("a.example")] if run_input["countryCode"] == "us" else [row("a.example"), row("b.example"), row("c.example")]
            return [page("brand", *rows)]
        with patch.object(apify_runner, "run_actor", side_effect=search) as actor, \
             patch.object(research_runner, "process_supplier", side_effect=self.decision) as supplier:
            research_runner.run_research_job("test", request)
        job = job_store.get_job("test")
        self.assertEqual(actor.call_count, 2)
        self.assertEqual(supplier.call_count, 2)
        self.assertEqual(job["processed"], 2)
        self.assertEqual(len({r["record_id"] for r in job["discovery_candidates"]}), 4)
        self.assertEqual(job["discovery_candidates"][1]["reason"], "already_seen")

    def test_pending_checks_are_honest_after_target_stop_or_interruption(self):
        for name, decision, expected_status, stop_reason in [
            ("target", {"status": "qualified", "url": "https://a.example"}, "completed", "target_reached"),
            ("stop", JobStopped("user"), "stopped", "stopped"),
            ("limit", LimitReached("page_limit"), "limited", "page_limit"),
        ]:
            with self.subTest(name=name):
                context = self.context(name=name, target_suppliers=1, max_candidate_domains=3)
                with patch.object(apify_runner, "run_actor", return_value=[page("brand", row("a.example"), row("b.example"))]), \
                     patch.object(research_runner, "process_supplier", side_effect=[decision]):
                    research_runner.run_research_job(name, context.request)
                job = job_store.get_job(name)
                self.assertEqual(job["status"], expected_status)
                self.assertEqual(job["discovery_candidates"][1]["verification_status"], "not_checked")
                self.assertEqual(job["discovery_candidates"][1]["verification_stop_reason"], stop_reason)
                self.assertEqual(job["discovery_candidates"][0]["verification_status"],
                                 "qualified" if name == "target" else "interrupted")

    def test_api_exposes_selection_and_older_jobs_keep_empty_defaults(self):
        context = self.context(max_candidate_domains=1)
        with patch.object(apify_runner, "run_actor", return_value=[page("brand", row("a.example"), row("b.example"))]), \
             patch.object(research_runner, "process_supplier", side_effect=self.decision):
            research_runner.run_research_job("test", context.request)
        with TestClient(main.app, headers={"X-API-Key": "offline-test-api-key"}) as client:
            result = client.get("/research/result/test").json()
            self.assertEqual(len(result["discovery_candidates"]), 2)
            self.assertEqual(len(result["discovery_coverage"]), 1)
            self.assertEqual(result["review"][0]["discovery"]["record_id"], result["discovery_candidates"][0]["record_id"])
            self.assertNotIn("verification_status", result["review"][0]["discovery"])
            old = job_store.get_job("test")
            del old["discovery_candidates"], old["discovery_coverage"]
            with patch.object(main, "get_job", return_value=old):
                legacy = client.get("/research/result/test").json()
            self.assertEqual(legacy["discovery_candidates"], [])
            self.assertEqual(legacy["discovery_coverage"], [])


if __name__ == "__main__":
    unittest.main()
