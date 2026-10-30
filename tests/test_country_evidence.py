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


class CountryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name)/"jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()
        self.jobs = 0

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def check_supplier(self, text, quotes=(), *, country="United States", basis="headquarters", allowed=None,
                       extra_pages=None):
        self.jobs += 1
        url = "https://example.com/contact"
        pages = [{"url": url, "text": "We manufacture sauna heaters.\n\nWe supply electric sauna heaters.\n\n"+text}]+(extra_pages or [])
        request = ResearchRequest(product="Sauna heaters", allowed_countries=allowed or ["United States", "Canada"])
        job_id = "countries-"+str(self.jobs)
        job_store.init_job(job_id, request.model_dump())
        context = ResearchContext(job_id, request)
        analysis = {"is_product_company": True, "company_name": "Example", "supplier_type": "Manufacturer", "owns_brand": True,
                    "product_match": "supported", "product_kind": "primary", "matched_product_urls": [url],
                    "country": country, "country_basis": basis, "identity_match": "not_requested", "email": None,
                    "phone": None, "confidence": 0.99, "notes": "Model country/basis can disagree with the source.",
                    "evidence": [{"claim": "role", "source_url": url, "quote": "We manufacture sauna heaters"},
                                 {"claim": "product_match", "source_url": url, "quote": "We supply electric sauna heaters"}]+
                                [{"claim": "country", "source_url": url, "quote": q} for q in quotes]}
        with patch.object(supplier_validator, "fetch_website_pages", return_value=pages), \
             patch.object(supplier_validator, "analyze_supplier_with_llm", return_value=analysis):
            row = supplier_validator.process_supplier(request.product, url, context)
        self.assertEqual(context.operations, [])
        return row

    def test_verified_redwood_office_resolves_unknown_model_country_without_claiming_hq(self):
        quote = "Office Address 20730 72nd Ave S, Kent, WA 98032"
        row = self.check_supplier("Office Address\n\n20730 72nd Ave S, Kent, WA 98032", [quote], country=None, basis="unknown")
        self.assertEqual(row["status"], "qualified")
        self.assertEqual((row["country"], row["country_basis"]), ("United States", "office"))
        self.assertIsNone(row["model_country"])
        self.assertEqual(row["model_country_basis"], "unknown")
        self.assertEqual(row["location_verification"]["location_type"], "office")

    def test_penguin_office_is_recovered_when_model_quotes_only_manufacturing_origin(self):
        text = "Manufactured in Tennessee.\n\nOffice Address\n\nKnoxville Office\n\n10315 Cogdill Rd\n\nKnoxville, TN 37932"
        row = self.check_supplier(text, ["Manufactured in Tennessee"], basis="manufacturing")
        self.assertEqual((row["status"], row["country_basis"]), ("qualified", "office"))
        self.assertTrue(row["location_verification"]["source_repair_used"])
        self.assertTrue(any(e.get("evidence_origin") == "captured_source_location_repair" for e in row["evidence"]))
        self.assertTrue(any(e.get("location_type") == "manufacturing_origin" for e in row["evidence_issues"]))

    def test_new_model_office_and_company_base_values_are_supported(self):
        for basis, text in [("office", "Our office is in Toronto, Ontario"),
                            ("company_base", "We are based in Surrey, BC")]:
            with self.subTest(basis=basis):
                row = self.check_supplier(text, [text], country="Canada", basis=basis)
                self.assertEqual((row["status"], row["country_basis"]), ("qualified", basis))

    def test_geo_country_comes_from_location_instead_of_wrong_model_country(self):
        quote = "Headquarters: Toronto, Ontario"
        row = self.check_supplier(quote, [quote], country="United States", allowed=["Canada"])
        self.assertEqual((row["status"], row["country"]), ("qualified", "Canada"))
        self.assertEqual(row["model_country"], "United States")

    def test_model_country_alone_cannot_establish_geography(self):
        for text in ["Our office is in Springfield", "Headquarters: Somewhere"]:
            with self.subTest(text=text):
                row = self.check_supplier(text, [text])
                self.assertEqual(row["status"], "review")
                self.assertIsNone(row["country"])

    def test_manufacturing_and_unlabelled_addresses_do_not_become_offices(self):
        for text in ["Made in Canada", "Manufactured in Toronto, Ontario", "Contact Us\n\nToronto, Ontario",
                     "Office Hours\n\n9-5\n\n20730 72nd Ave S, Kent, WA 98032",
                     "Our workshop is in Toronto, Ontario", "Return address: Kent, WA 98032",
                     "Our headquarters are not in Toronto, Ontario", "Our customer's office is in Toronto, Ontario"]:
            with self.subTest(text=text):
                row = self.check_supplier(text)
                self.assertEqual((row["status"], row["reason"]), ("review", "headquarters_not_established"))

    def test_explicit_foreign_hq_takes_precedence_over_allowed_country_office(self):
        for hq in ["Headquarters: Berlin, Germany", "We are headquartered in Berlin, Germany", "Headquarters\n\nGermany"]:
            with self.subTest(hq=hq):
                row = self.check_supplier("Office Address: Kent, WA 98032\n\n"+hq)
                self.assertEqual((row["status"], row["reason"]), ("excluded", "headquarters_outside_brief"))
                self.assertEqual((row["country"], row["country_basis"]), ("Germany", "headquarters"))

    def test_conflicting_locations_at_same_priority_need_review(self):
        for label in ["Headquarters", "Office Address"]:
            with self.subTest(label=label):
                row = self.check_supplier(label+": Toronto, Ontario\n\n"+label+": Kent, WA 98032")
                self.assertEqual((row["status"], row["reason"]), ("review", "company_location_conflict"))
                self.assertEqual(row["location_verification"]["status"], "ambiguous")

    def test_unknown_hq_country_cannot_be_replaced_by_known_office(self):
        row = self.check_supplier("Headquarters: Somewhere\n\nOffice Address: Kent, WA 98032")
        self.assertEqual(row["status"], "review")

    def test_office_heading_and_geography_do_not_cross_unrelated_address_cards(self):
        row = self.check_supplier("Office Address\n\n123 Unknown Road\n\nWorkshop\n\nKent, WA 98032")
        self.assertEqual(row["status"], "review")

    def test_geography_handles_california_city_name_and_canadian_postal_address(self):
        for text, country in [("Office Address: Ontario, CA 91761", "United States"),
                              ("Office Address: Cambridge, ON N1R 5S2", "Canada"),
                              ("Headquarters: San Diego, California", "United States"),
                              ("Headquarters: Vaughan, Ontario", "Canada")]:
            with self.subTest(text=text):
                row = self.check_supplier(text, [text], country=None, basis="unknown")
                self.assertEqual((row["status"], row["country"]), ("qualified", country))

    def test_conflicting_country_and_region_on_one_card_need_review(self):
        text = "Office Address: Toronto, Ontario, United States"
        self.assertEqual(self.check_supplier(text, [text])["status"], "review")

    def test_recovered_quotes_are_literal_short_and_keep_location_type(self):
        row = self.check_supplier("Office Address\n\n20730 72nd Ave S, Kent, WA 98032", country=None, basis="unknown")
        self.assertEqual(row["status"], "qualified")
        entries = [e for e in row["evidence"] if e["claim"] == "country"]
        self.assertTrue(entries)
        for e in entries:
            self.assertLessEqual(len(e["quote"].split()), 12)
            self.assertEqual(e["location_type"], "office")
            self.assertEqual(e["verified_country"], "United States")
            self.assertEqual(e["source_url"], "https://example.com/contact")

    def test_invented_country_quote_is_rejected_before_independent_source_recovery(self):
        text = "Our headquarters are in Toronto, Ontario"
        row = self.check_supplier(text, ["Headquarters in an invented location"], country=None, basis="market")
        self.assertEqual((row["status"], row["country"]), ("qualified", "Canada"))
        self.assertTrue(any(e["reason"] == "quote_not_in_captured_source" for e in row["evidence_issues"]))
        self.assertFalse(any(e["quote"] == "Headquarters in an invented location" for e in row["evidence"]))

    def test_non_current_and_third_party_locations_cannot_be_recovered(self):
        for text in ["Our headquarters isn't in Toronto, Ontario", "Our office isn't in Toronto, Ontario",
                     "Planned Office\n\nToronto, Ontario", "Our office will be in Toronto, Ontario",
                     "Former headquarters: Toronto, Ontario", "Our supplier's headquarters are in Toronto, Ontario",
                     "Our partner's office is in Toronto, Ontario"]:
            with self.subTest(text=text):
                row = self.check_supplier(text)
                self.assertEqual(row["status"], "review")

    def test_activity_at_hq_is_not_a_second_unresolved_location(self):
        text = "Canadian support team. nationwide technicians. full repair at HQ.\n\nHeadquarters: Vaughan, Ontario"
        row = self.check_supplier(text, ["Headquarters: Vaughan, Ontario"], country="Canada")
        self.assertEqual((row["status"], row["country_basis"]), ("qualified", "headquarters"))
        self.assertFalse(any(e["quote"] == "full repair at HQ." for e in row["location_verification"]["observations"]))

    def test_office_goods_and_employee_locations_do_not_establish_company_base(self):
        for text in ["We sell office furniture in Canada", "Our office manager is based in Toronto, Ontario",
                     "Our employees are based in Toronto, Ontario"]:
            with self.subTest(text=text):
                self.assertEqual(self.check_supplier(text)["status"], "review")


if __name__ == "__main__":
    unittest.main()
