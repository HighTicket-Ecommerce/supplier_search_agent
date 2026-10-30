import unittest
from backend.product_evidence import verify_product_configuration

class ConfigurationFollowupTests(unittest.TestCase):
    def check(self, text, quote, path='/products/plunge'):
        url='https://example.com'+path
        return verify_product_configuration('Complete cold plunge systems',
            [{'claim':'product_match','source_url':url,'quote':quote}], [{'url':url,'text':text}], [url])['status']

    def test_positive_configuration_headings_can_name_included_extras(self):
        for heading, quote in [
            ('Cold Plunge Tub and Chiller Bundle with Accessories','Includes a 1HP chiller and an insulated tub'),
            ('Free accessories included','Tub and chiller'),
            ('Included: tub, chiller and accessories','Insulated tub and 1HP chiller'),
            ('Complete system - optional upgrades available','Includes tub and chiller')]:
            with self.subTest(heading=heading):
                self.assertEqual(self.check(heading+'\n\n'+quote,quote),'supported')
