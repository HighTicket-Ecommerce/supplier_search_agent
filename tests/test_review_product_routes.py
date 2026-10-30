import unittest
from backend.web_fetcher import _page_priority


class ProductRouteReviewTests(unittest.TestCase):
    def test_negated_accessories_do_not_disable_the_accessory_penalty(self):
        brief = "Complete cold plunge systems, no filters or accessories"
        rank = lambda slug: _page_priority("https://example.com/products/"+slug, brief)
        self.assertLess(rank("cold-plunge-tub-and-chiller-bundle"), rank("all-in-one-cold-plunge-filter"))
        self.assertLess(rank("cold-plunge-system"), rank("cold-plunge-filter"))

    def test_explicit_pair_bundle_can_name_extras_without_with(self):
        brief = "Complete cold plunge systems"
        rank = lambda slug: _page_priority("https://example.com/products/"+slug, brief)
        self.assertLess(rank("cold-plunge-tub-and-chiller-bundle-filter-and-cover"), rank("cold-plunge-filter"))
        self.assertLess(rank("cold-plunge-system"), rank("all-in-one-cold-plunge-filter"))
