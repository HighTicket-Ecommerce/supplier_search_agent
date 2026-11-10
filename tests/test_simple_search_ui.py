"""The everyday supplier-search flow should need business inputs only."""
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest
from backend.models import ResearchRequest

APP = Path(__file__).resolve().parents[1] / 'ui' / 'streamlit_app.py'


class SimpleSearchUITests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'SUPPLIER_UI_PASSWORD': '', 'SUPPLIER_API_KEY': 'offline-ui-key'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected network'))
        self.network.start(); self.addCleanup(self.network.stop)

    def test_default_search_shows_business_filters_and_no_technical_controls(self):
        with patch('requests.request') as request:
            app = AppTest.from_file(str(APP)).run()
        self.assertFalse(app.exception)
        self.assertEqual([w.label for w in app.main.text_input], ['Product types', 'Exclude products'])
        self.assertEqual([w.label for w in app.main.multiselect], ['Supplier country', 'Supplier type'])
        self.assertEqual([w.label for w in app.main.number_input], ['Suppliers to find', 'Search budget ($)'])
        self.assertIn('Search', [w.label for w in app.main.button])
        self.assertEqual(app.main.expander[0].label, 'More options')
        self.assertFalse(app.main.expander[0].proto.expanded)
        self.assertEqual(list(app.selectbox), [])
        self.assertEqual(list(app.text_area), [])
        self.assertEqual(list(app.get('file_uploader')), [])
        roles = next(w for w in app.multiselect if w.label == 'Supplier type')
        self.assertEqual(roles.options, ['Manufacturer', 'Brand owner', 'Distributor'])
        self.assertEqual([w.label for w in app.checkbox], ['Allow Google Sheets export after review'])
        request.assert_not_called()

    def start_search(self, *, customize=False, supplier_type="Manufacturer", allow_export=False):
        payloads = []
        qualified = [{'url': 'https://fixture.example', 'supplier_name': 'Fixture supplier', 'status': 'qualified'}] if allow_export else []
        def request(method, url, **kwargs):
            response = MagicMock()
            if method == 'POST':
                payloads.append(kwargs['json']); response.json.return_value = {'job_id': 'simple-ui'}
            elif '/status/' in url:
                response.json.return_value = {'status': 'completed', 'accepted_count': len(qualified), 'review_count': 0, 'processed': len(qualified)}
            else:
                response.json.return_value = {'job_id': 'simple-ui', 'status': 'completed', 'accepted': qualified, 'review': [], 'rejected': [], 'preview_only': payloads[0]['preview_only']}
            return response
        with patch('requests.request', side_effect=request):
            app = AppTest.from_file(str(APP)).run()
            next(w for w in app.text_input if w.label == 'Product types').set_value('Sauna heaters')
            next(w for w in app.multiselect if w.label == 'Supplier country').set_value(['Canada'])
            next(w for w in app.multiselect if w.label == 'Supplier type').set_value([supplier_type])
            next(w for w in app.text_input if w.label == 'Exclude products').set_value('replacement parts, accessories')
            if customize:
                next(w for w in app.number_input if w.label == 'Suppliers to find').set_value(7)
                next(w for w in app.number_input if w.label == 'Search budget ($)').set_value(2.0)
            if allow_export:
                next(w for w in app.checkbox if w.label == 'Allow Google Sheets export after review').check()
            next(w for w in app.button if w.label == 'Search').click().run()
            if allow_export:
                candidates = next(w for w in app.multiselect if w.label == 'Select reviewed candidates to export')
                self.assertEqual(candidates.value, [])
                self.assertTrue(next(w for w in app.button if w.label == 'Export selected to Google Sheets').disabled)
                candidates.set_value(['https://fixture.example']).run()
                self.assertFalse(next(w for w in app.button if w.label == 'Export selected to Google Sheets').disabled)
        self.assertFalse(app.exception)
        self.assertEqual(len(payloads), 1)
        return payloads[0]

    def test_basic_search_preserves_filters_and_bounded_backend_defaults(self):
        payload = self.start_search()
        request = ResearchRequest.model_validate(payload)
        self.assertEqual(request.product, 'Sauna heaters')
        self.assertEqual(request.allowed_countries, ['Canada'])
        self.assertEqual(request.allowed_supplier_types, ['Manufacturer'])
        self.assertEqual(request.excluded_products, ['replacement parts', 'accessories'])
        self.assertTrue(request.use_apify); self.assertTrue(request.preview_only)
        self.assertEqual(request.candidate_urls, [])
        self.assertEqual(request.research_mode, 'supplier_search')
        self.assertIsNone(request.master_reference_id)
        self.assertFalse(request.use_shopping); self.assertFalse(request.use_shopify_catalogue)
        self.assertEqual((request.max_pages, request.max_pages_per_supplier, request.max_external_calls, request.max_runtime_seconds), (30, 3, 50, 300))
        self.assertEqual((request.target_suppliers, request.max_execution_cost_usd), (5, 5.0))
        self.assertNotIn('max_pages', payload)

    def test_more_options_can_adjust_business_goal_and_budget(self):
        request = ResearchRequest.model_validate(self.start_search(customize=True))
        self.assertEqual((request.target_suppliers, request.max_execution_cost_usd), (7, 2.0))
        self.assertTrue(request.preview_only)

    def test_export_opt_in_enables_explicit_selection_without_exporting_automatically(self):
        request = ResearchRequest.model_validate(self.start_search(allow_export=True))
        self.assertFalse(request.preview_only)

    def test_distributor_search_keeps_its_evidence_allowance_without_a_page_control(self):
        request = ResearchRequest.model_validate(self.start_search(supplier_type='Distributor'))
        self.assertEqual(request.max_pages_per_supplier, 4)
        self.assertEqual(request.max_pages, 30)
        self.assertEqual(request.max_execution_cost_usd, 5.0)
