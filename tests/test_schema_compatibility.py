"""Compare complete outbound schemas with the reconstructed pre-upgrade baseline."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from backend import model_client
from backend.models import CatalogueAnalysis, SupplierAnalysis


class SchemaCompatibilityTests(unittest.TestCase):
    def test_both_outbound_schemas_match_pre_upgrade_runtime(self):
        frozen = json.loads((Path(__file__).parent / "fixtures/pre_upgrade_schemas.json").read_text())
        # PR #11 deliberately adds two location bases; all other pre-upgrade schema
        # structure stays frozen. The original fixture remains unchanged.
        frozen["supplier_analysis"]["properties"]["country_basis"]["enum"] = [
            "headquarters", "office", "company_base", "manufacturing", "market", "unknown"]
        for name, model in (("supplier_analysis", SupplierAnalysis), ("catalogue_analysis", CatalogueAnalysis)):
            with self.subTest(name=name):
                response = SimpleNamespace(id="offline", usage=None, choices=[SimpleNamespace(finish_reason="length")])
                context = MagicMock()
                context.remaining_seconds.return_value = 30
                with patch.object(model_client.client.chat.completions, "create", return_value=response) as create, \
                     patch.object(model_client, "OPENAI_API_KEY", "offline"), \
                     patch.object(model_client, "OPENAI_INPUT_USD_PER_MILLION", 1.75), \
                     patch.object(model_client, "OPENAI_OUTPUT_USD_PER_MILLION", 14):
                    model_client.request_structured([{"role": "user", "content": "Offline schema test"}], model,
                                                    context, schema_name=name)
                self.assertEqual(create.call_args.kwargs["response_format"], {"type": "json_schema", "json_schema": {
                    "name": name, "strict": True, "schema": frozen[name]}})
