import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"

from backend import job_store, supplier_validator, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class SupplierRoleTests(unittest.TestCase):
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

    def check_supplier(self, quotes, *, role="Manufacturer", body=None, company="Example",
                       allowed=None, is_product_company=True, owns_brand=True, extra_pages=None):
        self.jobs += 1
        url = "https://example.com/about"
        request = ResearchRequest(product="Sauna heaters", allowed_countries=["Canada"],
                                  **({"allowed_supplier_types": allowed} if allowed else {}))
        job_id = "roles-" + str(self.jobs)
        job_store.init_job(job_id, request.model_dump())
        context = ResearchContext(job_id, request)
        pages = [{"url": url, "text": (body if body is not None else "\n\n".join(quotes)) +
                  "\n\nWe supply electric sauna heaters.\n\nHeadquarters: Toronto, Ontario"}] + (extra_pages or [])
        evidence = [{"claim": "role", "source_url": url, "quote": q} for q in quotes]
        evidence += [{"claim": "product_match", "source_url": url, "quote": "We supply electric sauna heaters"},
                     {"claim": "country", "source_url": url, "quote": "Headquarters: Toronto, Ontario"}]
        analysis = {"is_product_company": is_product_company, "company_name": company, "supplier_type": role,
                    "owns_brand": owns_brand, "product_match": "supported", "product_kind": "primary",
                    "matched_product_urls": [url], "country": "Canada", "country_basis": "headquarters",
                    "identity_match": "not_requested", "email": None, "phone": None, "confidence": 0.99,
                    "notes": "High confidence must not replace role evidence.", "evidence": evidence}
        with patch.object(supplier_validator, "fetch_website_pages", return_value=pages), \
             patch.object(supplier_validator, "analyze_supplier_with_llm", return_value=analysis):
            row = supplier_validator.process_supplier(request.product, url, context)
        self.assertEqual(context.operations, [])
        return row

    def assert_role_review(self, row, model_role="Manufacturer"):
        self.assertEqual(row["status"], "review")
        self.assertEqual(row["reason"], "supplier_role_not_established")
        self.assertEqual(row["supplier_type"], "Unknown")
        self.assertEqual(row["model_supplier_type"], model_role)
        self.assertEqual(row["role_verification"]["status"], "not_established")

    def test_contact_catalogue_and_product_quotes_cannot_establish_roles(self):
        for role in ["Manufacturer", "Brand owner", "Distributor", "Retailer", "Marketplace", "Media / Blog"]:
            for quote in ["Talk to an expert: 844-728-6200", "Products: saunas, heaters and cold plunges", "info@example.com"]:
                with self.subTest(role=role, quote=quote):
                    self.assert_role_review(self.check_supplier([quote], role=role), role)

    def test_design_and_engineering_do_not_establish_manufacturing(self):
        for quote in ["Example designs saunas and cold plunge tubs", "We design our own sauna heaters",
                      "We engineer our own products", "We're the only Canadian brand engineering every part"]:
            with self.subTest(quote=quote):
                self.assert_role_review(self.check_supplier([quote]))

    def test_self_attributed_production_and_own_facility_support_manufacturing(self):
        for quote in ["We manufacture our own products", "Example manufactures sauna heaters",
                      "We design and manufacture sauna heaters",
                      "We proudly build all of our products in Canada",
                      "Every heater is manufactured in our Surrey facility",
                      "Example is a manufacturer of sauna heaters",
                      "Example is a proudly Canadian manufacturer",
                      "Example, as a manufacturer, can assist customers",
                      "Example Sauna Heater Manufacturer, Worldwide Product Supplier"]:
            with self.subTest(quote=quote):
                row = self.check_supplier([quote])
                self.assertEqual(row["status"], "qualified")
                self.assertEqual(row["supplier_type"], "Manufacturer")

    def test_brand_and_own_product_design_support_brand_owner(self):
        for quote in ["We're the only Canadian brand engineering every part",
                      "We own the Example brand", "Our own brand of sauna heaters",
                      "Example designs saunas and cold plunge tubs", "We design our own sauna heaters",
                      "Every product we make is engineered for performance", "We create cold plunges"]:
            with self.subTest(quote=quote):
                self.assertEqual(self.check_supplier([quote], role="Brand owner")["status"], "qualified")
        for quote in ["We sell products from leading brands", "Example - Official Store",
                      "Our products are made in Canada", "Engineered for recovery"]:
            with self.subTest(quote=quote):
                self.assert_role_review(self.check_supplier([quote], role="Brand owner"), "Brand owner")

    def test_clipped_negation_plans_and_foreign_manufacturers_need_review(self):
        for quote, body in [
            ("manufacture sauna heaters", "We do not manufacture sauna heaters."),
            ("manufacture sauna heaters", "We plan to manufacture sauna heaters."),
            ("manufacture sauna heaters", "Our suppliers manufacture sauna heaters."),
            ("manufactures sauna heaters", "Acme manufactures sauna heaters. We resell them."),
            ("We manufacture sauna heaters", "Customer review: We manufacture sauna heaters for our clients."),
            ("We manufacture sauna heaters", "Testimonials\n\nWe manufacture sauna heaters for our clients."),
            ("We manufacture sauna heaters", "Previously, We manufacture sauna heaters was our slogan."),
        ]:
            with self.subTest(body=body):
                self.assert_role_review(self.check_supplier([quote], body=body))

    def test_brand_design_for_other_companies_and_clipped_ownership_are_not_own_brand(self):
        for quote, body in [
            ("We design our own sauna heaters", "We design our own sauna heaters for other brands."),
            ("own the Example brand", "We do not own the Example brand."),
            ("our own brand", "We have never had our own brand."),
            ("We own the Example brand", "Our dealer says: We own the Example brand."),
        ]:
            with self.subTest(body=body):
                self.assert_role_review(self.check_supplier([quote], body=body, role="Brand owner"), "Brand owner")

    def test_role_nouns_in_other_relationships_cannot_change_the_predicate(self):
        for role, quote in [
            ("Manufacturer", "We are a retailer of products from a manufacturer"),
            ("Brand owner", "We are a distributor of a recovery brand"),
            ("Brand owner", "Our brand partners manufacture sauna heaters"),
            ("Brand owner", "Our brand directory lists sauna products"),
            ("Distributor", "We are an authorized distributor of Example heaters wholesale"),
        ]:
            with self.subTest(role=role, quote=quote):
                self.assert_role_review(self.check_supplier([quote], role=role), role)

    def test_building_partnerships_and_design_services_are_not_product_production(self):
        for role, quote in [
            ("Manufacturer", "We build relationships with heater manufacturers"),
            ("Manufacturer", "We build our brand with premium sauna products"),
            ("Brand owner", "We design websites for sauna product manufacturers"),
            ("Brand owner", "We craft experiences with sauna products"),
        ]:
            with self.subTest(role=role, quote=quote):
                self.assert_role_review(self.check_supplier([quote], role=role), role)

    def test_contracted_negation_and_role_service_modifiers_need_review(self):
        for role, quote, body in [
            ("Brand owner", "our own brand", "We don't have our own brand."),
            ("Brand owner", "our own brand", "We can't claim our own brand."),
            ("Manufacturer", "We are a manufacturer representative", None),
            ("Brand owner", "We are a brand consultancy for sauna products", None),
            ("Brand owner", "We are a brand partner for Acme heaters", None),
        ]:
            with self.subTest(role=role, quote=quote):
                self.assert_role_review(self.check_supplier([quote], body=body, role=role), role)

    def test_distributor_needs_third_party_goods_and_business_channel(self):
        for quote in ["We distribute third-party heaters wholesale to dealers",
                      "We are an authorized distributor of Acme heaters to retailers",
                      "We supply third-party brands to trade customers"]:
            with self.subTest(quote=quote):
                self.assertEqual(self.check_supplier([quote], role="Distributor", allowed=["Distributor"])["status"], "qualified")
        for quote in ["Wholesale", "Become a dealer", "We distribute our own products to retailers",
                      "We sell Acme heaters to consumers", "We manufacture heaters for our dealers",
                      "We sell third-party products", "We supply wholesale heaters"]:
            with self.subTest(quote=quote):
                self.assert_role_review(self.check_supplier([quote], role="Distributor", allowed=["Distributor"]), "Distributor")
        row = self.check_supplier(["We distribute third-party heaters wholesale to dealers"], role="Distributor")
        self.assertEqual((row["status"], row["reason"]), ("excluded", "supplier_role_outside_brief"))

    def test_explicit_retailer_is_excluded_only_when_role_supported(self):
        row = self.check_supplier(["We are a retailer of third-party sauna heaters"], role="Retailer")
        self.assertEqual((row["status"], row["reason"]), ("excluded", "supplier_role_outside_brief"))
        row = self.check_supplier(["We are a retailer of third-party sauna heaters"], role="Retailer", allowed=["Retailer"])
        self.assertEqual(row["status"], "qualified")
        self.assert_role_review(self.check_supplier(["We sell our own products to consumers"], role="Retailer"), "Retailer")

    def test_non_product_boolean_cannot_turn_irrelevant_role_quotes_into_exclusion(self):
        self.assert_role_review(self.check_supplier(["Contact our team"], is_product_company=False))
        row = self.check_supplier(["We manufacture sauna heaters"], is_product_company=False)
        self.assertEqual((row["status"], row["reason"]), ("review", "product_company_classification_conflict"))
        row = self.check_supplier(["We publish sauna product reviews"], role="Media / Blog", is_product_company=False)
        self.assertEqual((row["status"], row["reason"]), ("excluded", "not_product_company"))

    def test_role_support_cannot_cross_source_blocks_and_source_repair_is_audited(self):
        row = self.check_supplier(["Contact our team"], body="Contact our team.\n\nWe manufacture sauna heaters.")
        self.assertEqual(row["status"], "qualified")
        self.assertTrue(row["role_verification"]["source_repair_used"])
        self.assertEqual(row["role_verification"]["model_evidence_status"], "not_established")
        self.assertTrue(any(e.get("evidence_origin") == "captured_source_role_repair" for e in row["evidence"]))
        row = self.check_supplier(["We manufacture sauna heaters"], body="We manufacture\n\nsauna heaters")
        self.assert_role_review(row)
        row = self.check_supplier(["We distribute third-party heaters"], role="Distributor",
                                 body="We distribute third-party heaters.\n\nWholesale to dealers")
        self.assert_role_review(row, "Distributor")

    def test_source_repair_needs_the_exact_role_and_preserves_attribution_checks(self):
        for body in ["Contact us.\n\nExample designs sauna heaters.",
                     "Testimonials\n\nWe manufacture sauna heaters.",
                     "Our suppliers manufacture sauna heaters.", "We don't manufacture sauna heaters."]:
            with self.subTest(body=body):
                self.assert_role_review(self.check_supplier(["Contact us"], body=body))
        row = self.check_supplier(["Example - Official Store"], role="Brand owner",
                                 body="Example - Official Store\n\nExample crafts the best sauna heaters in Canada.")
        self.assertEqual(row["status"], "qualified")
        self.assertTrue(row["role_verification"]["source_repair_used"])
        self.assertTrue(all(len(e["quote"].split()) <= 12 for e in row["evidence"]))
        self.assertTrue(any(e["quote"].startswith("Example crafts") for e in row["evidence"] if e["claim"] == "role"))

    def test_support_retains_verified_source_and_drops_irrelevant_role_quotes(self):
        quote = "We manufacture sauna heaters"
        row = self.check_supplier([quote, "Talk to an expert"])
        self.assertEqual(row["status"], "qualified")
        self.assertEqual([e["quote"] for e in row["evidence"] if e["claim"] == "role"], [quote])
        support = row["role_verification"]["supporting_evidence"]
        self.assertEqual((support[0]["source_url"], support[0]["quote"]), ("https://example.com/about", quote))
        self.assertTrue(any(e["quote"] == "Talk to an expert" for e in row["evidence_issues"]))

    def test_roles_have_reserved_excerpt_space_beyond_product_content(self):
        text = "Sauna heaters. " * 1200 + "\n\nWe distribute third-party heaters wholesale to dealers."
        page = web_fetcher.prompt_pages([{"url": "https://example.com", "text": text}], "Sauna heaters")[0]
        self.assertTrue(any("We distribute third-party heaters wholesale to dealers" in e for e in page["excerpts"]))


if __name__ == "__main__":
    unittest.main()
