import unittest
from backend.product_role_evidence import verify_requested_product_role


class ProductRoleReviewTests(unittest.TestCase):
    def check(self, clause, company="Example"):
        url = "https://example.com/about"
        return verify_requested_product_role("Complete cold plunge systems", "Manufacturer", company,
            [{"claim": "role", "source_url": url, "quote": " ".join(clause.split()[:12])}], [{"url": url, "text": clause}])["status"]

    def test_adjectives_and_purpose_do_not_promote_components_to_systems(self):
        for clause in ("We manufacture cold plunge stainless steel chillers",
                       "We manufacture cold plunge high performance filtration systems",
                       "We manufacture components to build cold plunge systems",
                       "We manufacture components of complete cold plunge systems"):
            with self.subTest(clause=clause):
                self.assertEqual(self.check(clause), "not_established")
        for clause in ("We manufacture cold plunge systems with stainless steel chillers",
                       "We manufacture cold plunge stainless steel tubs",
                       "We manufacture cold plunges and chillers"):
            with self.subTest(clause=clause):
                self.assertEqual(self.check(clause), "supported")

    def test_self_attributed_appositive_manufacturer_can_bind_the_category(self):
        self.assertEqual(self.check("Example, a manufacturer of cold plunges"), "supported")
        self.assertEqual(self.check("Example\n\nLeading manufacturer of cold plunges"), "supported")
        self.assertEqual(self.check("We source tubs from Acme, a manufacturer of cold plunges"), "not_established")
