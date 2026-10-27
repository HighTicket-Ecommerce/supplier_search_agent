import json
import importlib.util
import io
import os
from contextlib import redirect_stderr
from pathlib import Path
import socket
import tempfile
import unittest
import sys
from unittest.mock import patch

os.environ["OPENAI_API_KEY"] = "offline-test-key"
os.environ["APIFY_TOKEN"] = "offline-test-token"
os.environ["OPENAI_MODEL"] = "gpt-5.2-2025-12-11"

from backend import job_store, supplier_validator, web_fetcher
from backend.location_evidence import hq_quote_acceptable
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class EvidenceCollectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(Path(self.directory.name)/"jobs.sqlite")})
        self.env.start()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network access"))
        self.network.start()
        web_fetcher._CACHE.clear()

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        self.directory.cleanup()

    def context(self, name="test", **kwargs):
        request = ResearchRequest(product="Complete cold plunge systems", **kwargs)
        job_store.init_job(name, request.model_dump())
        return ResearchContext(name, request)

    def test_actor_keeps_html_navigation_and_footer_links_separate_from_body(self):
        context = self.context()
        item = {"markdown": "A complete cold plunge with integrated chiller.", "html": '''
            <nav><a href="/pages/company-profile" aria-label="About us"></a></nav>
            <main><h1>Cold plunges</h1><a href="/products/plunge">Integrated system</a></main>
            <footer><a href="/pages/contact-us">Contact</a><a href="https://other.example/about">External</a>
            <a href="/privacy">Privacy</a><a href="javascript:alert(1)">Bad</a></footer>
            <script><a href="/pages/fake-about">Invented</a></script>'''}
        def actor(*args, **kwargs):
            context.reserve("apify", .5, run_id="html-run", dataset_id="html-dataset")
            return [item]
        with patch.object(web_fetcher, "run_actor", side_effect=actor) as run:
            page = web_fetcher.fetch_page("https://example.com/", context)
        self.assertEqual(run.call_args.args[1]["outputFormats"], ["markdown", "html"])
        selector = run.call_args.args[1]["removeElementsCssSelector"]
        self.assertNotIn("nav", selector); self.assertNotIn("footer", selector)
        self.assertEqual({link["url"] for link in page["links"]}, {
            "https://example.com/pages/company-profile", "https://example.com/products/plunge", "https://example.com/pages/contact-us"})
        self.assertEqual(page["actor_run_id"], "html-run")
        self.assertTrue(page["html_captured"])
        self.assertEqual(context.pages, 1)

    def test_footer_about_link_is_followed_when_clean_text_has_no_links(self):
        context = self.context(max_pages_per_supplier=2)
        first = {"url":"https://example.com/", "text":"Cold plunge systems", "links":[
            {"url":"https://example.com/pages/about-us", "label":"About", "discovered_from":"https://example.com/"}]}
        about = {"url":"https://example.com/pages/about-us", "text":"Our headquarters are in Toronto, Ontario."}
        with patch.object(web_fetcher, "fetch_page", side_effect=[first, about]) as fetch:
            pages = web_fetcher.fetch_website_pages("https://example.com/", context)
        self.assertEqual(fetch.call_args_list[1].args[0], about["url"])
        self.assertEqual(pages[1]["discovered_from"], first["url"])
        self.assertEqual(pages[1]["evidence_purpose"], "hq")

    def test_homepage_location_routes_remaining_page_to_product(self):
        context = self.context(max_pages_per_supplier=2)
        first = {"url":"https://example.com/", "text": "Our headquarters are in Toronto, Ontario. "
                 "[About](/about) [Contact](/contact) [System](/products/plunge)"}
        with patch.object(web_fetcher, "fetch_page", side_effect=[first, {"url":"https://example.com/products/plunge", "text":"Tub with included chiller"}]) as fetch:
            pages = web_fetcher.fetch_website_pages("https://example.com/", context)
        self.assertEqual(fetch.call_args_list[1].args[0], "https://example.com/products/plunge")
        self.assertEqual(pages[1]["evidence_purpose"], "product")

    def test_footer_city_prioritizes_contact_to_get_company_address_context(self):
        context = self.context(max_pages_per_supplier=3)
        first = {"url":"https://example.com/", "text":"Handbuilt cold plunge tubs. Redmond, Oregon. [About](/pages/about) [Contact](/pages/contact) [System](/products/plunge)"}
        contact = {"url":"https://example.com/pages/contact", "text":"1104 SE Lake Rd Ste. 101, Redmond, OR 97756"}
        product = {"url":"https://example.com/products/plunge", "text":"An integrated chiller is included in the tub."}
        with patch.object(web_fetcher,"fetch_page",side_effect=[first,contact,product]) as fetch:
            pages = web_fetcher.fetch_website_pages(first["url"],context)
        self.assertEqual(fetch.call_args_list[1].args[0],contact["url"])
        self.assertEqual(fetch.call_args_list[2].args[0],product["url"])
        self.assertEqual(len(pages),3)
        self.assertFalse(hq_quote_acceptable("Redmond, Oregon",first["text"],first["url"]))

    def test_about_then_product_from_secondary_page_stays_inside_caps(self):
        context = self.context(max_pages_per_supplier=3, max_pages=3)
        first = {"url":"https://example.com/", "text":"[About](/about) [Contact](/contact)"}
        about = {"url":"https://example.com/about", "text":"Our headquarters are in Toronto, Ontario. [System](/products/plunge)"}
        product = {"url":"https://example.com/products/plunge", "text":"An integrated chiller is included in the tub. [Other](/products/second)"}
        def fetch(url, ctx, **kwargs):
            ctx.take_page()
            return {first["url"]:first, about["url"]:about, product["url"]:product}[url]
        with patch.object(web_fetcher, "fetch_page", side_effect=fetch) as call:
            pages = web_fetcher.fetch_website_pages(first["url"], context)
        self.assertEqual([p["url"] for p in pages], [first["url"], about["url"], product["url"]])
        self.assertEqual(call.call_count, 3)
        self.assertEqual(context.pages, 3)
        self.assertEqual(pages[-1]["discovered_from"], about["url"])

    def test_failed_company_page_does_not_consume_all_followups(self):
        context = self.context(max_pages_per_supplier=3)
        first = {"url":"https://example.com/", "text":"[About](/about) [Contact](/contact) [System](/products/plunge)"}
        with patch.object(web_fetcher, "fetch_page", side_effect=[first, None, {"url":"https://example.com/products/plunge", "text":"A tub and included chiller"}]) as call:
            pages = web_fetcher.fetch_website_pages(first["url"], context)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(call.call_args_list[2].args[0], "https://example.com/products/plunge")
        self.assertEqual(len(pages), 2)

    def test_html_only_page_can_supply_readable_evidence(self):
        context = self.context()
        html = "<main><h1>Our company</h1><p>Our headquarters are in Toronto, Ontario.</p></main>"
        with patch.object(web_fetcher, "run_actor", return_value=[{"html":html}]):
            page = web_fetcher.fetch_page("https://example.com/about", context)
        self.assertIn("Our headquarters are in Toronto, Ontario.", page["text"])
        self.assertNotIn("<main>", page["text"])

    def test_empty_boolean_image_alt_does_not_break_real_world_link_parsing(self):
        html = '<footer><a href="/pages/about-us"><img alt src="/logo.png">About</a><a href="/pages/contact" title>Contact</a></footer>'
        links, parser = web_fetcher.evidence_links(html, "", "https://example.com/", "Cold plunge systems")
        self.assertEqual({row["url"] for row in links}, {"https://example.com/pages/about-us", "https://example.com/pages/contact"})

    def test_product_routing_avoids_media_protocols_and_solo_chillers_for_system_brief(self):
        product = "Complete cold plunge systems"
        self.assertIsNone(web_fetcher._page_priority("https://example.com/cdn/shop/files/cold-plunge.webp", product))
        self.assertIsNone(web_fetcher._page_priority("https://example.com/pages/the-cold-plunge-protocol", product))
        system = web_fetcher._page_priority("https://example.com/products/cold-plunge-pro", product)
        collection = web_fetcher._page_priority("https://example.com/collections/cold-plunges", product)
        chiller = web_fetcher._page_priority("https://example.com/products/best-cold-plunge-chiller", product)
        self.assertLess(system, collection)
        self.assertLess(collection, chiller)
        bundle = web_fetcher._page_priority("https://example.com/products/barrel-cold-plunge-tub-bundle", product)
        mat = web_fetcher._page_priority("https://example.com/products/dry-mat-cold-plunge", product)
        self.assertLess(bundle, mat)
        self.assertIsNotNone(web_fetcher._page_priority("https://example.com/products/best-cold-plunge-chiller", "Cold plunge chillers"))

    def test_penguin_navigation_chooses_collection_instead_of_all_in_one_filter(self):
        context = self.context(max_pages_per_supplier=3, max_pages=3)
        home = {"url": "https://penguinchillers.com/", "text": "Cold therapy equipment", "links": [
            {"url": "https://penguinchillers.com/pages/contact", "label": "Contact Us"},
            {"url": "https://penguinchillers.com/products/all-in-one-cold-plunge-filter", "label": "View Product"},
            {"url": "https://penguinchillers.com/collections/cold-therapy", "label": "Cold Therapy"},
            {"url": "https://penguinchillers.com/products/cold-therapy-filter-replacements", "label": "View Product"},
            {"url": "https://penguinchillers.com/products/1-hp-water-chiller", "label": "View Product"}]}
        contact = {"url": home["links"][0]["url"], "text": "Our office address is 10315 Cogdill Rd, Knoxville, TN."}
        collection_url = "https://penguinchillers.com/collections/cold-therapy"
        def fetch(url, ctx, **kwargs):
            ctx.take_page()
            # The unfetched collection body is deliberately unavailable in this routing test.
            return {home["url"]: home, contact["url"]: contact}.get(url)
        with patch.object(web_fetcher, "fetch_page", side_effect=fetch) as fetch:
            pages = web_fetcher.fetch_website_pages(home["url"], context)
        self.assertEqual([call.args[0] for call in fetch.call_args_list], [home["url"], contact["url"], collection_url])
        self.assertEqual(context.pages, 3)
        self.assertEqual(len(pages), 2)

    def test_accessories_do_not_inherit_complete_system_priority_from_their_names(self):
        product = "Complete cold plunge systems"
        collection = web_fetcher._page_priority("https://example.com/collections/cold-therapy", product, "Cold Therapy")
        for slug, label in [
            ("all-in-one-cold-plunge-filter", "View Product"),
            ("integrated-cold-plunge-cover", "View Product"),
            ("cold-plunge-filter-bundle", "View Product"),
            ("12345", "Replacement filters for the all-in-one cold plunge"),
            ("cold-plunge-system-accessories", "Complete plunge system accessories"),
        ]:
            with self.subTest(slug=slug, label=label):
                rank = web_fetcher._page_priority("https://example.com/products/" + slug, product, label)
                self.assertLess(collection, rank)

    def test_complete_tub_with_included_accessories_keeps_product_priority(self):
        product = "Complete cold plunge systems"
        collection = web_fetcher._page_priority("https://example.com/collections/cold-plunges", product)
        for slug, label in [
            ("cold-plunge-tub-bundle-with-filter-and-cover", "Cold plunge tub bundle with filter and cover"),
            ("cold-plunge-with-integrated-filtration", "Cold plunge with integrated filtration"),
            ("c1", "All-in-one cold plunge with filter and cover"),
        ]:
            with self.subTest(slug=slug):
                rank = web_fetcher._page_priority("https://example.com/products/" + slug, product, label)
                self.assertLess(rank, collection)

    def test_specific_filter_brief_can_still_choose_a_filter(self):
        home = {"url": "https://example.com/", "text": "Cold therapy", "links": [
            {"url": "https://example.com/collections/cold-therapy", "label": "Cold Therapy"},
            {"url": "https://example.com/products/all-in-one-cold-plunge-filter", "label": "Replacement filter"}]}
        filter_page = {"url": home["links"][1]["url"], "text": "Replacement filters"}
        def fetch(url, ctx, **kwargs):
            ctx.take_page()
            return {home["url"]: home, filter_page["url"]: filter_page}[url]
        for product in ["Cold plunge replacement filters", "Complete cold plunge filter systems"]:
            with self.subTest(product=product):
                context = self.context(name=product, max_pages_per_supplier=2, max_pages=2, allowed_countries=[])
                context.request.product = product
                with patch.object(web_fetcher, "fetch_page", side_effect=fetch) as call:
                    web_fetcher.fetch_website_pages(home["url"], context)
                self.assertEqual(call.call_args_list[1].args[0], filter_page["url"])
                self.assertEqual(context.pages, 2)

    def test_visible_text_quotes_and_observed_links_are_preserved_separately(self):
        context = self.context()
        html = '<main><p>Our system includes a <strong>tub</strong> and chiller.</p><a href="/products/plunge">Plunge system</a></main>'
        with patch.object(web_fetcher, "run_actor", return_value=[{"html":html,"markdown":"Our system includes a **tub** and chiller."}]):
            page = web_fetcher.fetch_page("https://example.com/", context)
        self.assertTrue(supplier_validator.quote_in_source("Our system includes a tub and chiller.", page["text"]))
        self.assertEqual(page["text_format"], "visible_html_text")
        prompt = web_fetcher.prompt_pages([page], context.request.product)[0]
        self.assertEqual(prompt["observed_product_links"][0]["url"], "https://example.com/products/plunge")

    def test_hq_heading_and_location_value_stay_in_one_source_window(self):
        text = "Navigation "*200 + "\n\nFounded\n\n2021\n\nHeadquarters\n\nSan Diego, California\n\nFounders\n\nExample founders"
        excerpts = web_fetcher.prompt_pages([{"url":"https://example.com/about","text":text}], "Complete cold plunge systems", countries=["United States"])[0]["excerpts"]
        self.assertTrue(any("Headquarters\n\nSan Diego, California" in excerpt for excerpt in excerpts))
        self.assertTrue(hq_quote_acceptable("Headquarters San Diego, California", text, "https://example.com/about"))

    def test_invalid_country_quote_has_an_actionable_diagnostic(self):
        issues = []
        quote = "Founded in San Diego in 2021"
        evidence = [{"claim":"country","source_url":"https://example.com/about","quote":quote}]
        valid, _ = supplier_validator.validate_evidence(evidence, [{"url":"https://example.com/about","text":quote}], diagnostics=issues)
        self.assertEqual(valid, [])
        self.assertEqual(issues[0]["reason"], "quote_does_not_establish_company_location")

    def test_long_literal_office_quote_is_shortened_without_losing_its_context(self):
        quote = "Our office address in central Oregon is 1104 SE Lake Rd Ste. 101, Redmond, OR 97756."
        pages = [{"url":"https://example.com/contact", "text":quote}]
        evidence = [{"claim":"country","source_url":pages[0]["url"],"quote":quote}]
        valid, ok = supplier_validator.validate_evidence(evidence,pages)
        self.assertTrue(ok)
        self.assertEqual(len(valid),1)
        self.assertLessEqual(len(valid[0]["quote"].split()),12)
        self.assertIn("1104 SE Lake Rd", valid[0]["quote"])
        self.assertTrue(supplier_validator.quote_in_source(valid[0]["quote"],quote))
        self.assertEqual(valid[0]["original_quote"],supplier_validator._norm_quote(quote))
        self.assertEqual(valid[0]["location_type"], "office")

    def test_bluecube_workshop_address_cannot_establish_headquarters(self):
        url = "https://bluecubebaths.com/pages/contact"
        text = ("Visit us in central Oregon — 1104 SE Lake Rd Ste. 101, Redmond, OR 97756. "
                "Experience contrast therapy with adjustable flow rates, tour our workshop, "
                "and see the craftsmanship behind every BlueCube.")
        for quote in ["Visit us in central Oregon — 1104 SE Lake Rd",
                      "1104 SE Lake Rd Ste. 101, Redmond, OR 97756", text]:
            with self.subTest(quote=quote):
                issues = []
                valid, _ = supplier_validator.validate_evidence(
                    [{"claim": "country", "source_url": url, "quote": quote}],
                    [{"url": url, "text": text}], diagnostics=issues)
                self.assertEqual(valid, [])
                self.assertEqual(issues[0]["location_type"], "workshop")

    def test_contact_path_and_generic_contact_heading_do_not_make_an_office(self):
        quote = "318448 8th Line NE Melancthon, ON Canada"
        for path in ["contact", "about", "company", "locations"]:
            for prefix in ["", "Contact Us\n\n", "Company Address\n\n", "Office Hours\n\nMon-Fri 9-5\n\n"]:
                with self.subTest(path=path, prefix=prefix):
                    self.assertFalse(hq_quote_acceptable(quote, prefix + quote, "https://example.com/" + path))

    def test_office_and_headquarters_phrases_still_need_an_actual_location(self):
        for quote in ["Call us at our office", "Visit our office in person", "Headquarters: Our team",
                      "Our headquarters is in the building", "Our office hours are 9-5"]:
            with self.subTest(quote=quote):
                self.assertFalse(hq_quote_acceptable(quote, quote, "https://example.com/contact"))

    def test_location_types_preserve_explicit_offices_and_hq_cards(self):
        cases = [
            ("Headquarters San Diego, California", "Headquarters\n\nSan Diego, California", "headquarters"),
            ("coldture hq is in vaughan, ontario", "coldture hq is in vaughan, ontario", "headquarters"),
            ("10315 Cogdill Rd Knoxville, TN 37932", "Office Address\n\nKnoxville Office\n\n10315 Cogdill Rd\n\nKnoxville, TN 37932", "office"),
            ("Office Address 20730 72nd Ave S, Kent, WA 98032", "Office Address\n\n20730 72nd Ave S, Kent, WA 98032", "office"),
            ("Melancthon, ON Canada, L9V 2K3", "Head Office & Manufacturing\nLeisurecraft\n\n318448 8th Line NE\nMelancthon, ON\nCanada, L9V 2K3", "headquarters"),
            ("Based in Surrey, BC", "Based in Surrey, BC, we ship worldwide.", "company_base"),
        ]
        for quote, text, kind in cases:
            with self.subTest(quote=quote):
                valid, _ = supplier_validator.validate_evidence(
                    [{"claim": "country", "source_url": "https://example.com/", "quote": quote}],
                    [{"url": "https://example.com/", "text": text}])
                self.assertEqual(len(valid), 1)
                self.assertEqual(valid[0]["location_type"], kind)

    def test_office_or_hq_heading_does_not_leak_to_another_location(self):
        quote = "555 Production Rd, Vancouver, BC"
        for text in [
            "Headquarters\n\nToronto, Ontario\n\nWorkshop\n\n" + quote,
            "Our Office\n\n111 Business Rd, Toronto, ON\n\n" + quote,
            "Headquarters: Toronto, Ontario.\n\nLearn more about our products.\n\n" + quote,
        ]:
            with self.subTest(text=text):
                self.assertFalse(hq_quote_acceptable(quote, text, "https://example.com/contact"))

    def test_production_sites_and_clipped_based_in_statements_do_not_prove_hq(self):
        for kind in ["workshop", "factory", "showroom", "warehouse", "distribution center"]:
            source = "Our " + kind + " is based in Toronto, Ontario."
            with self.subTest(kind=kind):
                self.assertFalse(hq_quote_acceptable("based in Toronto, Ontario", source, "https://example.com/about"))
        for statement in ["Our office is in Toronto, Ontario", "Our headquarters are in Toronto, Ontario"]:
            self.assertTrue(hq_quote_acceptable(statement, statement + ".\n\nVisit our workshop in Vancouver, BC.", "https://example.com/"))

    def test_workshop_only_supplier_stays_in_review_despite_model_hq_claim(self):
        url = "https://example.com/contact"
        quote = "1104 SE Lake Rd, Redmond, OR 97756"
        text = ("We manufacture cold plunge systems. Integrated chiller included in the plunge tub. "
                "[System](https://example.com/products/plunge)\n\nWorkshop\n\n" + quote)
        analysis = {"is_product_company": True, "company_name": "Example", "supplier_type": "Manufacturer", "owns_brand": True,
            "product_match": "supported", "product_kind": "primary", "matched_product_urls": ["https://example.com/products/plunge"],
            "country": "United States", "country_basis": "headquarters", "identity_match": "not_requested", "email": None, "phone": None,
            "confidence": 0.9, "notes": "Synthetic regression", "evidence": [
                {"claim": "role", "source_url": url, "quote": "We manufacture cold plunge systems"},
                {"claim": "product_match", "source_url": url, "quote": "Integrated chiller included in the plunge tub"},
                {"claim": "country", "source_url": url, "quote": quote}]}
        context = self.context(allowed_countries=["United States"])
        with patch.object(supplier_validator, "fetch_website_pages", return_value=[{"url": url, "text": text}]), \
             patch.object(supplier_validator, "analyze_supplier_with_llm", return_value=analysis):
            result = supplier_validator.process_supplier(context.request.product, url, context)
        self.assertEqual(result["status"], "review")
        self.assertEqual(result["reason"], "headquarters_not_established")
        self.assertEqual(result["evidence_issues"][0]["location_type"], "workshop")
        self.assertEqual({e["claim"] for e in result["evidence"]}, {"role", "product_match"})

    def test_unlabelled_footer_address_routes_to_contact_without_becoming_hq(self):
        context = self.context(max_pages_per_supplier=3, max_pages=3)
        home = {"url": "https://example.com/", "text": "318448 8th Line NE\nMelancthon, ON\nCanada", "links": [
            {"url": "https://example.com/about", "label": "About"},
            {"url": "https://example.com/contact", "label": "Contact"},
            {"url": "https://example.com/products/cold-plunge", "label": "Plunge"}]}
        contact = {"url": "https://example.com/contact", "text": home["text"]}
        product = {"url": "https://example.com/products/cold-plunge", "text": "Tub with included chiller"}
        def fetch(url, ctx, **kwargs):
            ctx.take_page()
            return {p["url"]: p for p in [home, contact, product]}[url]
        with patch.object(web_fetcher, "fetch_page", side_effect=fetch) as call:
            web_fetcher.fetch_website_pages(home["url"], context)
        self.assertEqual([c.args[0] for c in call.call_args_list], [home["url"], contact["url"], product["url"]])
        self.assertFalse(hq_quote_acceptable(home["text"], contact["text"], contact["url"]))
        self.assertEqual(context.pages, 3)

    def test_long_nonliteral_or_non_hq_quotes_cannot_be_repaired_into_hq(self):
        cases = [
            ("We always ship every one of our cold plunge products directly to customers throughout Canada.",
             "We always ship every one of our cold plunge products directly to customers throughout Canada."),
            ("Our wonderful company office is actually based in Toronto Ontario and this quote was invented.",
             "Based in Toronto, Ontario."),
        ]
        for quote, text in cases:
            with self.subTest(quote=quote):
                valid, _ = supplier_validator.validate_evidence(
                    [{"claim":"country","source_url":"https://example.com/contact","quote":quote}],
                    [{"url":"https://example.com/contact","text":text}])
                self.assertEqual(valid,[])

    def test_navigation_only_html_still_triggers_optional_browser(self):
        context = self.context(allow_browser_fallback=True, max_pages=2)
        nav = "<nav>"+("Menu links "*100)+"</nav>"
        def actor(*args, **kwargs):
            if args[1]["scrapingTool"] == "raw-http":
                return [{"html":nav,"markdown":"Menu links "*100}]
            return [{"html":"<main>"+("Cold plunge product evidence "*30)+"</main>", "markdown":"Cold plunge product evidence "*30}]
        with patch.object(web_fetcher, "run_actor", side_effect=actor) as run:
            page = web_fetcher.fetch_page("https://example.com/", context, attempts_left=2)
        self.assertEqual(run.call_count, 2)
        self.assertTrue(page["browser_fallback"])
        self.assertEqual(context.pages, 2)

    def test_product_contents_survive_many_exclusion_and_country_mentions(self):
        context = self.context()
        content = ("Menu Canada complete plunge systems. "*100)+"\n\n"
        content += "\n\n".join("Replacement filters and assembly services are separate." for _ in range(20))
        contents = "The Glacier package includes a stainless tub and an integrated chiller."
        content += "\n\n"+contents+"\n\nOur headquarters are in Toronto, Ontario.\n\nWe manufacture our own cold plunge systems.\n\nsales@example.com"
        excerpts = web_fetcher.prompt_pages([{"url":"https://example.com/", "text":content}], context.request.product,
            countries=["Canada"], extra_terms=["replacement filters", "assembly services", "sauna heaters", "inflatable tubs without a chiller"])[0]["excerpts"]
        self.assertTrue(any(contents in s for s in excerpts))
        self.assertTrue(any("We manufacture our own" in s for s in excerpts))
        self.assertTrue(any("sales@example.com" in s for s in excerpts))
        self.assertLessEqual(len(excerpts), 14)

    def test_country_quote_requires_affirmative_company_location(self):
        rejected = ["Ships throughout Canada", "Free delivery in Canada", "Made in Canada", "Born in California",
                    "Our products are assembled in Oregon", "Visit our Ontario showroom", "Warehouse address: Toronto, Ontario",
                    "Enter your billing address", "Our headquarters are not in Canada", "Our HQ", "Canada", "### Knoxville Office"]
        for quote in rejected:
            with self.subTest(quote=quote):
                self.assertFalse(hq_quote_acceptable(quote, quote, "https://example.com/contact"))
        accepted = ["Based in Surrey, BC", "Headquarters: San Diego, California", "coldture hq is in vaughan, ontario",
                    "We're a Surrey, BC manufacturer", "Our head office is in Toronto, Ontario"]
        for quote in accepted:
            with self.subTest(quote=quote):
                self.assertTrue(hq_quote_acceptable(quote, quote, "https://example.com/about"))

    def test_street_address_requires_office_context_and_rejects_return_address(self):
        quote = "1104 SE Lake Rd Ste. 101, Redmond, OR 97756"
        self.assertFalse(hq_quote_acceptable(quote, quote, "https://example.com/contact"))
        self.assertTrue(hq_quote_acceptable(quote, "Office Address\n\n" + quote, "https://example.com/contact"))
        self.assertFalse(hq_quote_acceptable(quote, quote, "https://example.com/products/plunge"))
        self.assertFalse(hq_quote_acceptable(quote, "Return shipping address: "+quote, "https://example.com/contact"))
        self.assertFalse(hq_quote_acceptable("Toronto, Ontario", "Our warehouse is in Toronto, Ontario", "https://example.com/about"))

    def test_clipped_negation_and_customer_location_do_not_prove_company_hq(self):
        quote = "based in Canada"
        self.assertFalse(hq_quote_acceptable(quote, "We are not based in Canada.", "https://example.com/about"))
        self.assertFalse(hq_quote_acceptable(quote, "Our customer is based in Canada.", "https://example.com/about"))
        self.assertTrue(hq_quote_acceptable("Based in Surrey, BC", "Based in Surrey, BC, we ship worldwide.", "https://example.com/about"))

    def test_unrelated_shipping_paragraph_does_not_void_valid_location(self):
        quote = "Our headquarters are in Toronto, Ontario"
        source = quote+".\n\nShipping and returns are available throughout Canada."
        self.assertTrue(hq_quote_acceptable(quote, source, "https://example.com/"))

    def test_shipping_only_synthetic_supplier_stays_in_review(self):
        url = "https://example.com/"
        text = "We manufacture cold plunge systems. Integrated chiller included in the plunge tub. Ships throughout Canada. [System](https://example.com/products/plunge)"
        analysis = {"is_product_company":True,"company_name":"Example","supplier_type":"Manufacturer","owns_brand":True,
            "product_match":"supported","product_kind":"primary","matched_product_urls":["https://example.com/products/plunge"],
            "country":"Canada","country_basis":"headquarters","identity_match":"not_requested","email":None,"phone":None,"confidence":0.9,"notes":"Synthetic regression",
            "evidence":[{"claim":"role","source_url":url,"quote":"We manufacture cold plunge systems"},
                        {"claim":"product_match","source_url":url,"quote":"Integrated chiller included in the plunge tub"},
                        {"claim":"country","source_url":url,"quote":"Ships throughout Canada"}]}
        context = self.context(allowed_countries=["Canada"])
        with patch.object(supplier_validator,"fetch_website_pages",return_value=[{"url":url,"text":text}]), \
             patch.object(supplier_validator,"analyze_supplier_with_llm",return_value=analysis):
            result = supplier_validator.process_supplier(context.request.product, url, context)
        self.assertEqual(result["status"], "review")
        self.assertEqual(result["reason"], "headquarters_not_established")
        self.assertEqual({e["claim"] for e in result["evidence"]}, {"role", "product_match"})
        self.assertEqual(context.operations, [])

    def test_development_preview_runner_refuses_final_check_cases_before_calls(self):
        path = Path(__file__).parents[1]/"docs"/"benchmarks"/"cold-plunge-2026-10-27"/"run_evidence_check.py"
        spec = importlib.util.spec_from_file_location("evidence_check_runner_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys,"argv",[str(path),"--cases","final-inergize","--round","protected-case"]), \
             patch.object(web_fetcher,"run_actor") as actor, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                module.main()
        self.assertEqual(stopped.exception.code, 2)
        actor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
