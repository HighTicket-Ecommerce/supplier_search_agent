import unittest
from unittest.mock import patch
from backend import config


class ManifestReviewTests(unittest.TestCase):
    def test_effective_model_configuration_has_only_explicit_non_secret_fields(self):
        with patch.multiple(config, OPENAI_MODEL="configured-snapshot", OPENAI_MAX_OUTPUT_TOKENS=2048,
                            OPENAI_INPUT_USD_PER_MILLION=2.0, OPENAI_OUTPUT_USD_PER_MILLION=10.0,
                            OPENAI_API_KEY="must-not-be-captured", APIFY_TOKEN="must-not-be-captured"):
            self.assertEqual(config.model_settings_snapshot(), {"model": "configured-snapshot", "max_output_tokens": 2048,
                "input_usd_per_million": 2.0, "output_usd_per_million": 10.0})
