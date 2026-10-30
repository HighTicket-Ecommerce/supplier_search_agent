import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import job_store, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class NavigationFollowupTests(unittest.TestCase):
    def test_exclusions_apply_to_their_own_noun_phrase_and_keep_system_route(self):
        briefs = ["Complete cold plunge systems; filters and accessories not included",
                  "Complete cold plunge systems; filters and accessories excluded",
                  "Complete cold plunge systems; filters optional",
                  "Complete cold plunge systems, don't want filters",
                  "Filters excluded. Complete cold plunge systems",
                  "Complete cold plunge systems (filters and accessories out of scope)",
                  "Filters optional; no-plumbing cold plunge systems"]
        for index, brief in enumerate(briefs):
            with self.subTest(brief=brief):
                collection = "/collections/cold-plunge-systems"
                accessory = "/products/cold-plunge-replacement-filter"
                self.assertLess(self.rank(collection, brief), self.rank(accessory, brief))
                with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(tmp)/"jobs.sqlite")}):
                    request = ResearchRequest(product=brief, max_pages_per_supplier=3)
                    job_store.init_job("route", request.model_dump()); context = ResearchContext("route", request)
                    calls = []
                    def fetch(url, ctx, **kwargs):
                        ctx.take_page(); calls.append(url)
                        return {"url": url, "text": "[About](/about) [Filter]("+accessory+") [Systems]("+collection+")" if len(calls) == 1 else "Captured company or product"}
                    with patch.object(web_fetcher, "fetch_page", side_effect=fetch):
                        web_fetcher.fetch_website_pages("https://example.com", context)
                    self.assertIn("https://example.com"+collection, calls)
                    self.assertNotIn("https://example.com"+accessory, calls)
                    self.assertEqual(context.pages, 3)

    def test_hyphenated_no_compounds_preserve_the_requested_category(self):
        for brief in ("No-plumbing cold plunge systems", "No-dig cold plunge systems"):
            with self.subTest(brief=brief):
                self.assertLess(self.rank("/products/no-plumbing-cold-plunge-tub-and-chiller-bundle", brief),
                                self.rank("/products/gift-card", brief))

    def rank(self, path, brief="Complete cold plunge systems", label=""):
        return web_fetcher._page_priority("https://example.com"+path, brief, label)

    def test_an_accessory_for_a_bundle_remains_an_accessory(self):
        for path in ("/products/replacement-filter-for-cold-plunge-tub-and-chiller-bundle",
                     "/products/steps-for-the-plunge-and-chiller-bundle"):
            with self.subTest(path=path):
                self.assertLess(self.rank("/collections/cold-plunge-systems"), self.rank(path))

    def test_complete_bundle_head_can_precede_included_extras(self):
        for slug, label in [
            ('cold-plunge-tub-chiller-bundle-filter-cover', 'Tub & Chiller Bundle + Filter & Cover'),
            ('chiller-and-tub-bundle-filter-cover', 'Chiller and Tub Bundle with Cover'),
            ('cold-plunge-tub-chiller-package-filter', 'Tub and Chiller Package + Filter'),
            ('cold-plunge-chiller-tub-combo-cover', 'Chiller and Tub Combo + Cover'),
            ('cold-plunge-complete-system-filter-and-cover', 'Complete Cold Plunge System + Filter and Cover')]:
            with self.subTest(slug=slug):
                self.assertLess(self.rank('/products/'+slug, label=label), self.rank('/collections/cold-plunge-systems'))
        self.assertGreater(self.rank('/products/all-in-one-plunge-filter'), self.rank('/collections/cold-plunge-systems'))

    def test_structured_exclusions_override_mentions_in_the_brief(self):
        product='Gas grills; replacement filters optional'
        wanted=web_fetcher._page_priority('https://example.com/collections/gas-grills',product,excluded_products=['replacement filters'])
        excluded=web_fetcher._page_priority('https://example.com/products/replacement-filters',product,excluded_products=['replacement filters'])
        self.assertLess(wanted,excluded)
        product='Gas grills and replacement filters'
        wanted=web_fetcher._page_priority('https://example.com/collections/gas-grills',product,excluded_products=['replacement filters'])
        excluded=web_fetcher._page_priority('https://example.com/products/replacement-filters',product,excluded_products=['replacement filters'])
        self.assertLess(wanted,excluded)
