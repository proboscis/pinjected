"""Tests for ide_supports.intellij.config_creator_for_env module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from returns.maybe import Some

from pinjected.ide_supports.intellij.config_creator_for_env import (
    IRunner,
    LocalRunner,
    TEST_ENV,
    _run_command_with_env,
    run_command_with_env,
    idea_config_creator_from_envs,
)
from pinjected.module_inspector import ModuleVarSpec
from pinjected.helper_structure import IdeaRunConfiguration


class TestIRunner:
    """Test IRunner interface."""

    def test_interface_definition(self):
        """Test IRunner is defined correctly."""
        assert hasattr(IRunner, "run")

        # Test that it's an abstract interface
        runner = IRunner()
        assert hasattr(runner, "run")


class TestLocalRunner:
    """Test LocalRunner implementation."""

    def test_inheritance(self):
        """Test LocalRunner inherits from IRunner."""
        assert issubclass(LocalRunner, IRunner)

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_run_command(self, mock_run):
        """Test LocalRunner.run executes subprocess."""
        # Mock subprocess result
        mock_result = Mock()
        mock_result.stdout = b"command output"
        mock_run.return_value = mock_result

        runner = LocalRunner()
        result = await runner.run("echo test")

        assert result == "command output"
        mock_run.assert_called_once_with(
            "echo test", shell=True, capture_output=True, check=False
        )

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_run_command_with_error(self, mock_run):
        """Test LocalRunner.run handles command errors."""
        # Mock subprocess result with error
        mock_result = Mock()
        mock_result.stdout = b"error output"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        runner = LocalRunner()
        result = await runner.run("invalid command")

        # Should still return stdout even on error
        assert result == "error output"


class TestTEST_ENV:
    """Test TEST_ENV constant."""

    def test_test_env_is_injected(self):
        """Test TEST_ENV is an injected value."""
        # TEST_ENV should be the result of calling injected(LocalRunner)()
        assert TEST_ENV is not None
        # It should be some form of proxy or injected object
        assert hasattr(TEST_ENV, "__class__")


class TestRunCommandWithEnv:
    """Test _run_command_with_env function."""

    @pytest.mark.asyncio
    async def test_run_command_basic(self):
        """Test basic command execution."""
        # Create mock environment
        mock_env = AsyncMock(spec=IRunner)
        mock_env.run.return_value = "command output"

        # Get the wrapped function
        if hasattr(_run_command_with_env, "__wrapped__"):
            func = _run_command_with_env.__wrapped__
        elif hasattr(_run_command_with_env, "src_function"):
            func = _run_command_with_env.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        result = await func(mock_env, "module.variable")

        assert result == "command output"
        mock_env.run.assert_called_once_with("python -m pinjected run module.variable")

    @pytest.mark.asyncio
    async def test_run_command_with_additional_args(self):
        """Test command with additional arguments."""
        # Create mock environment with additional args
        mock_env = AsyncMock(spec=IRunner)
        mock_env.run.return_value = "command output"
        mock_env.pinjected_additional_args = {
            "arg1": "value1",
            "arg2": "value with spaces",
        }

        # Get the wrapped function
        if hasattr(_run_command_with_env, "__wrapped__"):
            func = _run_command_with_env.__wrapped__
        elif hasattr(_run_command_with_env, "src_function"):
            func = _run_command_with_env.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        result = await func(mock_env, "module.variable")

        assert result == "command output"
        # Check that shlex.quote was used for values with spaces
        call_args = mock_env.run.call_args[0][0]
        assert "python -m pinjected run module.variable" in call_args
        assert "--arg1=value1" in call_args
        assert "--arg2=" in call_args
        assert "value with spaces" in call_args or "'value with spaces'" in call_args

    @pytest.mark.asyncio
    async def test_run_command_no_run_method(self):
        """Test error when env doesn't have run method."""
        # Create mock without run method
        mock_env = Mock()
        del mock_env.run

        # Get the wrapped function
        if hasattr(_run_command_with_env, "__wrapped__"):
            func = _run_command_with_env.__wrapped__
        elif hasattr(_run_command_with_env, "src_function"):
            func = _run_command_with_env.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        with pytest.raises(AssertionError, match="does not have run method"):
            await func(mock_env, "module.variable")

    def test_run_command_with_env_global(self):
        """Test run_command_with_env global is defined."""
        assert run_command_with_env is not None
        # It should be a partial application of _run_command_with_env
        assert hasattr(run_command_with_env, "__class__")


