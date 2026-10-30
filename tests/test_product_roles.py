import copy
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"

from backend import job_store, product_role_evidence, supplier_validator
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class RequestedProductRoleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name) / "jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()
        self.jobs = 0

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def run_case(self, role_quote, *, body=None, role="Manufacturer", product="Complete cold plunge systems", extra_pages=None):
        url = "https://example.com/products/cold-plunge"
        inclusion = "This cold plunge includes a tub and chiller"
        pages = [{"url": url, "text": "Example Cold Plunge\n\n" + (body or role_quote) + "\n\n" + inclusion}] + (extra_pages or [])
        analysis = {"is_product_company": True, "company_name": "Example", "supplier_type": role, "owns_brand": None,
                    "product_match": "supported", "product_kind": "primary", "matched_product_urls": [url],
                    "country": None, "country_basis": "unknown", "identity_match": "not_requested", "email": None,
                    "phone": None, "confidence": .99, "notes": "Company-role and product-role evidence are distinct.",
                    "evidence": [{"claim": "role", "source_url": url, "quote": role_quote},
                                 {"claim": "product_match", "source_url": url, "quote": inclusion}]}
        return self.process(product, url, pages, analysis)

    def process(self, product, url, pages, analysis):
        self.jobs += 1
        request = ResearchRequest(product=product, allowed_countries=[])
        job_id = "product-role-" + str(self.jobs)
        job_store.init_job(job_id, request.model_dump())
        context = ResearchContext(job_id, request)
        with patch.object(supplier_validator, "fetch_website_pages", return_value=pages), \
             patch.object(supplier_validator, "analyze_supplier_with_llm", return_value=copy.deepcopy(analysis)):
            result = supplier_validator.process_supplier(product, url, context)
        self.assertEqual(context.operations, [])
        return result

    def assert_scope_review(self, result):
        self.assertEqual((result["status"], result["reason"]), ("review", "requested_product_role_not_established"))
        self.assertEqual(result["role_verification"]["status"], "supported")
        self.assertEqual(result["product_match"], "supported")
        self.assertEqual(result["requested_product_supplier_type"], "Unknown")

    def test_saved_penguin_component_role_does_not_qualify_the_complete_system(self):
        fixture = json.loads(Path(__file__).with_name("fixtures").joinpath("penguin_product_role.json").read_text())
        result = self.process(fixture["product"], fixture["pages"][0]["url"], fixture["pages"], fixture["analysis"])
        self.assert_scope_review(result)
        self.assertEqual(result["supplier_type"], "Manufacturer")
        self.assertEqual(result["product_configuration"]["status"], "supported")
        self.assertFalse(result["product_role_verification"]["source_repair_used"])

    def test_explicit_primary_production_retains_qualification(self):
        for quote in ["Example manufactures complete cold plunge systems", "We build ice baths",
                      "We design and manufacture cold plunges", "We are a manufacturer of cold plunges",
                      "Every cold plunge is manufactured in our facility"]:
            with self.subTest(quote=quote):
                result = self.run_case(quote)
                self.assertEqual(result["status"], "qualified")
                self.assertEqual(result["requested_product_supplier_type"], "Manufacturer")

    def test_component_making_for_a_system_does_not_establish_system_production(self):
        for quote in ["We manufacture chillers for cold plunge systems", "We manufacture cold plunge chillers",
                      "We manufacture ice bath filters", "We build chillers used in cold plunges",
                      "We manufacture cold plunge integrated chillers", "We manufacture cold plunge filtration systems",
                      "We manufacture cold plunge equipment", "We manufacture ice bath housings"]:
            with self.subTest(quote=quote):
                self.assert_scope_review(self.run_case(quote))

    def test_selling_the_complete_item_does_not_extend_a_component_role(self):
        for quote in ["We manufacture chillers and sell complete cold plunges",
                      "We manufacture chillers and Acme manufactures complete cold plunges",
                      "We are a manufacturer of chillers and Acme is a manufacturer of cold plunges",
                      "Our chillers are built in our facility and Acme cold plunges are manufactured overseas"]:
            with self.subTest(quote=quote):
                self.assert_scope_review(self.run_case("We manufacture chillers", body="We manufacture chillers.\n\n" + quote))

    def test_two_self_attributed_production_actions_can_support_the_primary_item(self):
        quote = "We manufacture chillers and we manufacture cold plunges"
        self.assertEqual(self.run_case(quote)["status"], "qualified")

    def test_brand_creation_is_scoped_and_does_not_become_manufacturing(self):
        for quote in ["We design cold plunge tubs", "Example makes premium cold plunges",
                      "We create ice baths", "Our own brand of cold plunges"]:
            with self.subTest(quote=quote):
                result = self.run_case(quote, role="Brand owner")
                self.assertEqual(result["status"], "qualified")
                self.assertEqual(result["requested_product_supplier_type"], "Brand owner")
        self.assertEqual(self.run_case("We design cold plunges")["reason"], "supplier_role_not_established")

    def test_designing_components_does_not_establish_the_complete_product_brand(self):
        for quote in ["We design cold plunge chillers", "We create ice bath filters", "We design saunas", "We design cold plunge products"]:
            with self.subTest(quote=quote):
                self.assert_scope_review(self.run_case(quote, role="Brand owner"))

    def test_generic_role_and_nearby_product_cards_cannot_fill_the_relationship(self):
        body = "We manufacture chillers.\n\nComplete Cold Plunges\n\nBeyond Cold Summit\n\nBuilt in Tennessee"
        self.assert_scope_review(self.run_case("We manufacture chillers", body=body))

    def test_scoped_source_repair_uses_literal_quotes_without_provider_calls(self):
        result = self.run_case("We manufacture chillers", body="We manufacture chillers.\n\nWe manufacture complete cold plunges.")
        self.assertEqual(result["status"], "qualified")
        self.assertTrue(result["product_role_verification"]["source_repair_used"])
        recovered = [e for e in result["evidence"] if e.get("evidence_origin") == "captured_source_product_role_repair"]
        self.assertEqual(len(recovered), 1)
        self.assertLessEqual(len(recovered[0]["quote"].split()), 12)

    def test_source_repair_does_not_use_negated_historical_or_other_speaker_statements(self):
        for statement in ["We do not manufacture cold plunges.", "We used to manufacture cold plunges.",
                          "Testimonials\n\nWe manufacture cold plunges.", "Our suppliers manufacture cold plunges."]:
            with self.subTest(statement=statement):
                self.assert_scope_review(self.run_case("We manufacture chillers", body="We manufacture chillers.\n\n" + statement))

    def test_role_repair_cannot_silently_switch_the_company_role(self):
        result = self.run_case("We own the Example brand", role="Brand owner",
                               body="We own the Example brand.\n\nWe manufacture cold plunges.")
        self.assert_scope_review(result)
        self.assertEqual(result["supplier_type"], "Brand owner")

    def test_owning_one_brand_does_not_make_contract_design_an_own_product(self):
        result = self.run_case("We own the Example brand", role="Brand owner",
                               body="We own the Example brand and we design cold plunges for other brands.")
        self.assert_scope_review(result)

    def test_a_role_quote_cannot_cross_blocks_into_product_scope(self):
        result = self.run_case("We manufacture chillers", body="We manufacture chillers.\n\nWe manufacture\n\ncold plunges")
        self.assert_scope_review(result)

    def test_other_briefs_and_distributor_scope_are_explicitly_not_checked(self):
        for product, role in [("Sauna heaters", "Manufacturer"), ("Cold plunge chillers", "Manufacturer"),
                              ("Cold plunge filters", "Brand owner"), ("Complete cold plunge systems", "Distributor")]:
            with self.subTest(product=product, role=role):
                result = product_role_evidence.verify_requested_product_role(product, role, "Example", [], [])
                self.assertEqual(result["status"], "not_required")

    def test_source_repair_is_bounded_even_with_a_long_component_catalogue(self):
        url = "https://example.com/about"
        text = "We manufacture cold plunge filters " * 400
        entry = {"claim": "role", "source_url": url, "quote": "We manufacture cold plunge filters"}
        with patch.object(product_role_evidence, "verify_supplier_role", wraps=product_role_evidence.verify_supplier_role) as verify:
            result = product_role_evidence.verify_requested_product_role("Complete cold plunge systems", "Manufacturer", "Example", [entry], [{"url": url, "text": text}])
        self.assertEqual(result["status"], "not_established")
        self.assertLessEqual(verify.call_count, 1 + product_role_evidence.MAX_RECOVERY_WINDOWS_PER_PAGE)


if __name__ == "__main__":
    unittest.main()
