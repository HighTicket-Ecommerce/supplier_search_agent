import unittest
from backend.location_evidence import hq_quote_acceptable
from backend.web_fetcher import PageHTML


class LocationReviewTests(unittest.TestCase):
    def test_table_and_definition_labels_remain_separate_words(self):
        for html in ("<table><tr><th>Headquarters</th><td>Toronto, Ontario</td></tr></table>",
                     "<dl><dt>Headquarters</dt><dd>Toronto, Ontario</dd></dl>"):
            parser = PageHTML(); parser.feed(html)
            self.assertEqual(" ".join("".join(parser.parts).split()), "Headquarters Toronto, Ontario")

    def test_contracted_negation_is_not_company_location(self):
        for source in ("We aren't based in Toronto, Ontario.", "Our headquarters isn't in Toronto, Ontario."):
            self.assertFalse(hq_quote_acceptable("Toronto, Ontario", source, "https://example.com/about"))

    def test_explicit_shared_hq_is_location_but_factory_alone_is_not(self):
        source = "Our headquarters and factory are in Toronto, Ontario."
        self.assertTrue(hq_quote_acceptable(source, source))
        self.assertFalse(hq_quote_acceptable("Our factory is in Toronto, Ontario."))

    def test_self_location_supports_spelled_out_region(self):
        source = "We're a Toronto, Ontario manufacturer."
        self.assertTrue(hq_quote_acceptable(source, source))
        self.assertFalse(hq_quote_acceptable("We sell to Toronto, Ontario manufacturers."))
