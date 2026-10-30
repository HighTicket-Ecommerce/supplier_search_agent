import unittest
from backend import location_evidence, supplier_validator


class LocationFollowupTests(unittest.TestCase):
    def test_shared_headquarters_grammar_accepts_one_place_and_keeps_other_owners_out(self):
        positives = ["Our headquarters and factory are located in Toronto, Ontario.",
                     "Our factory and headquarters are in Toronto, Ontario.",
                     "Our headquarters and factory are both in Toronto, Ontario.",
                     "Our corporate headquarters and factory are in Toronto, Ontario.",
                     "Our headquarters and factories are in Toronto, Ontario.",
                     "Our HQ & factory are in Toronto, Ontario."]
        negatives = ["Our factory is in Toronto, Ontario.",
                     "Our customer's headquarters and factory are in Toronto, Ontario."]
        for text in positives + negatives:
            with self.subTest(text=text):
                self.assertEqual(location_evidence.hq_quote_acceptable(text, text), text in positives)

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

    def test_shipping_actions_do_not_change_location_subject(self):
        for source in ["We're based in Toronto, Ontario and ship across Canada.",
                       "We're based in Toronto, Ontario, and we ship across Canada.",
                       "Proudly based in Toronto, Ontario, we offer free shipping across Canada."]:
            quote = source.split(' and ship')[0].split(', and we')[0].split(', we offer')[0]
            self.assertEqual(location_evidence.location_quote_kind(quote, source), 'company_base')
        source = 'Located in Toronto, Ontario, our factory produces heaters.'
        self.assertEqual(location_evidence.location_quote_kind('Located in Toronto, Ontario', source), 'factory')

    def test_shipping_paragraph_is_not_an_hq_label(self):
        quote = 'Our headquarters are in Toronto, Ontario.'
        sources = ['Shipping and returns available across North America.\n\n'+quote,
                   '<div>Free shipping across Canada</div><p>'+quote+'</p>',
                   '<p><a href="/returns">Returns and exchanges</a></p><p>'+quote+'</p>']
        from backend.web_fetcher import PageHTML
        for source in sources:
            if '<' in source:
                parser = PageHTML(); parser.feed(source); source = ''.join(parser.parts)
            self.assertEqual(location_evidence.location_quote_kind(quote, source), 'headquarters')
