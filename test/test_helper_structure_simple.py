"""Simple tests for helper_structure.py module to improve coverage."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import is_dataclass
import warnings

from pinjected.helper_structure import (
    IdeaRunConfiguration,
    IdeaRunConfigurations,
    _a_resolve,
    SpecTrace,
    MetaContext,
    RunnablePair,
)
from pinjected import DelegatedVar, Design, EmptyDesign, Injected
from pinjected.di.design_spec.protocols import DesignSpec
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import ModuleVarPath
from pinjected.v2.keys import StrBindKey


class TestIdeaRunConfiguration:
    """Test the IdeaRunConfiguration dataclass."""

    def test_idea_run_configuration_is_dataclass(self):
        """Test that IdeaRunConfiguration is a dataclass."""
        assert is_dataclass(IdeaRunConfiguration)

    def test_idea_run_configuration_creation(self):
        """Test creating IdeaRunConfiguration instance."""
        config = IdeaRunConfiguration(
            name="test_config",
            script_path="/path/to/script.py",
            interpreter_path="/usr/bin/python",
            arguments=["--arg1", "value1"],
            working_dir="/working/dir",
        )

        assert config.name == "test_config"
        assert config.script_path == "/path/to/script.py"
        assert config.interpreter_path == "/usr/bin/python"
        assert config.arguments == ["--arg1", "value1"]
        assert config.working_dir == "/working/dir"


class TestIdeaRunConfigurations:
    """Test the IdeaRunConfigurations dataclass."""

    def test_idea_run_configurations_is_dataclass(self):
        """Test that IdeaRunConfigurations is a dataclass."""
        assert is_dataclass(IdeaRunConfigurations)

    def test_idea_run_configurations_creation(self):
        """Test creating IdeaRunConfigurations instance."""
        config1 = IdeaRunConfiguration(
            name="config1",
            script_path="script1.py",
            interpreter_path="python",
            arguments=[],
            working_dir=".",
        )
        config2 = IdeaRunConfiguration(
            name="config2",
            script_path="script2.py",
            interpreter_path="python3",
            arguments=["--debug"],
            working_dir="./src",
        )

        configs = IdeaRunConfigurations(configs={"test": [config1], "prod": [config2]})

        assert "test" in configs.configs
        assert "prod" in configs.configs
        assert len(configs.configs["test"]) == 1
        assert configs.configs["test"][0].name == "config1"


class TestAResolve:
    """Test the _a_resolve function."""

    @pytest.mark.asyncio
    async def test_a_resolve_with_regular_value(self):
        """Test _a_resolve with regular (non-special) value."""
        result = await _a_resolve("regular_value")
        assert result == "regular_value"

        result = await _a_resolve(42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_a_resolve_with_delegated_var(self):
        """Test _a_resolve with DelegatedVar."""
        mock_var = Mock(spec=DelegatedVar)

        with patch("pinjected.helper_structure.AsyncResolver") as mock_resolver_class:
            mock_resolver = AsyncMock()
            mock_resolver.provide.return_value = "resolved_value"
            mock_resolver_class.return_value = mock_resolver

            result = await _a_resolve(mock_var)

            mock_resolver_class.assert_called_once_with(EmptyDesign)
            mock_resolver.provide.assert_called_once_with(mock_var)
            assert result == "resolved_value"

    @pytest.mark.asyncio
    async def test_a_resolve_with_injected(self):
        """Test _a_resolve with Injected."""
        mock_injected = Mock(spec=Injected)

        with patch("pinjected.helper_structure.AsyncResolver") as mock_resolver_class:
            mock_resolver = AsyncMock()
            mock_resolver.provide.return_value = "injected_result"
            mock_resolver_class.return_value = mock_resolver

            result = await _a_resolve(mock_injected)

            mock_resolver_class.assert_called_once_with(EmptyDesign)
            mock_resolver.provide.assert_called_once_with(mock_injected)
            assert result == "injected_result"


class TestSpecTrace:
    """Test the SpecTrace dataclass."""

    def test_spec_trace_is_dataclass(self):
        """Test that SpecTrace is a dataclass."""
        assert is_dataclass(SpecTrace)

    def test_spec_trace_creation(self):
        """Test creating SpecTrace instance."""
        mock_spec1 = Mock(spec=ModuleVarSpec)
        mock_spec2 = Mock(spec=ModuleVarSpec)
        mock_accumulated = Mock(spec=DesignSpec)

        trace = SpecTrace(trace=[mock_spec1, mock_spec2], accumulated=mock_accumulated)

        assert trace.trace == [mock_spec1, mock_spec2]
        assert trace.accumulated is mock_accumulated

    @pytest.mark.asyncio
    async def test_a_gather_from_path(self):
        """Test a_gather_from_path static method."""
        mock_path = Path("/test/path")

        # Mock the walk_module_with_special_files
        mock_var1 = Mock(spec=ModuleVarSpec)
        mock_var1.var = Mock(spec=DesignSpec)
        mock_var2 = Mock(spec=ModuleVarSpec)
        mock_var2.var = Mock(spec=DesignSpec)

        # Create proper mocks for DesignSpec with __iadd__ for += operation
        mock_spec1 = Mock(spec=DesignSpec)
        mock_spec2 = Mock(spec=DesignSpec)
        # Don't use spec for mock_acc to allow magic method mocking
        mock_acc = Mock()
        mock_acc.__iadd__ = Mock(return_value=mock_acc)

        with patch(
            "pinjected.helper_structure.walk_module_with_special_files"
        ) as mock_walk:
            mock_walk.return_value = [mock_var1, mock_var2]

            with patch("pinjected.helper_structure._a_resolve") as mock_resolve:
                mock_resolve.side_effect = [mock_spec1, mock_spec2]

                with patch.object(DesignSpec, "empty", return_value=mock_acc):
                    result = await SpecTrace.a_gather_from_path(mock_path)

                    assert isinstance(result, SpecTrace)
                    assert len(result.trace) == 2
                    assert result.trace[0] is mock_var1
                    assert result.trace[1] is mock_var2
                    # Check that += was called for each spec
                    assert mock_acc.__iadd__.call_count == 2


class TestMetaContext:
    """Test the MetaContext dataclass."""

    def test_meta_context_is_dataclass(self):
        """Test that MetaContext is a dataclass."""
        assert is_dataclass(MetaContext)

    def test_meta_context_creation(self):
        """Test creating MetaContext instance."""
        mock_trace = [Mock(spec=ModuleVarSpec)]
        mock_design = Mock(spec=Design)
        mock_spec_trace = Mock(spec=SpecTrace)
        key_to_path = {StrBindKey("test"): "/path/to/test"}

        context = MetaContext(
            trace=mock_trace,
            accumulated=mock_design,
            spec_trace=mock_spec_trace,
            key_to_path=key_to_path,
        )

        assert context.trace == mock_trace
        assert context.accumulated is mock_design
        assert context.spec_trace is mock_spec_trace
        assert context.key_to_path == key_to_path

    @pytest.mark.asyncio
    async def test_a_gather_from_path_deprecated(self):
        """Test deprecated a_gather_from_path method."""
        mock_path = Path("/test/path")

        # Create a mock design with bindings
        mock_design = Mock(spec=Design)
        mock_design.bindings = {"key1": "value1"}
        mock_design.__add__ = Mock(return_value=mock_design)

        mock_var = Mock(spec=ModuleVarSpec)
        mock_var.var_path = "/test/path/__meta_design__"
        mock_var.var = mock_design

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with patch("pinjected.helper_structure.walk_module_attr") as mock_walk:
                mock_walk.return_value = [mock_var]

                with patch(
                    "pinjected.helper_structure.AsyncResolver"
                ) as mock_resolver_class:
                    mock_resolver = AsyncMock()
                    mock_resolver.provide_or.return_value = EmptyDesign
                    mock_resolver_class.return_value = mock_resolver

                    with patch("pinjected.helper_structure.logger"):
                        await MetaContext.a_gather_from_path(mock_path)

                        assert len(w) == 1
                        assert issubclass(w[0].category, DeprecationWarning)
                        assert "deprecated" in str(w[0].message)

    @pytest.mark.asyncio
    async def test_a_gather_bindings_with_legacy(self):
        """Test a_gather_bindings_with_legacy method."""
        mock_path = Path("/test/path")

        # Create mock design
        mock_design = Mock(spec=Design)
        mock_design.bindings = {}
        mock_design.__add__ = Mock(return_value=mock_design)

        mock_var = Mock(spec=ModuleVarSpec)
        mock_var.var_path = "/test/path/__design__"
        mock_var.module_file_path = Path("/test/path.py")
        mock_var.var = mock_design

        with patch(
            "pinjected.helper_structure.walk_module_with_special_files"
        ) as mock_walk:
            mock_walk.return_value = [mock_var]

            with patch("pinjected.helper_structure._a_resolve") as mock_resolve:
                mock_resolve.return_value = mock_design

                with patch.object(SpecTrace, "a_gather_from_path") as mock_gather_spec:
                    mock_spec_trace = Mock(spec=SpecTrace)
                    mock_gather_spec.return_value = mock_spec_trace

                    with patch("pinjected.helper_structure.logger"):
                        result = await MetaContext.a_gather_bindings_with_legacy(
                            mock_path
                        )

                        assert isinstance(result, MetaContext)
                        assert result.spec_trace is mock_spec_trace

    @pytest.mark.asyncio
    async def test_a_gather_bindings_with_legacy_meta_design_error(self):
        """Test a_gather_bindings_with_legacy raises error for __meta_design__."""
        mock_path = Path("/test/path")

        mock_var = Mock(spec=ModuleVarSpec)
        mock_var.var_path = "/test/path/__meta_design__"

        with patch(
            "pinjected.helper_structure.walk_module_with_special_files"
        ) as mock_walk:
            mock_walk.return_value = [mock_var]

            with pytest.raises(DeprecationWarning) as exc_info:
                await MetaContext.a_gather_bindings_with_legacy(mock_path)

            assert "__meta_design__" in str(exc_info.value)
            assert "deprecated" in str(exc_info.value)

    def test_gather_from_path_sync(self):
        """Test synchronous gather_from_path method."""
        mock_path = Path("/test/path")

        with patch("asyncio.run") as mock_run:
            mock_context = Mock(spec=MetaContext)
            mock_run.return_value = mock_context

            result = MetaContext.gather_from_path(mock_path)

            assert result is mock_context
            mock_run.assert_called_once()

    def test_final_design_property(self):
        """Test final_design property."""
        mock_design = Mock(spec=Design)

        context = MetaContext(
            trace=[], accumulated=Mock(), spec_trace=Mock(), key_to_path={}
        )

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = mock_design

            result = context.final_design

            assert result is mock_design
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_a_final_design_property(self):
        """Test async a_final_design property."""
        mock_accumulated = Mock(spec=Design)
        mock_accumulated.__add__ = Mock(return_value=mock_accumulated)
        mock_accumulated.__contains__ = Mock(
            return_value=False
        )  # Simulate key not in design

        context = MetaContext(
            trace=[], accumulated=mock_accumulated, spec_trace=Mock(), key_to_path={}
        )

        with (
            patch(
                "pinjected.run_helpers.run_injected.load_user_default_design"
            ) as mock_default,
            patch(
                "pinjected.run_helpers.run_injected.load_user_overrides_design"
            ) as mock_overrides,
        ):
            mock_default.return_value = EmptyDesign
            mock_overrides.return_value = EmptyDesign

            with patch("pinjected.helper_structure.logger"):
                result = await context.a_final_design

                assert result is not None
                # Check that it checked for the deprecated key
                mock_accumulated.__contains__.assert_called_once()

    @pytest.mark.asyncio
    async def test_a_final_design_with_deprecated_default_design_paths(self):
        """Test a_final_design raises error for deprecated default_design_paths."""
        mock_accumulated = Mock(spec=Design)
        mock_accumulated.__contains__ = Mock(return_value=True)

        context = MetaContext(
            trace=[], accumulated=mock_accumulated, spec_trace=Mock(), key_to_path={}
        )

        with patch("pinjected.helper_structure.logger"):
            with pytest.raises(DeprecationWarning) as exc_info:
                await context.a_final_design

            assert "default_design_paths" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_a_load_default_design_for_variable(self):
        """Test a_load_default_design_for_variable static method."""
        # Use an existing module to avoid import errors
        mock_var = ModuleVarPath("pinjected.helper_structure.test_var")
        mock_design = Mock(spec=Design)

        with patch.object(MetaContext, "a_gather_bindings_with_legacy") as mock_gather:
            mock_context = Mock(spec=MetaContext)
            mock_context.a_final_design = AsyncMock(return_value=mock_design)()
            mock_gather.return_value = mock_context

            result = await MetaContext.a_load_default_design_for_variable(mock_var)

            assert result is mock_design

    @pytest.mark.asyncio
    async def test_a_load_default_design_for_variable_with_string(self):
        """Test a_load_default_design_for_variable with string input."""
        var_str = "pinjected.helper_structure.test_var"
        mock_design = Mock(spec=Design)

        with patch.object(MetaContext, "a_gather_bindings_with_legacy") as mock_gather:
            mock_context = Mock(spec=MetaContext)
            mock_context.a_final_design = AsyncMock(return_value=mock_design)()
            mock_gather.return_value = mock_context

            result = await MetaContext.a_load_default_design_for_variable(var_str)

            assert result is mock_design

    def test_load_default_design_for_variable_deprecated(self):
        """Test deprecated load_default_design_for_variable method."""
        var_str = "test.module.var"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with patch("asyncio.run") as mock_run:
                mock_design = Mock(spec=Design)
                mock_run.return_value = mock_design

                result = MetaContext.load_default_design_for_variable(var_str)

                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message)
                assert result is mock_design

    @pytest.mark.asyncio
    async def test_a_design_for_variable(self):
        """Test a_design_for_variable static method."""
        mock_var = ModuleVarPath("pinjected.helper_structure.test_var")
        mock_design = Mock(spec=Design)

        with patch.object(MetaContext, "a_gather_bindings_with_legacy") as mock_gather:
            mock_context = Mock(spec=MetaContext)
            mock_context.a_final_design = AsyncMock(return_value=mock_design)()
            mock_gather.return_value = mock_context

            result = await MetaContext.a_design_for_variable(mock_var)

            assert result is mock_design


class TestRunnablePair:
    """Test the RunnablePair dataclass."""

    def test_runnable_pair_is_dataclass(self):
        """Test that RunnablePair is a dataclass."""
        assert is_dataclass(RunnablePair)

    def test_runnable_pair_creation(self):
        """Test creating RunnablePair instance."""
        mock_injected = Mock(spec=Injected)
        mock_design = Mock(spec=Design)

        pair = RunnablePair(target=mock_injected, design=mock_design)

        assert pair.target is mock_injected
        assert pair.design is mock_design

    def test_run(self):
        """Test run method."""
        mock_injected = Mock(spec=Injected)
        mock_design = Mock(spec=Design)
        mock_graph = {mock_injected: "result_value"}
        mock_design.to_graph.return_value = mock_graph

        pair = RunnablePair(target=mock_injected, design=mock_design)

        with patch("pinjected.helper_structure.logger"):
            result = pair.run()

            assert result == "result_value"
            mock_design.to_graph.assert_called_once()

    def test_save_html_with_default_name(self):
        """Test save_html method with default name."""
        mock_injected = Mock(spec=Injected)
        mock_design = Mock()  # Don't use spec since to_vis_graph not in Design spec
        mock_vis_graph = Mock()
        mock_design.to_vis_graph.return_value = mock_vis_graph

        pair = RunnablePair(target=mock_injected, design=mock_design)

        pair.save_html()

        mock_design.to_vis_graph.assert_called_once()
        mock_vis_graph.save_as_html.assert_called_once_with(
            mock_injected, "graph.html", show=True
        )

    def test_save_html_with_custom_name(self):
        """Test save_html method with custom name."""
        mock_injected = Mock(spec=Injected)
        mock_design = Mock()  # Don't use spec since to_vis_graph not in Design spec
        mock_vis_graph = Mock()
        mock_design.to_vis_graph.return_value = mock_vis_graph

        pair = RunnablePair(target=mock_injected, design=mock_design)

        pair.save_html("custom.html", show=False)

        mock_design.to_vis_graph.assert_called_once()
        mock_vis_graph.save_as_html.assert_called_once_with(
            mock_injected, "custom.html", show=False
        )


class TestModuleGlobals:
    """Test module-level globals."""

    def test_design_global(self):
        """Test __design__ global is defined."""
        from pinjected.helper_structure import __design__

        assert isinstance(__design__, Design)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
