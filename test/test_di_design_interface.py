"""Tests for pinjected/di/design_interface.py module."""

import pytest
from unittest.mock import Mock, patch, call

from returns.maybe import Some

from pinjected.di.design_interface import (
    Design,
    DesignOverridesStore,
    DesignOverrideContext,
    DESIGN_OVERRIDES_STORE,
)
from pinjected.di.proxiable import DelegatedVar
from pinjected.module_var_path import ModuleVarPath
from pinjected.v2.keys import StrBindKey, IBindKey
from pinjected.v2.binds import IBind


class ConcreteDesign(Design):
    """Concrete implementation for testing abstract Design class."""

    def __init__(self, bindings=None):
        self._bindings = bindings or {}
        self._children = []

    def __contains__(self, item: IBindKey):
        return item in self._bindings

    def __getitem__(self, item: IBindKey | str) -> IBind:
        if isinstance(item, str):
            item = StrBindKey(item)
        return self._bindings[item]

    @property
    def bindings(self) -> dict[IBindKey, IBind]:
        return self._bindings

    @property
    def children(self):
        return self._children


class TestDesignInterface:
    """Tests for Design abstract base class."""

    def test_add_operator(self):
        """Test __add__ creates MergedDesign."""
        design1 = ConcreteDesign()
        design2 = ConcreteDesign()

        result = design1 + design2

        # Should return a MergedDesign instance
        assert hasattr(result, "srcs")
        assert result.srcs == [design1, design2]

    def test_purify(self):
        """Test purify method."""
        mock_bind = Mock(spec=IBind)
        design = ConcreteDesign({StrBindKey("test"): mock_bind})

        with patch(
            "pinjected.di.design_interface.DependencyResolver"
        ) as mock_resolver_class:
            mock_resolver = Mock()
            mock_purified = Mock()

            # Set up chain of mocks
            mock_purified.unbind = Mock(return_value=mock_purified)
            mock_resolver.purified_design.return_value = mock_purified
            mock_resolver_class.return_value = mock_resolver

            design.purify("target")

            # Verify resolver was created with design
            mock_resolver_class.assert_called_once_with(design)
            mock_resolver.purified_design.assert_called_once_with("target")

            # Verify unbind was called for each key
            assert mock_purified.unbind.call_count == 4
            expected_calls = [
                call(StrBindKey("__resolver__")),
                call(StrBindKey("session")),
                call(StrBindKey("__design__")),
                call(StrBindKey("__task_group__")),
            ]
            mock_purified.unbind.assert_has_calls(expected_calls)

    def test_context_manager(self):
        """Test __enter__ and __exit__ context manager methods."""
        design = ConcreteDesign()

        # Mock the frame
        mock_frame = Mock(spec=["f_back"])

        with patch("inspect.currentframe") as mock_currentframe:
            mock_currentframe.return_value = Mock(f_back=mock_frame)

            # Test __enter__
            with patch.object(DESIGN_OVERRIDES_STORE, "add") as mock_add:
                result = design.__enter__()

                assert result is design
                mock_add.assert_called_once_with(mock_frame, design)

            # Test __exit__
            with patch.object(DESIGN_OVERRIDES_STORE, "pop") as mock_pop:
                design.__exit__(None, None, None)

                mock_pop.assert_called_once_with(mock_frame)

    def test_from_bindings_static_method(self):
        """Test from_bindings static method."""
        bindings = {StrBindKey("test"): Mock(spec=IBind)}

        result = Design.from_bindings(bindings)

        assert hasattr(result, "_bindings")
        assert result._bindings == bindings

    def test_empty_static_method(self):
        """Test empty static method."""
        result = Design.empty()

        assert hasattr(result, "_bindings")
        assert len(result._bindings) == 0

    def test_dfs_design(self):
        """Test dfs_design generator method."""
        # Create parent with children
        parent = ConcreteDesign()
        child1 = ConcreteDesign()
        child2 = ConcreteDesign()
        grandchild = ConcreteDesign()

        parent._children = [child1, child2]
        child1._children = [grandchild]

        # Collect all designs from DFS
        designs = list(parent.dfs_design())

        assert len(designs) == 4
        assert designs[0] is parent
        assert designs[1] is child1
        assert designs[2] is grandchild
        assert designs[3] is child2

    def test_keys(self):
        """Test keys method."""
        key1 = StrBindKey("key1")
        key2 = StrBindKey("key2")
        bindings = {key1: Mock(), key2: Mock()}
        design = ConcreteDesign(bindings)

        keys = design.keys()

        assert set(keys) == {key1, key2}

    @patch("pinjected.pinjected_logging.logger")
    def test_provide_deprecated(self, mock_logger):
        """Test provide method (deprecated)."""
        mock_bind = Mock()
        design = ConcreteDesign({StrBindKey("test"): mock_bind})

        with patch("pinjected.v2.async_resolver.AsyncResolver") as mock_resolver_class:
            mock_resolver = Mock()
            mock_blocking = Mock()
            mock_blocking.provide.return_value = "result"
            mock_resolver.to_blocking.return_value = mock_blocking
            mock_resolver_class.return_value = mock_resolver

            # Test with string key
            result = design.provide("test")

            assert result == "result"
            mock_logger.warning.assert_called_once()
            assert "deprecated" in mock_logger.warning.call_args[0][0]
            mock_resolver_class.assert_called_once_with(design)
            mock_blocking.provide.assert_called_once_with(StrBindKey("test"))

    def test_provide_with_default(self):
        """Test provide with default value."""
        design = ConcreteDesign({})  # Empty bindings

        with patch("pinjected.v2.async_resolver.AsyncResolver"):
            # Test with default
            result = design.provide("missing_key", Some("default_value"))

            assert result == "default_value"

    @patch("pinjected.pinjected_logging.logger")
    def test_to_graph_deprecated(self, mock_logger):
        """Test to_graph method (deprecated)."""
        design = ConcreteDesign()

        with patch("pinjected.v2.async_resolver.AsyncResolver") as mock_resolver_class:
            mock_resolver = Mock()
            mock_blocking = Mock()
            mock_resolver.to_blocking.return_value = mock_blocking
            mock_resolver_class.return_value = mock_resolver

            result = design.to_graph()

            assert result is mock_blocking
            mock_logger.warning.assert_called_once()
            assert "deprecated" in mock_logger.warning.call_args[0][0]

    def test_diff(self):
        """Test diff method."""
        bindings1 = {StrBindKey("key1"): Mock(), StrBindKey("key2"): Mock()}
        bindings2 = {StrBindKey("key1"): Mock(), StrBindKey("key3"): Mock()}

        design1 = ConcreteDesign(bindings1)
        design2 = ConcreteDesign(bindings2)

        with patch("pinjected.di.util.get_dict_diff") as mock_diff:
            mock_diff.return_value = [("key2", "val1", "val2")]

            result = design1.diff(design2)

            assert result == [("key2", "val1", "val2")]
            mock_diff.assert_called_once_with(bindings1, bindings2)

    @patch("pinjected.pinjected_logging.logger")
    def test_inspect_picklability(self, mock_logger):
        """Test inspect_picklability method."""
        design = ConcreteDesign({StrBindKey("test"): Mock()})

        with patch("pinjected.di.util.check_picklable") as mock_check:
            design.inspect_picklability()

            mock_logger.info.assert_called_once()
            mock_check.assert_called_once_with(design.bindings)


