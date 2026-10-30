import unittest
from backend.role_evidence import verify_supplier_role, recover_role_evidence

class RoleFollowupTests(unittest.TestCase):
    def check(self, text, role='Manufacturer', product='Sauna heaters', heading='Example'):
        url='https://example.com/about'; pages=[{'url':url,'text':heading+'\n\n'+text}]
        result=verify_supplier_role(role,'Example',[{'claim':'role','source_url':url,'quote':text}],pages,product)
        return result['status'], recover_role_evidence(role,'Example',pages,product)

    def test_foreign_manufacturer_and_warranty_labels_cannot_attribute_production(self):
        negatives=['Manufacturer: Harvia','Manufacturer warranty: 5 years on our heaters.',
                   'The manufacturer of our heaters is Harvia.', 'A leading manufacturer supplies our heaters.',
                   'The leading manufacturer Harvia supplies all our heaters.',
                   'Example stocks heaters of a leading manufacturer.',
                   'Example is the official heater dealer of a leading manufacturer.',
                   "We are a leading manufacturer's authorized dealer.",
                   'We source our heaters from a leading manufacturer.']
        positives=['Example is a leading manufacturer of sauna heaters.',
                   'We are a leading manufacturer of sauna heaters.',
                   'Leading manufacturer of sauna heaters since 1985', 'Manufacturer: Example']
        for text in negatives+positives:
            with self.subTest(text=text):
                status,recovery=self.check(text)
                self.assertEqual(status,'supported' if text in positives else 'not_established')
                self.assertEqual(bool(recovery),text in positives)
        from test_supplier_roles import SupplierRoleTests
        fixture=SupplierRoleTests(); fixture.setUp()
        try:
            for text in negatives:
                with self.subTest(end_to_end=text):
                    row=fixture.check_supplier([text],body='Example\n\n'+text)
                    self.assertEqual(row['status'],'review')
        finally: fixture.tearDown()

    def test_product_modifiers_cannot_turn_services_into_physical_goods(self):
        for text,role,product in [
            ('We design bicycle tours across Europe','Brand owner','bicycles'),
            ('We build bicycle trails and pump tracks','Manufacturer','bicycles'),
            ('We create ceramic workshops for kids','Brand owner','Ceramic planters'),
            ('We produce kayak films and events','Manufacturer','kayaks'),
            ('We build bicycle communities','Manufacturer','bicycles')]:
            with self.subTest(text=text):
                status,recovery=self.check(text,role,product)
                self.assertEqual(status,'not_established'); self.assertFalse(recovery)
