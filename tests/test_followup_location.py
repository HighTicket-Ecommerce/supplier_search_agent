import unittest
from backend import location_evidence, supplier_validator


class LocationFollowupTests(unittest.TestCase):
    def test_self_descriptions_require_a_location_not_an_adjective_or_customer(self):
        negatives = ["We're a small, independent company.", "We are a small, local business.",
                     "We're a supplier to a Toronto, Ontario company."]
        positives = ["We're a Vancouver, British Columbia manufacturer.", "We're a Toronto, ON manufacturer.",
                     "We're a Montréal, Québec manufacturer."]
        url = "https://example.com/about"
        for text in negatives + positives:
            with self.subTest(text=text):
                expected = text in positives
                self.assertEqual(location_evidence.hq_quote_acceptable(text, text, url), expected)
                self.assertEqual(location_evidence.has_company_location(text, url), expected)
                evidence, _ = supplier_validator.validate_evidence(
                    [{"claim": "country", "source_url": url, "quote": text}], [{"url": url, "text": text}])
                self.assertEqual(bool(evidence), expected)