class TestDesignOverridesStore:
    """Tests for DesignOverridesStore class."""

    def test_initialization(self):
        """Test DesignOverridesStore initialization."""
        store = DesignOverridesStore()

        assert store.bindings == {}
        assert store.stack == []

    def test_add(self):
        """Test add method."""
        store = DesignOverridesStore()
        # Create a mock frame with f_globals attribute
        mock_frame = Mock()
        mock_frame.f_globals = {"test_var": "test_value"}
        mock_design = Mock(spec=Design)

        store.add(mock_frame, mock_design)

        assert len(store.stack) == 1
        context = store.stack[0]
        assert context.src is mock_design
        assert context.init_frame is mock_frame

    def test_pop_empty_stack(self):
        """Test pop method with empty target vars."""
        store = DesignOverridesStore()
        mock_frame = Mock()
        mock_frame.f_globals = {"test_var": "test_value"}
        mock_design = Mock(spec=Design)

        # Add a context
        store.add(mock_frame, mock_design)

        # Mock the context exit to return empty list
        with patch.object(store.stack[0], "exit", return_value=[]):
            store.pop(mock_frame)

        assert len(store.stack) == 0
        assert len(store.bindings) == 0

    def test_pop_with_target_vars(self):
        """Test pop method with target variables."""
        store = DesignOverridesStore()
        mock_frame = Mock()
        mock_frame.f_globals = {"test_var": "test_value"}
        mock_design = ConcreteDesign()

        # Add a context
        store.add(mock_frame, mock_design)

        # Mock module var paths
        mvp1 = ModuleVarPath("module.var1")
        mvp2 = ModuleVarPath("module.var2")

        # Mock the context exit to return module var paths
        with patch.object(store.stack[0], "exit", return_value=[mvp1, mvp2]):
            store.pop(mock_frame)

        assert len(store.stack) == 0
        assert mvp1 in store.bindings
        assert mvp2 in store.bindings
        assert isinstance(store.bindings[mvp1], Design)

    def test_pop_with_existing_binding(self):
        """Test pop doesn't override existing bindings."""
        store = DesignOverridesStore()
        mock_frame = Mock()
        mock_frame.f_globals = {"test_var": "test_value"}
        mock_design = ConcreteDesign()

        # Pre-populate with existing binding
        mvp = ModuleVarPath("module.var")
        existing_design = ConcreteDesign()
        store.bindings[mvp] = existing_design

        # Add a context
        store.add(mock_frame, mock_design)

        # Mock the context exit
        with patch.object(store.stack[0], "exit", return_value=[mvp]):
            store.pop(mock_frame)

        # Should not override
        assert store.bindings[mvp] is existing_design

    def test_get_overrides(self):
        """Test get_overrides method."""
        store = DesignOverridesStore()

        # Test with no override
        mvp1 = ModuleVarPath("module.var1")
        result = store.get_overrides(mvp1)
        assert hasattr(result, "bindings")  # Should be empty design
        assert len(result.bindings) == 0

        # Test with override
        mvp2 = ModuleVarPath("module.var2")
        mock_design = Mock(spec=Design)
        store.bindings[mvp2] = mock_design

        result = store.get_overrides(mvp2)
        assert result is mock_design


