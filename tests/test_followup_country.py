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

    def test_sales_markets_do_not_extend_the_headquarters_address(self):
        for text in ['Headquarters: Kent, WA 98032; we also sell to Canada.',
                     'Headquarters: Kent, WA 98032, serving the USA and Canada.',
                     'Selling across Canada from our headquarters in Kent, WA 98032.',
                     'Headquarters\n\nKent, WA 98032\n\nWe also sell to Canada.',
                     'Headquarters: 1234 Example Ave, Ontario, California 91761']:
            with self.subTest(text=text): self.assert_country(text,'United States','headquarters')

    def test_unresolved_headquarters_cards_block_lower_priority_offices(self):
        for card in ['HEADQUARTERS\n\nSINGAPORE', 'Company HQ\n\nSINGAPORE', 'World HQ\n\nSINGAPORE',
                     'HQ\n\nHo Chi Minh City', 'HQ\n\nSão Paulo', 'HQ\nSingapore', 'HQ | Singapore',
                     '<h4>HQ</h4><span>Singapore</span>']:
            text=card+('<p>Office: Kent, WA 98032</p>' if '<' in card else '\n\nOffice: Kent, WA 98032')
            with self.subTest(card=card):
                result=self.check(text)
                self.assertEqual((result['status'],result['country'],result['location_type']),('not_established',None,'headquarters'),result)
        self.assert_country('HQ\n\nCanada\n\nOffice: Kent, WA 98032','Canada','headquarters')
