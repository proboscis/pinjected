"""Tests for environment variable parser for PINJECTED_* variables."""

import os
from unittest.mock import patch

from pinjected.run_helpers.env_var_parser import parse_pinjected_env_vars


class TestEnvVarParser:
    """Tests for parse_pinjected_env_vars function."""

    def test_parse_pinjected_env_vars_empty(self):
        """Test parsing when no PINJECTED_* vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {}

    def test_parse_pinjected_env_vars_single(self):
        """Test parsing a single PINJECTED_ variable."""
        with patch.dict(os.environ, {"PINJECTED_API_KEY": "secret123"}, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {"api_key": "secret123"}

    def test_parse_pinjected_env_vars_multiple(self):
        """Test parsing multiple PINJECTED_ variables."""
        env_vars = {
            "PINJECTED_API_KEY": "secret123",
            "PINJECTED_DATABASE_URL": "postgresql://localhost/db",
            "PINJECTED_MAX_RETRIES": "3",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {
                "api_key": "secret123",
                "database_url": "postgresql://localhost/db",
                "max_retries": "3",
            }

    def test_parse_pinjected_env_vars_mixed_case(self):
        """Test that env var names are converted to lowercase."""
        with patch.dict(os.environ, {"PINJECTED_MixedCase": "value"}, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {"mixedcase": "value"}

    def test_parse_pinjected_env_vars_import_syntax(self):
        """Test that import syntax {module.var} is preserved."""
        with patch.dict(
            os.environ, {"PINJECTED_CONFIG": "{myapp.settings.config}"}, clear=True
        ):
            result = parse_pinjected_env_vars()
            assert result == {"config": "{myapp.settings.config}"}

    def test_parse_pinjected_env_vars_empty_value(self):
        """Test handling of empty values."""
        with patch.dict(os.environ, {"PINJECTED_EMPTY": ""}, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {"empty": ""}

    def test_parse_pinjected_env_vars_skip_non_pinjected(self):
        """Test that non-PINJECTED_ vars are ignored."""
        env_vars = {
            "PINJECTED_VAR1": "value1",
            "OTHER_VAR": "ignored",
            "PINJECTED_VAR2": "value2",
            "PATH": "/usr/bin",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {"var1": "value1", "var2": "value2"}

    def test_parse_pinjected_env_vars_underscore_handling(self):
        """Test handling of underscores in variable names."""
        with patch.dict(os.environ, {"PINJECTED_SNAKE_CASE_VAR": "value"}, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {"snake_case_var": "value"}

    @patch("pinjected.run_helpers.env_var_parser.logger")
    def test_parse_pinjected_env_vars_empty_key_warning(self, mock_logger):
        """Test warning is logged for PINJECTED_ with no suffix."""
        with patch.dict(os.environ, {"PINJECTED_": "value"}, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {}
            mock_logger.warning.assert_called_once_with(
                "Skipping empty key from env var: PINJECTED_"
            )

    def test_parse_pinjected_env_vars_special_characters(self):
        """Test handling of special characters in values."""
        env_vars = {
            "PINJECTED_JSON": '{"key": "value"}',
            "PINJECTED_EQUALS": "key=value",
            "PINJECTED_SPACES": "value with spaces",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {
                "json": '{"key": "value"}',
                "equals": "key=value",
                "spaces": "value with spaces",
            }

    @patch("pinjected.run_helpers.env_var_parser.logger")
    def test_parse_pinjected_env_vars_debug_logging(self, mock_logger):
        """Test debug logging of parsed variables."""
        with patch.dict(os.environ, {"PINJECTED_TEST": "value"}, clear=True):
            result = parse_pinjected_env_vars()
            assert result == {"test": "value"}
            mock_logger.debug.assert_called_once_with(
                "Parsed env var PINJECTED_TEST -> test='value'"
            )
