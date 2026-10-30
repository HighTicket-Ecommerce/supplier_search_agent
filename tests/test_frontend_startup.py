"""Frontend boot with the same import isolation as the Streamlit console entry."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest


class FrontendStartupTests(unittest.TestCase):
    def test_frontend_boots_without_repository_root_on_python_path(self):
        app_path = Path(__file__).resolve().parents[1] / 'ui' / 'streamlit_app.py'
        code = textwrap.dedent('''
            import importlib.util
            import os
            from pathlib import Path
            import socket
            import sys
            from unittest.mock import patch
            sys.dont_write_bytecode = True
            import dotenv
            dotenv.load_dotenv = lambda *args, **kwargs: False

            app_path = Path(sys.argv[1])
            root = app_path.parent.parent
            assert str(root) not in sys.path
            assert importlib.util.find_spec('backend') is None
            from streamlit.testing.v1 import AppTest

            with patch.dict(os.environ, {
                'SUPPLIER_UI_PASSWORD': '', 'SUPPLIER_API_KEY': 'offline-startup-key',
                'OPENAI_API_KEY': '', 'APIFY_TOKEN': '',
            }), patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected network')), \
                 patch('requests.request', side_effect=AssertionError('Unexpected backend request')):
                app = AppTest.from_file(str(app_path)).run(timeout=15)
                assert not app.exception, [error.message for error in app.exception]
                assert app.title[0].value == 'Supplier Research Agent'
                assert any(field.label == 'Workflow' for field in app.selectbox)
        ''')
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, '-I', '-c', code, str(app_path)],
                                    cwd=tmp, capture_output=True, text=True, timeout=45,
                                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
