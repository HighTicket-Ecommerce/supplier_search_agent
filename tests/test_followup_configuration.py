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

    def test_exclusion_and_compatibility_headings_do_not_supply_components(self):
        for heading in ['Does not include', "Doesn't include", "What isn't included", "Doesn't come with", 'Does not come with', 'Never included', 'Pairs well with']:
            with self.subTest(heading=heading):
                self.assertEqual(self.check(heading+'\n\nTub and chiller', 'Tub and chiller'),'not_established')
        self.assertEqual(self.check('Included\n\nTub and chiller','Tub and chiller'),'supported')

    def test_inventory_list_names_do_not_describe_one_configuration(self):
        for prefix in ['Products include','Our product line includes','Our lineup includes','Our collection includes','Our offerings include','The shop features']:
            quote=prefix+' tubs and chillers'
            for path in ['/products/plunge','/collections/plunges']:
                with self.subTest(quote=quote,path=path):
                    self.assertEqual(self.check(quote,quote,path),'not_established')