class TestDesignOverrideContext:
    """Tests for DesignOverrideContext class."""

    def test_initialization(self):
        """Test DesignOverrideContext initialization."""
        mock_design = Mock(spec=Design)
        mock_frame = Mock()
        mock_frame.f_globals = {"test_var": "test_value"}
        mock_frame.f_globals = {"var1": "value1", "var2": "value2"}

        context = DesignOverrideContext(mock_design, mock_frame)

        assert context.src is mock_design
        assert context.init_frame is mock_frame
        assert context.last_global_ids == {"var1": id("value1"), "var2": id("value2")}

    def test_exit_no_changes(self):
        """Test exit with no global changes."""
        mock_design = Mock(spec=Design)
        mock_frame = Mock()
        mock_frame.f_globals = {"test_var": "test_value"}
        globals_dict = {"var1": "value1", "__name__": "test_module"}
        mock_frame.f_globals = globals_dict

        context = DesignOverrideContext(mock_design, mock_frame)

        # Exit with same frame (no changes)
        result = context.exit(mock_frame)

        assert result == []

    def test_exit_with_new_vars(self):
        """Test exit with new global variables."""
        mock_design = Mock(spec=Design)
        init_frame = Mock()
        init_frame.f_globals = {"test_var": "test_value"}
        init_frame.f_globals = {"var1": "value1", "__name__": "test_module"}

        context = DesignOverrideContext(mock_design, init_frame)

        # Create exit frame with new variables
        exit_frame = Mock()
        exit_frame.f_globals = {"test_var": "test_value"}
        mock_delegated = Mock(spec=DelegatedVar)
        exit_globals = {
            "var1": "value1",
            "new_var": mock_delegated,
            "__name__": "test_module",
        }
        exit_frame.f_globals = exit_globals

        result = context.exit(exit_frame)

        assert len(result) == 1
        assert result[0].path == "test_module.new_var"

    def test_exit_with_changed_vars(self):
        """Test exit with changed global variables."""
        mock_design = Mock(spec=Design)
        value1 = "initial"
        init_frame = Mock()
        init_frame.f_globals = {"test_var": "test_value"}
        init_frame.f_globals = {"var1": value1, "__name__": "test_module"}

        context = DesignOverrideContext(mock_design, init_frame)

        # Create exit frame with changed variable
        exit_frame = Mock()
        exit_frame.f_globals = {"test_var": "test_value"}

        # Import the actual Injected class
        from pinjected.di.injected import InjectedPure

        # Create a real Injected instance instead of mocking
        injected_value = InjectedPure("new_value")

        exit_globals = {
            "var1": injected_value,  # Changed to real Injected
            "__name__": "test_module",
        }
        exit_frame.f_globals = exit_globals

        result = context.exit(exit_frame)

        assert len(result) == 1
        assert result[0].path == "test_module.var1"

    def test_exit_filters_non_delegated_changes(self):
        """Test exit only tracks DelegatedVar and Injected changes."""
        mock_design = Mock(spec=Design)
        init_frame = Mock()
        init_frame.f_globals = {"test_var": "test_value"}
        init_frame.f_globals = {"var1": "value1", "__name__": "test_module"}

        context = DesignOverrideContext(mock_design, init_frame)

        # Create exit frame with various changes
        exit_frame = Mock()
        exit_frame.f_globals = {"test_var": "test_value"}
        exit_globals = {
            "var1": "changed_value",  # Changed but not DelegatedVar/Injected
            "var2": Mock(spec=DelegatedVar),  # New DelegatedVar
            "var3": "new_regular",  # New but not DelegatedVar/Injected
            "__name__": "test_module",
        }
        exit_frame.f_globals = exit_globals

        result = context.exit(exit_frame)

        # Should only track var2
        assert len(result) == 1
        assert result[0].path == "test_module.var2"


class TestGlobalDesignOverridesStore:
    """Tests for the global DESIGN_OVERRIDES_STORE."""

    def test_global_store_exists(self):
        """Test that global store is initialized."""
        assert isinstance(DESIGN_OVERRIDES_STORE, DesignOverridesStore)
        assert hasattr(DESIGN_OVERRIDES_STORE, "bindings")
        assert hasattr(DESIGN_OVERRIDES_STORE, "stack")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
