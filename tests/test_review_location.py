import unittest
from backend.location_evidence import hq_quote_acceptable, location_quote_kind
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

    def test_clipped_location_checks_the_factory_subject_after_it(self):
        source = "Located in Toronto, Ontario, our factory produces sauna heaters."
        self.assertEqual(location_quote_kind("Located in Toronto, Ontario", source), "factory")

    def test_unrelated_shipping_sentence_does_not_void_current_hq(self):
        source = "Shipping is available across Canada. Our headquarters are in Toronto, Ontario."
        self.assertEqual(location_quote_kind("Our headquarters are in Toronto, Ontario", source), "headquarters")
        self.assertEqual(location_quote_kind("Toronto, Ontario", "Headquarters\n\nToronto, Ontario"), "headquarters")
