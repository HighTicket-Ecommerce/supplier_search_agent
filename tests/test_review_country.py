import unittest
from backend.country_evidence import verify_company_location


class CountryReviewTests(unittest.TestCase):
    def check(self, text):
        return verify_company_location([], [{"url": "https://example.com/contact", "text": text}])

    def test_sales_country_does_not_conflict_with_office_country(self):
        result = self.check("We sell in Canada. Office Address: Kent, WA 98032.")
        self.assertEqual((result["status"], result["country"]), ("supported", "United States"))

    def test_full_postal_address_disambiguates_long_ontario_california_value(self):
        result = self.check("Office Address: Our large purpose built international corporate office at 123 Industrial Road, Ontario, CA 91761")
        self.assertEqual((result["status"], result["country"]), ("supported", "United States"))
        self.assertTrue(all(len(e["quote"].split()) <= 12 for e in result["supporting_evidence"]))

    def test_unknown_split_hq_prevents_office_fallback(self):
        result = self.check("Headquarters\n\nSingapore\n\nOffice Address: Kent, WA 98032")
        self.assertEqual((result["status"], result["country"], result["location_type"]), ("not_established", None, "headquarters"))

    def test_current_hq_survives_following_future_office(self):
        result = self.check("Our headquarters are in Toronto, Ontario. Our future office will be in Germany.")
        self.assertEqual((result["status"], result["country"]), ("supported", "Canada"))
