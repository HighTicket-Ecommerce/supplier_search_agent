import unittest
from backend import location_evidence, supplier_validator


class LocationFollowupTests(unittest.TestCase):
    def test_shared_subjects_do_not_assign_the_factory_country_to_headquarters(self):
        for source in ["Our headquarters and factory are in Toronto and Shenzhen, China respectively.",
                       "Our headquarters and factory are in Toronto and Shenzhen, China."]:
            for quote in (source, "Our headquarters and factory are in Toronto"):
                with self.subTest(source=source, quote=quote):
                    self.assertFalse(location_evidence.hq_quote_acceptable(quote, source))

    def test_location_negation_handles_contractions_generally(self):
        for text in ["We haven't been based in Canada since 2019.",
                     "Our head office hasn't been in Toronto, Ontario since 2019.",
                     "We won't be based in Canada.", "We aren't based in Toronto, Ontario."]:
            for quote in (text, text.replace("'", "’")):
                with self.subTest(quote=quote):
                    self.assertFalse(location_evidence.hq_quote_acceptable(quote, quote))
                    self.assertFalse(location_evidence.has_company_location(quote))

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
