import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from backend.security import load_fernet


class FernetConfigurationTests(unittest.TestCase):
    def test_missing_key_defaults_to_production_and_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "REPORTFORGE_SECRET_KEY is required"):
                load_fernet()

    def test_non_development_environment_fails_closed_without_key(self):
        with patch.dict(os.environ, {"REPORTFORGE_ENV": "staging"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "REPORTFORGE_SECRET_KEY is required"):
                load_fernet()

    def test_development_fallback_requires_explicit_opt_in(self):
        with patch.dict(os.environ, {"REPORTFORGE_ENV": "development"}, clear=True):
            cipher = load_fernet()
        token = cipher.encrypt(b"development-only")
        self.assertEqual(cipher.decrypt(token), b"development-only")

    def test_production_uses_a_valid_configured_key(self):
        key = Fernet.generate_key().decode("ascii")
        with patch.dict(
            os.environ,
            {"REPORTFORGE_ENV": "production", "REPORTFORGE_SECRET_KEY": key},
            clear=True,
        ):
            cipher = load_fernet()
        token = cipher.encrypt(b"production-secret")
        self.assertEqual(cipher.decrypt(token), b"production-secret")

    def test_invalid_configured_key_fails_even_in_development(self):
        with patch.dict(
            os.environ,
            {"REPORTFORGE_ENV": "development", "REPORTFORGE_SECRET_KEY": "invalid"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "valid URL-safe base64 Fernet key"):
                load_fernet()

    def test_application_import_fails_closed_without_production_key(self):
        env = os.environ.copy()
        env.pop("REPORTFORGE_SECRET_KEY", None)
        env.pop("REPORTFORGE_ENV", None)
        result = subprocess.run(
            [sys.executable, "-c", "import backend.main"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REPORTFORGE_SECRET_KEY is required", result.stderr)


if __name__ == "__main__":
    unittest.main()
