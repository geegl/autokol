"""Minimal tests for src.utils.api_keys (C3 from audit plan)."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock streamlit before importing the module
st_mock = MagicMock()
st_mock.secrets = {}
sys.modules["streamlit"] = st_mock

import src.utils.api_keys as api_keys_mod
from src.utils.api_keys import get_progress_api_key, iter_api_keys

MOCK_FALLBACK = "test_fallback_key"


class TestGetProgressApiKey(unittest.TestCase):
    """get_progress_api_key: st.secrets > env > fallback."""

    def test_returns_fallback_when_nothing_set(self):
        st_mock.secrets = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
                result = get_progress_api_key()
                self.assertEqual(result, MOCK_FALLBACK)

    def test_returns_env_var_when_set(self):
        st_mock.secrets = {}
        with patch.dict(os.environ, {"PROGRESS_API_KEY": "env-key-123"}, clear=True):
            with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
                result = get_progress_api_key()
                self.assertEqual(result, "env-key-123")

    def test_returns_secrets_over_env(self):
        with patch.dict(os.environ, {"PROGRESS_API_KEY": "env-key"}, clear=True):
            st_mock.secrets = {"PROGRESS_API_KEY": "secret-key"}
            with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
                result = get_progress_api_key()
                self.assertEqual(result, "secret-key")

    def test_returns_env_when_secrets_raises(self):
        with patch.dict(os.environ, {"PROGRESS_API_KEY": "env-fallback"}, clear=True):
            st_mock.secrets = MagicMock()
            st_mock.secrets.__contains__ = MagicMock(side_effect=Exception("no secrets"))
            with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
                result = get_progress_api_key()
                self.assertEqual(result, "env-fallback")


class TestIterApiKeys(unittest.TestCase):
    """iter_api_keys: primary + fallback (deduplicated)."""

    def test_returns_primary_then_fallback(self):
        with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
            with patch.object(api_keys_mod, "get_progress_api_key", return_value="primary"):
                keys = iter_api_keys()
                self.assertEqual(keys, ["primary", MOCK_FALLBACK])

    def test_returns_only_fallback_when_primary_is_fallback(self):
        with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
            with patch.object(api_keys_mod, "get_progress_api_key", return_value=MOCK_FALLBACK):
                keys = iter_api_keys()
                self.assertEqual(keys, [MOCK_FALLBACK])

    def test_no_duplicates_when_primary_equals_fallback(self):
        with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
            with patch.object(api_keys_mod, "get_progress_api_key", return_value=MOCK_FALLBACK):
                keys = iter_api_keys()
                self.assertEqual(len(keys), 1)

    def test_returns_list_type(self):
        with patch.object(api_keys_mod, "FALLBACK_PROGRESS_API_KEY", MOCK_FALLBACK):
            with patch.object(api_keys_mod, "get_progress_api_key", return_value="x"):
                result = iter_api_keys()
                self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
