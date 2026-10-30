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
