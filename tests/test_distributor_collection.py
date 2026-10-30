"""Regressions for the two live distributor collection failures, without network."""
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"

from backend import job_store, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class DistributorCollectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name) / "jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()
        web_fetcher._CACHE.clear()

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def context(self, **kwargs):
        request = ResearchRequest(product="Fire Magic outdoor gas grills", allowed_supplier_types=["Distributor"], **kwargs)
        job_store.init_job("distributor", request.model_dump())
        return ResearchContext("distributor", request)

    def test_inline_exclusions_never_become_positive_navigation_terms(self):
        clean = "Fire Magic outdoor gas grills"
        for suffix in [" (excluding accessories and electric grills)", ", except for replacement parts", " but not charcoal grills"]:
            with self.subTest(suffix=suffix):
                self.assertEqual(web_fetcher._product_terms(clean + suffix), web_fetcher._product_terms(clean))

    def test_fire_does_not_match_fireplaces_and_gas_grills_beat_outdoor_products(self):
        product = "Fire Magic outdoor gas grills"
        self.assertIsNone(web_fetcher._page_priority("https://example.com/fireplaces", product, "Fireplaces"))
        grill = web_fetcher._page_priority("https://example.com/gas-%26-primo-grills", product, "Gas & Primo Grills")
        outdoor = web_fetcher._page_priority("https://example.com/outdoor-products", product, "Outdoor Products")
        self.assertLess(grill, outdoor)

    def test_decoded_facets_distinguish_gas_from_charcoal_and_accessories(self):
        product = "Fire Magic outdoor gas grills (excluding accessories and charcoal grills)"
        def rank(category):
            url = "https://example.com/brandsupplier/fire-magic?facet=" + quote('[["catname","catname","' + category + '"]]')
            return web_fetcher._page_priority(url, product, excluded_products=["accessories", "charcoal grills"])
        self.assertLess(rank("Gas Grills"), rank("Charcoal Grills"))
        self.assertLess(rank("Gas Grills"), rank("Grill Parts and Accessories"))

    def test_complete_grill_with_extras_keeps_priority_over_accessories(self):
        exclusions = ["accessories", "replacement parts"]
        product = "Fire Magic outdoor gas grills"
        complete = web_fetcher._page_priority("https://example.com/products/fire-magic-gas-grill-with-accessories", product,
            "Fire Magic gas grill with accessories", excluded_products=exclusions)
        parts = web_fetcher._page_priority("https://example.com/products/fire-magic-gas-grill-accessories", product,
            "Fire Magic gas grill accessories", excluded_products=exclusions)
        self.assertLess(complete, parts)

    def test_exclusions_override_an_explicit_accessory_brief(self):
        product = "Fire Magic replacement parts"
        parts = web_fetcher._page_priority("https://example.com/products/fire-magic-replacement-parts", product,
            "Fire Magic replacement parts", excluded_products=["replacement parts"])
        grills = web_fetcher._page_priority("https://example.com/products/fire-magic-gas-grills", product)
        self.assertGreater(parts, grills)
        # The same accessory request remains valid without an explicit exclusion.
        allowed_parts = web_fetcher._page_priority("https://example.com/products/fire-magic-replacement-parts", product,
            "Fire Magic replacement parts")
        self.assertLess(allowed_parts, grills)

    def test_category_exclusion_does_not_bury_a_dual_purpose_product(self):
        product = "Complete cold plunge systems"
        dual = web_fetcher._page_priority("https://example.com/products/cedar-hot-tub-cold-plunge", product,
                                         excluded_products=["hot tubs"])
        collection = web_fetcher._page_priority("https://example.com/collections/all", product,
                                               excluded_products=["hot tubs"])
        self.assertLess(dual, collection)

    def test_public_trade_entry_is_opt_in_and_account_actions_stay_excluded(self):
        login = "https://example.com/account/login?ReturnURL=%2Fitemdetail%2Fc430i"
        self.assertIsNone(web_fetcher._page_priority(login, "Gas grills"))
        self.assertEqual(web_fetcher._page_priority(login, "Gas grills", trade_policy=True), (3, 0))
        for path in ["/account/logout", "/account/orders", "/account/reset-password", "/checkout", "/account/login?token=private", "/account/login?delete=1"]:
            with self.subTest(path=path):
                self.assertIsNone(web_fetcher._page_priority("https://example.com" + path, "Gas grills", trade_policy=True))

    def test_distributor_route_collects_about_matching_category_and_one_trade_policy(self):
        # Link shapes/labels reproduce Rutherford's live brand catalogue. The
        # secondary bodies are controlled evidence, not claims of a fresh crawl.
        base = "https://www.rutherfordequipment.com"
        home = {"url": base + "/brandsupplier/fire-magic", "text": "Fire Magic brand catalogue", "links": [
            {"url": base + "/forms/contact-us", "label": "Contact Us"},
            {"url": base + "/static/about-us", "label": "About Us"},
            {"url": base + "/brandsupplier/fire-magic?facet=" + quote('[["catname","catname","Grill Parts and Accessories"]]'), "label": "Grill Parts and Accessories (631)"},
            {"url": base + "/brandsupplier/fire-magic?facet=" + quote('[["catname","catname","Gas Grills"]]'), "label": "Gas Grills (145)"},
            {"url": base + "/account/login?ReturnURL=%2Fitemdetail%2Fc430i", "label": "Please Log In"}]}
        about_url, gas_url, policy_url = (home["links"][i]["url"] for i in [1, 3, 4])
        bodies = {home["url"]: home, about_url: {"url": about_url, "text": "Our headquarters is in Covington, Georgia."},
                  gas_url: {"url": gas_url, "text": "Fire Magic gas grills"},
                  policy_url: {"url": policy_url, "text": "Rutherford Equipment is a wholesale distributor only."}}
        context = self.context(max_pages_per_supplier=4, max_pages=4, excluded_products=["accessories", "replacement parts"])
        def fetch(url, ctx, **kwargs):
            ctx.take_page()
            return bodies[url]
        with patch.object(web_fetcher, "fetch_page", side_effect=fetch) as call:
            pages = web_fetcher.fetch_website_pages(home["url"], context)
        self.assertEqual([c.args[0] for c in call.call_args_list], [home["url"], about_url, gas_url, policy_url])
        self.assertEqual([p.get("evidence_purpose") for p in pages[1:]], ["hq", "product", "trade"])
        self.assertEqual(context.pages, 4)

    def test_multiple_login_variants_consume_only_one_trade_attempt(self):
        home = {"url": "https://example.com/", "text": "Distributor products", "links": [
            {"url": "https://example.com/account/login?ReturnURL=" + str(i), "label": "Please Log In"} for i in range(10)]}
        context = self.context(max_pages_per_supplier=8, max_pages=8, allowed_countries=[])
        def fetch(url, ctx, **kwargs):
            ctx.take_page()
            return home if url == home["url"] else None
        with patch.object(web_fetcher, "fetch_page", side_effect=fetch) as call:
            pages = web_fetcher.fetch_website_pages(home["url"], context)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(context.pages, 2)
        self.assertEqual(pages, [home])

    def test_missing_policy_precedes_second_company_page_after_product(self):
        home = {"url": "https://example.com/brands/grills", "text": "Brand catalogue", "links": [
            {"url": "https://example.com/about", "label": "About Us"},
            {"url": "https://example.com/contact", "label": "Contact Us"},
            {"url": "https://example.com/products/gas-grill", "label": "Gas Grill"},
            {"url": "https://example.com/account/login", "label": "Sign in"}]}
        bodies = {home["url"]: home, **{link["url"]: {"url": link["url"], "text": "Company/product details; location unverified"}
                                        for link in home["links"]}}
        context = self.context(max_pages_per_supplier=4, max_pages=4)
        def fetch(url, ctx, **kwargs):
            ctx.take_page()
            return bodies[url]
        with patch.object(web_fetcher, "fetch_page", side_effect=fetch) as call:
            web_fetcher.fetch_website_pages(home["url"], context)
        self.assertEqual([c.args[0] for c in call.call_args_list],
                         [home["url"], home["links"][0]["url"], home["links"][2]["url"], home["links"][3]["url"]])
        self.assertEqual(context.pages, 4)

    def test_wholesale_navigation_label_does_not_replace_a_policy_page(self):
        home = {"url": "https://example.com/", "text": "Wholesale\nProducts\nContact", "links": [
            {"url": "https://example.com/account/login", "label": "Sign in"}]}
        context = self.context(max_pages_per_supplier=2, max_pages=2, allowed_countries=[])
        with patch.object(web_fetcher, "fetch_page", side_effect=[home, None]) as call:
            web_fetcher.fetch_website_pages(home["url"], context)
        self.assertEqual(call.call_args_list[1].args[0], home["links"][0]["url"])

    def test_buried_wholesale_policy_reaches_model_without_becoming_qualification(self):
        content = "Navigation and catalogue filler. " * 700 + "\n\nWholesale Trade only. No retail.\n\n"
        page = {"url": "https://example.com/", "text": content}
        prompt = web_fetcher.prompt_pages([page], "Fire Magic gas grills")[0]
        self.assertTrue(any("Wholesale Trade only. No retail." in excerpt for excerpt in prompt["excerpts"]))
        self.assertNotIn("supplier_type", prompt)

    def test_cache_does_not_reuse_links_from_different_brief_exclusions(self):
        context = self.context()
        html = '<main>' + ('Fire Magic grills ' * 30) + '</main><a href="/account/login">Log in</a>'
        with patch.object(web_fetcher, "run_actor", return_value=[{"html": html}]) as call:
            first = web_fetcher.fetch_page("https://example.com/", context)
            context.request.excluded_products = ["replacement parts"]
            second = web_fetcher.fetch_page("https://example.com/", context)
        self.assertEqual(call.call_count, 2)
        self.assertFalse(first.get("cache_hit", False))
        self.assertFalse(second.get("cache_hit", False))


if __name__ == "__main__":
    unittest.main()
