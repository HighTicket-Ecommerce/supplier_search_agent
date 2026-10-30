import unittest
from backend.role_evidence import verify_supplier_role, recover_role_evidence


class RoleReviewTests(unittest.TestCase):
    def check(self, text, role="Manufacturer", product="Sauna heaters"):
        url = "https://example.com/about"
        quote = text.split("\n\n")[-1]
        pages = [{"url": url, "text": text}]
        evidence = [{"claim": "role", "source_url": url, "quote": quote}]
        return verify_supplier_role(role, "Example", evidence, pages, product), recover_role_evidence(role, "Example", pages, product)

    def test_supplier_manufacturer_is_not_our_manufacturing_role(self):
        for body in ("Example\n\nWe source our heaters from a leading manufacturer.",
                     "Example\n\nOur supplier is a trusted manufacturer of heaters."):
            result, recovered = self.check(body)
            self.assertEqual(result["status"], "not_established")
            self.assertEqual(recovered, [])

    def test_future_product_benefit_does_not_negate_present_manufacturing(self):
        self.assertEqual(self.check("We manufacture heaters that will last for decades.")[0]["status"], "supported")
        self.assertEqual(self.check("We will manufacture heaters next year.")[0]["status"], "not_established")
        self.assertEqual(self.check("We don't manufacture heaters that will last.")[0]["status"], "not_established")

    def test_requested_physical_products_support_arbitrary_categories(self):
        for category in ("bicycles", "kayaks", "ceramic planters"):
            for role, verb in (("Manufacturer", "manufacture"), ("Brand owner", "design")):
                with self.subTest(category=category, role=role):
                    result, recovered = self.check("We "+verb+" our own "+category+".", role, category)
                    self.assertEqual(result["status"], "supported")
                    self.assertTrue(recovered)
        for text in ("We design websites for bicycles.", "We manufacture trust for bicycles.", "We design services for kayaks."):
            self.assertEqual(self.check(text, "Brand owner", "bicycles and kayaks")[0]["status"], "not_established")
