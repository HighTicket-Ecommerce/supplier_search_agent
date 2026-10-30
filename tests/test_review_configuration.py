import unittest
from backend.product_evidence import verify_product_configuration


class ConfigurationReviewTests(unittest.TestCase):
    def check(self, text, quote):
        url = "https://example.com/products/plunge"
        return verify_product_configuration("Complete cold plunge systems",
            [{"claim": "product_match", "source_url": url, "quote": quote}], [{"url": url, "text": text}], [url])["status"]

    def test_catalogue_inventory_is_not_one_configuration(self):
        quote = "Our products include tubs and chillers."
        self.assertEqual(self.check(quote, quote), "not_established")
        quote = "Our bundle includes a tub and chiller."
        self.assertEqual(self.check(quote, quote), "supported")

    def test_negative_or_optional_heading_cannot_authorize_inclusion(self):
        for heading in ("Not included", "Optional accessories", "Sold separately"):
            self.assertEqual(self.check(heading+"\n\nTub and chiller", "Tub and chiller"), "not_established")
        self.assertEqual(self.check("Included\n\nTub and chiller", "Tub and chiller"), "supported")