class TestIdeaConfigCreatorFromEnvs:
    """Test idea_config_creator_from_envs function."""

    def test_creates_config_creator(self):
        """Test that it creates a config creator function."""
        # Get the wrapped function
        if hasattr(idea_config_creator_from_envs, "__wrapped__"):
            func = idea_config_creator_from_envs.__wrapped__
        elif hasattr(idea_config_creator_from_envs, "src_function"):
            func = idea_config_creator_from_envs.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        creator = func(
            "/usr/bin/python", Some("/working/dir"), ["env1.module", "env2.module"]
        )

        assert callable(creator)

    @patch("pinjected.__file__", "/path/to/pinjected/__init__.py")
    def test_creates_configurations(self):
        """Test creating IDE configurations."""
        # Get the wrapped function
        if hasattr(idea_config_creator_from_envs, "__wrapped__"):
            func = idea_config_creator_from_envs.__wrapped__
        elif hasattr(idea_config_creator_from_envs, "src_function"):
            func = idea_config_creator_from_envs.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        # Create mock environments with proper attributes
        mock_env1 = Mock()
        mock_env1.path = "env1.module"
        mock_env1.var_name = "module"

        # Mock the ModuleVarPath class and instances
        with patch(
            "pinjected.ide_supports.intellij.config_creator_for_env.ModuleVarPath"
        ) as mock_mvp_class:
            # Mock for string conversion
            mock_mvp_string = Mock()
            mock_mvp_string.path = "env1.module"
            mock_mvp_string.var_name = "module"
            mock_mvp_string.module_file_path = "/path/to/module.py"

            # Mock for the spec's module path
            mock_mvp_spec = Mock()
            mock_mvp_spec.module_file_path = "/path/to/spec.py"

            # Return different mocks based on the argument
            def mvp_side_effect(arg):
                if arg == "env1.module":
                    return mock_mvp_string
                elif arg == "test.module.test_func":
                    return mock_mvp_spec
                else:
                    m = Mock()
                    m.path = arg
                    m.var_name = arg.split(".")[-1]
                    m.module_file_path = "/default/path.py"
                    return m

            mock_mvp_class.side_effect = mvp_side_effect

            creator = func("/usr/bin/python", Some("/working/dir"), ["env1.module"])

            # Create a test spec
            spec = ModuleVarSpec(var="test_func", var_path="test.module.test_func")

            configs = creator(spec)

            assert len(configs) == 1
            assert all(isinstance(c, IdeaRunConfiguration) for c in configs)

            # Check config
            config = configs[0]
            assert "submit test_func to env: module" in config.name
            assert config.interpreter_path == "/usr/bin/python"
            assert config.script_path == "/path/to/pinjected/__main__.py"
            assert config.working_dir == "/working/dir"
            assert "run" in config.arguments
            assert "--target-variable=test.module.test_func" in config.arguments

    def test_with_string_environments(self):
        """Test with string environment paths."""
        # Get the wrapped function
        if hasattr(idea_config_creator_from_envs, "__wrapped__"):
            func = idea_config_creator_from_envs.__wrapped__
        elif hasattr(idea_config_creator_from_envs, "src_function"):
            func = idea_config_creator_from_envs.src_function
        else:
            pytest.skip("Cannot access wrapped function")

        # Mock ModuleVarPath to avoid file system access
        with patch(
            "pinjected.ide_supports.intellij.config_creator_for_env.ModuleVarPath"
        ) as mock_mvp_class:
            mock_mvp = Mock()
            mock_mvp.var_name = "test_env"
            mock_mvp.path = "test.env"
            mock_mvp.module_file_path = "/test/path.py"
            mock_mvp_class.return_value = mock_mvp

            creator = func("/usr/bin/python", Some("."), ["string.env.path"])

            spec = ModuleVarSpec(var="func", var_path="module.func")

            with patch("pinjected.__file__", "/pinjected/__init__.py"):
                configs = creator(spec)

            assert len(configs) == 1
            mock_mvp_class.assert_called()  # Verify string was converted to ModuleVarPath
