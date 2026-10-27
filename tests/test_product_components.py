import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"

from backend import job_store, supplier_validator
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class ProductComponentTests(unittest.TestCase):
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

    def check_supplier(self, quotes, *, text=None, product="Complete cold plunge systems",
                       title="Example Cold Plunge Tub", url="https://example.com/products/plunge", extra_pages=None):
        self.jobs += 1
        request = ResearchRequest(product=product, allowed_countries=["Canada"])
        job_id = "components-" + str(self.jobs)
        job_store.init_job(job_id, request.model_dump())
        context = ResearchContext(job_id, request)
        body = text if text is not None else "\n\n".join(quotes)
        pages = [{"url": url, "text": title + "\n\n" + body +
                  "\n\nWe manufacture our own products.\n\nHeadquarters: Toronto, Ontario"}] + (extra_pages or [])
        evidence = [{"claim": "product_match", "source_url": url, "quote": quote} for quote in quotes]
        for page in extra_pages or []:
            evidence.extend({"claim": "product_match", "source_url": page["url"], "quote": quote}
                            for quote in page.get("test_quotes", []))
        evidence += [{"claim": "role", "source_url": url, "quote": "We manufacture our own products"},
                     {"claim": "country", "source_url": url, "quote": "Headquarters: Toronto, Ontario"}]
        analysis = {"is_product_company": True, "company_name": "Example", "supplier_type": "Manufacturer", "owns_brand": True,
                    "product_match": "supported", "product_kind": "primary", "matched_product_urls": [p["url"] for p in pages],
                    "country": "Canada", "country_basis": "headquarters", "identity_match": "not_requested",
                    "email": None, "phone": None, "confidence": 0.99, "notes": "Model incorrectly assumes inclusion when unclear.",
                    "evidence": evidence}
        with patch.object(supplier_validator, "fetch_website_pages", return_value=pages), \
             patch.object(supplier_validator, "analyze_supplier_with_llm", return_value=analysis):
            row = supplier_validator.process_supplier(product, url, context)
        self.assertEqual(context.operations, [])
        return row

    def assert_component_review(self, row):
        self.assertEqual(row["status"], "review")
        self.assertEqual(row["reason"], "complete_system_components_not_established")
        self.assertEqual(row["product_match"], "not_established")
        self.assertEqual(row["model_product_match"], "supported")
        self.assertEqual(row["product_configuration"]["status"], "not_established")

    def test_compartment_compatibility_optional_and_separate_components_need_review(self):
        for quote in [
            "a concealed chiller compartment built into the cedar housing",
            "optional chiller systems for precise, year-round temperature control",
            "Compatible with Penguin Chiller and Coldture Pro systems",
            "Includes a compartment for an integrated chiller",
            "Includes housing for an integrated chiller",
            "Includes integrated chiller controls",
            "Built-in chiller port",
            "Designed for an integrated chiller",
            "Chiller not included",
            "This tub does not include a chiller",
            "Integrated chiller sold separately",
            "Integrated chiller available separately",
            "Integrated chiller excluded from the package",
            "Choose whether to add a chiller at checkout",
            "Chiller-ready tub",
        ]:
            with self.subTest(quote=quote):
                self.assert_component_review(self.check_supplier([quote]))

    def test_explicit_supplied_complete_configurations_qualify(self):
        for quote in [
            "Each pairing includes a tub and a chiller unit",
            "This package includes a stainless tub and an integrated chiller",
            "The system combines the tub and cooling unit",
            "Summit pairs a stainless tub with an integrated chiller",
            "Barrel tub + Chiller Pro bundle",
            "An integrated chiller with automatic ice-making takes the water",
            "Siberian Pro features an advanced 0.8 HP chiller system",
            "Yes, it comes with both a heater and chiller",
            "Designed for daily recovery with an included integrated chiller",
        ]:
            with self.subTest(quote=quote):
                row = self.check_supplier([quote])
                self.assertEqual(row["status"], "qualified")
                self.assertEqual(row["product_configuration"]["status"], "supported")
                self.assertEqual(row["product_configuration"]["required_components"], ["tub", "chiller"])

    def test_negation_hypotheticals_and_component_nouns_cannot_be_clipped_away(self):
        for quote, text in [
            ("includes a tub and chiller", "This package never includes a tub and chiller."),
            ("integrated chiller", "This tub has a compartment for an integrated chiller."),
            ("tub and chiller", "Shown with a tub and chiller, sold separately."),
            ("includes a chiller", "The filter kit includes a chiller hose."),
            ("integrated chiller", "We recommend a model with an integrated chiller."),
            ("include a tub and chiller", "A complete system should include a tub and chiller."),
            ("chiller included", "No chiller included."),
        ]:
            with self.subTest(quote=quote, text=text):
                self.assert_component_review(self.check_supplier([quote], text=text))

    def test_separate_pages_and_product_cards_cannot_combine_missing_components(self):
        row = self.check_supplier(["Includes a stainless tub"], extra_pages=[{
            "url": "https://example.com/products/chiller", "text": "Cold Plunge Chiller\n\nIncludes a water chiller",
            "test_quotes": ["Includes a water chiller"]}])
        self.assert_component_review(row)
        row = self.check_supplier(["Includes a stainless tub", "Includes a water chiller"],
            url="https://example.com/collections/plunges", title="Cold Plunge Range",
            text="Tub only\n\nIncludes a stainless tub\n\nStandalone water chiller\n\nIncludes a water chiller")
        self.assert_component_review(row)
        row = self.check_supplier(["Includes a chiller"],
            text="Recommended standalone chillers\n\nMini chiller module\n\nIncludes a chiller")
        self.assert_component_review(row)

    def test_explicit_complete_option_is_not_voided_by_a_separate_tub_only_option(self):
        quote = "Complete bundle includes a tub and chiller"
        row = self.check_supplier([quote], text="Basic tub: chiller sold separately.\n\n" + quote + ".")
        self.assertEqual(row["status"], "qualified")
        row = self.check_supplier(["Add a chiller"], text="Options: Tub only | Add a chiller. Chiller sold separately.")
        self.assert_component_review(row)

    def test_chiller_component_and_other_category_briefs_keep_existing_scope(self):
        for product in ["Cold plunge replacement filters", "Cold plunge chillers", "Cold plunge chiller kits", "Complete cold plunge filter systems",
                        "Sauna heaters", "Complete pool filtration systems"]:
            with self.subTest(product=product):
                row = self.check_supplier(["We supply this requested product"], product=product)
                self.assertEqual(row["status"], "qualified")

    def test_tub_and_chiller_request_requires_both_even_without_the_word_complete(self):
        self.assert_component_review(self.check_supplier(["Compatible with a chiller"], product="Cold plunge tub and chiller"))

    def test_trademarked_plunge_title_keeps_integrated_chiller_evidence(self):
        for title in ["Sun Home Cold Plunge™ Pro Apex", "Sun Home Cold Plunge® Pro Apex"]:
            with self.subTest(title=title):
                row = self.check_supplier(["An integrated chiller with automatic ice-making"], title=title)
                self.assertEqual(row["status"], "qualified")

    def test_unquoted_other_configuration_is_not_used_to_repair_a_tub_only_quote(self):
        row = self.check_supplier(["Basic tub includes a stainless tub"],
            text="Basic tub includes a stainless tub.\n\nRecommended Pro bundle includes a tub and chiller.")
        self.assert_component_review(row)

    def test_support_retains_the_specific_verified_source_and_quote(self):
        quote = "The package includes a tub and a chiller"
        row = self.check_supplier([quote])
        self.assertEqual(row["status"], "qualified")
        support = row["product_configuration"]["supporting_evidence"]
        self.assertTrue(support)
        self.assertEqual(support[0]["source_url"], "https://example.com/products/plunge")
        self.assertEqual(support[0]["quote"], quote)


if __name__ == "__main__":
    unittest.main()
