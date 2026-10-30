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
        self.assertEqual(self.check('We manufacture saunas, chillers and cold plunges','cold plunges'),'supported')

    def test_component_heads_and_other_verbs_cannot_inherit_production(self):
        for text in ['We manufacture cold plunge lids', 'We manufacture cold plunge and ice bath chillers',
                     'We manufacture cold plunge ozone systems', 'We manufacture cold plunge stairs and handrails',
                     'We manufacture cold plunge, sauna and hot tub covers',
                     'We manufacture compressors powering cold plunge systems',
                     'We manufacture saunas and stock cold plunges from Acme',
                     'We manufacture saunas and are authorized dealers of Acme cold plunges',
                     'Example is a manufacturer of saunas and an authorized dealer of Acme cold plunges']:
            with self.subTest(text=text): self.assertEqual(self.check(text),'not_established')

    def test_self_manufacturer_descriptions_can_put_category_before_the_role(self):
        for text in ['Example is a leading cold plunge manufacturer',
                     "Example is Canada's premier cold plunge manufacturer",
                     'Example, a Canadian manufacturer of cold plunges, builds every tub by hand',
                     'Example, the leading manufacturer of cold plunges in Canada, ships worldwide']:
            with self.subTest(text=text): self.assertEqual(self.check(text),'supported')
        for text in ['The manufacturer of our cold plunges is Acme.',
                     'A leading manufacturer of cold plunges supplies our tubs.',
                     'Acme is a leading cold plunge manufacturer']:
            with self.subTest(text=text): self.assertEqual(self.check(text),'not_established')

    def test_foreign_manufacturer_words_cannot_qualify_a_complete_supplier(self):
        from test_product_roles import RequestedProductRoleTests
        fixture=RequestedProductRoleTests(); fixture.setUp()
        try:
            for text in ['The manufacturer of our cold plunges is Acme.',
                         'A leading manufacturer of cold plunges supplies our tubs.']:
                with self.subTest(text=text):
                    row=fixture.run_case(text,body='Example\n\n'+text)
                    self.assertEqual(row['status'],'review')
                    self.assertEqual(row['reason'],'supplier_role_not_established')
            row=fixture.run_case('Example is a leading cold plunge manufacturer')
            self.assertEqual(row['status'],'qualified')
        finally: fixture.tearDown()

    def test_plain_primary_category_briefs_also_require_a_product_role(self):
        from test_product_roles import RequestedProductRoleTests
        fixture=RequestedProductRoleTests(); fixture.setUp()
        try:
            for text in ['We manufacture cold plunge lids', 'We manufacture cold plunge and ice bath chillers',
                         'We manufacture cold plunge ozone systems', 'We manufacture cold plunge stairs and handrails',
                         'We manufacture cold plunge, sauna and hot tub covers',
                         'We manufacture compressors powering cold plunge systems',
                         'We manufacture saunas and stock cold plunges from Acme',
                         'We manufacture saunas and are authorized dealers of Acme cold plunges',
                         'Example is a manufacturer of saunas and an authorized dealer of Acme cold plunges']:
                with self.subTest(text=text): self.assertNotEqual(fixture.run_case(text,product='cold plunges')['status'],'qualified')
            self.assertEqual(fixture.run_case('We manufacture saunas, chillers and cold plunges',product='cold plunges')['status'],'qualified')
        finally: fixture.tearDown()
