import unittest
from backend.product_role_evidence import verify_requested_product_role

class ProductRoleFollowupTests(unittest.TestCase):
    def check(self,text,product='Complete cold plunge systems'):
        url='https://example.com/about'
        return verify_requested_product_role(product,'Manufacturer','Example',
            [{'claim':'role','source_url':url,'quote':' '.join(text.split()[:12])}], [{'url':url,'text':text}])['status']

    def test_a_primary_product_can_be_one_item_in_a_production_list(self):
        for text in ['We manufacture saunas, chillers and cold plunges',
                     'We manufacture wellness equipment including cold plunges',
                     'We manufacture recovery products such as cold plunges and saunas',
                     'We manufacture heaters, saunas and cold plunges in Finland']:
            with self.subTest(text=text): self.assertEqual(self.check(text),'supported')
        self.assertEqual(self.check('We manufacture saunas, chillers and cold plunges','cold plunges'),'not_required')

    def test_component_heads_and_other_verbs_cannot_inherit_production(self):
        for text in ['We manufacture cold plunge lids', 'We manufacture cold plunge and ice bath chillers',
                     'We manufacture cold plunge ozone systems', 'We manufacture cold plunge stairs and handrails',
                     'We manufacture cold plunge, sauna and hot tub covers',
                     'We manufacture compressors powering cold plunge systems',
                     'We manufacture saunas and stock cold plunges from Acme',
                     'We manufacture saunas and are authorized dealers of Acme cold plunges',
                     'Example is a manufacturer of saunas and an authorized dealer of Acme cold plunges']:
            with self.subTest(text=text): self.assertEqual(self.check(text),'not_established')
