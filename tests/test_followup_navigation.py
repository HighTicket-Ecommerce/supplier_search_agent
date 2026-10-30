import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import job_store, web_fetcher
from backend.models import ResearchRequest
from backend.research_context import ResearchContext


class NavigationFollowupTests(unittest.TestCase):
    def rank(self, path, brief="Complete cold plunge systems", label=""):
        return web_fetcher._page_priority("https://example.com"+path, brief, label)

    def test_an_accessory_for_a_bundle_remains_an_accessory(self):
        for path in ("/products/replacement-filter-for-cold-plunge-tub-and-chiller-bundle",
                     "/products/steps-for-the-plunge-and-chiller-bundle"):
            with self.subTest(path=path):
                self.assertLess(self.rank("/collections/cold-plunge-systems"), self.rank(path))
