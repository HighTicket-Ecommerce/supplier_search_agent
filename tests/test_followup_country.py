import unittest
from backend.country_evidence import verify_company_location
from backend.web_fetcher import PageHTML

class CountryFollowupTests(unittest.TestCase):
    def check(self,text):
        if '<' in text:
            parser=PageHTML(); parser.feed(text); text=''.join(parser.parts)
        return verify_company_location([], [{'url':'https://example.com/contact','text':text}])
    def assert_country(self,text,country,kind):
        result=self.check(text)
        self.assertEqual((result['status'],result['country'],result['location_type']),('supported',country,kind), result)
        self.assertTrue(all(len(e['quote'].split())<=12 for e in result['supporting_evidence']))

    def test_shipping_after_an_address_is_outside_the_location_card(self):
        self.assert_country('Headquarters\n\nKent, WA 98032\n\nNow shipping to Canada!', 'United States','headquarters')
