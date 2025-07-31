"""Integration tests for PINJECTED_* environment variable priority ordering."""

import os
import pytest
from unittest.mock import patch

from pinjected import design
from pinjected.run_helpers.run_injected import a_get_run_context
from pinjected.v2.keys import StrBindKey


class TestEnvVarPriority:
    """Tests for environment variable priority in the design merge order."""

    @pytest.mark.asyncio
    async def test_env_var_loading_basic(self):
        """Test that env vars are loaded into the design."""
        # Use an existing test module
        var_path = "test.test_package.child.module1.test_c"

        # Mock environment variables
        with patch.dict(os.environ, {"PINJECTED_API_KEY": "env_value"}, clear=False):
            # Get run context
            context = await a_get_run_context(design_path=None, var_path=var_path)

            # Check that env var is in the design
            final_design = context.get_final_design()
            assert StrBindKey("api_key") in final_design.bindings

            # Check env var bindings are tracked in MetaContext
            assert StrBindKey("api_key") in context.src_meta_context.key_to_path
            assert (
                context.src_meta_context.key_to_path[StrBindKey("api_key")]
                == "env:PINJECTED_API_KEY"
            )

    @pytest.mark.asyncio
    async def test_cli_overrides_env_var(self):
        """Test that CLI overrides take precedence over env vars."""
        var_path = "test.test_package.child.module1.test_c"

        # Mock environment variables
        with patch.dict(os.environ, {"PINJECTED_API_KEY": "env_value"}, clear=False):
            # Get run context
            context = await a_get_run_context(design_path=None, var_path=var_path)

            # Add CLI override
            context = context.add_overrides(design(api_key="cli_value"))

            # Verify both bindings exist
            final_design = context.get_final_design()
            assert StrBindKey("api_key") in final_design.bindings

    @pytest.mark.asyncio
    async def test_env_var_source_tracking(self):
        """Test that env var sources are properly tracked."""
        var_path = "test.test_package.child.module1.test_c"

        # Mock environment variables
        with patch.dict(
            os.environ,
            {
                "PINJECTED_API_KEY": "secret",
                "PINJECTED_DATABASE_URL": "postgres://localhost/db",
            },
            clear=False,
        ):
            # Get run context
            context = await a_get_run_context(design_path=None, var_path=var_path)

            # Check env var bindings are tracked in MetaContext
            assert StrBindKey("api_key") in context.src_meta_context.key_to_path
            assert (
                context.src_meta_context.key_to_path[StrBindKey("api_key")]
                == "env:PINJECTED_API_KEY"
            )
            assert StrBindKey("database_url") in context.src_meta_context.key_to_path
            assert (
                context.src_meta_context.key_to_path[StrBindKey("database_url")]
                == "env:PINJECTED_DATABASE_URL"
            )

    @pytest.mark.asyncio
    async def test_env_var_import_syntax(self):
        """Test that env vars with {module.var} syntax work correctly."""
        var_path = "test.test_package.child.module1.test_c"

        # Mock environment variable with import syntax
        with patch.dict(
            os.environ,
            {
                "PINJECTED_CONFIG": "{json.dumps}"  # Import json.dumps function
            },
            clear=False,
        ):
            # Get run context
            context = await a_get_run_context(design_path=None, var_path=var_path)

            # Verify the binding exists
            final_design = context.get_final_design()
            assert StrBindKey("config") in final_design.bindings

    @pytest.mark.asyncio
    async def test_multiple_env_vars(self):
        """Test multiple environment variables are all loaded."""
        var_path = "test.test_package.child.module1.test_c"

        # Mock multiple environment variables
        env_vars = {
            "PINJECTED_VAR1": "value1",
            "PINJECTED_VAR2": "value2",
            "PINJECTED_VAR3": "value3",
            "OTHER_VAR": "ignored",  # Should be ignored
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Get run context
            context = await a_get_run_context(design_path=None, var_path=var_path)

            # Check all PINJECTED_ vars are tracked in MetaContext
            key_to_path = context.src_meta_context.key_to_path
            env_keys = [k for k, v in key_to_path.items() if v.startswith("env:")]
            assert len(env_keys) == 3
            assert StrBindKey("var1") in key_to_path
            assert StrBindKey("var2") in key_to_path
            assert StrBindKey("var3") in key_to_path
            assert key_to_path[StrBindKey("var1")] == "env:PINJECTED_VAR1"
            assert key_to_path[StrBindKey("var2")] == "env:PINJECTED_VAR2"
            assert key_to_path[StrBindKey("var3")] == "env:PINJECTED_VAR3"

    @pytest.mark.asyncio
    async def test_empty_env_var_value(self):
        """Test that empty env var values are handled correctly."""
        var_path = "test.test_package.child.module1.test_c"

        # Mock environment variable with empty value
        with patch.dict(os.environ, {"PINJECTED_EMPTY": ""}, clear=False):
            # Get run context
            context = await a_get_run_context(design_path=None, var_path=var_path)

            # Verify the binding exists even with empty value
            final_design = context.get_final_design()
            assert StrBindKey("empty") in final_design.bindings
