"""Tests for cli_visualizations/tree.py to improve coverage."""

import pytest
from unittest.mock import Mock, patch
from pinjected.cli_visualizations.tree import (
    format_path_for_display,
    get_binding_location_info,
    format_injected_for_tree,
    design_rich_tree,
)
from pinjected.di.injected import InjectedByName, InjectedPure


def test_format_path_for_display():
    """Test format_path_for_display function."""
    # Test short path (should not be truncated)
    assert format_path_for_display("module/file.py") == "module/file.py"

    # Test long path (should be truncated)
    long_path = "very/long/path/to/module/file.py"
    result = format_path_for_display(long_path, max_length=20)
    assert result == ".../to/module/file.py"

    # Test path with empty parts (only processes if > max_length)
    # Short paths are returned as-is
    assert format_path_for_display("//module//file//") == "//module//file//"

    # Test exactly 3 parts
    assert format_path_for_display("one/two/three.py") == "one/two/three.py"

    # Test empty path
    assert format_path_for_display("") == ""

    # Test path at exact max length
    path = "a" * 50
    assert format_path_for_display(path, max_length=50) == path


def test_get_binding_location_info():
    """Test get_binding_location_info function."""
    # Create a mock DIGraph
    mock_graph = Mock()

    # Test with metadata containing frame info
    # The function expects returns.maybe types
    from returns.maybe import Some
    from pinjected.di.metadata.location_data import ModuleVarLocation
    from pathlib import Path

    mock_metadata = Mock()
    mock_metadata.code_location = Some(ModuleVarLocation(Path("test.py"), 42, 0))
    mock_graph.get_metadata.return_value = Some(mock_metadata)

    result = get_binding_location_info(mock_graph, "test_node")
    assert "test.py:42" in result

    # Test with no location info
    from returns.maybe import Nothing

    mock_metadata.code_location = Nothing
    mock_graph.get_metadata.return_value = Some(mock_metadata)
    result = get_binding_location_info(mock_graph, "test_node")
    assert result == ""

    # Test with no metadata
    mock_graph.get_metadata.return_value = Nothing
    result = get_binding_location_info(mock_graph, "test_node")
    assert result == ""

    # Test with binding_sources fallback
    binding_sources = {"test_node": "module.py:100"}
    result = get_binding_location_info(mock_graph, "test_node", binding_sources)
    assert result == " [from module.py:100]"


def test_format_injected_for_tree():
    """Test format_injected_for_tree function."""
    # Test with InjectedByName
    injected = InjectedByName("test_var")
    result = format_injected_for_tree(injected)
    assert result == "ByName(test_var)"

    # Test with InjectedPure
    injected_pure = InjectedPure(42)
    result = format_injected_for_tree(injected_pure)
    assert result == "42"  # For non-string/type/callable values, it returns str(value)

    # Test with PartialInjectedFunction
    from pinjected.di.injected import PartialInjectedFunction

    partial = Mock(spec=PartialInjectedFunction)
    result = format_injected_for_tree(partial)
    assert result == "Partial"


@patch("pinjected.cli_visualizations.tree.Tree")
@patch("rich.console.Console")
@patch("pinjected.cli_visualizations.tree.DIGraph")
def test_design_rich_tree(mock_digraph_class, mock_console_class, mock_tree_class):
    """Test design_rich_tree function."""
    # Create mock DIGraph instance
    mock_graph = Mock()
    mock_digraph_class.return_value = mock_graph

    # Mock create_dependency_digraph_rooted to return a proper structure
    mock_dep_graph = Mock()
    mock_dep_graph.graph = Mock()
    mock_dep_graph.graph.edges = []  # Empty edges for simplicity
    mock_graph.create_dependency_digraph_rooted.return_value = mock_dep_graph

    # Mock metadata
    mock_graph.get_metadata.return_value = None

    # Mock __getitem__ for d[node] access
    mock_graph.__getitem__ = Mock(return_value="value")

    # Mock Tree
    mock_tree = Mock()
    mock_tree_class.return_value = mock_tree

    # Mock Console
    mock_console = Mock()
    mock_console.file = Mock()
    mock_console.file.getvalue.return_value = "tree output"
    mock_console_class.return_value = mock_console

    # Create a real design that supports + operator
    from pinjected import design

    test_design = design()

    # Call the function
    result = design_rich_tree(test_design, "root")

    # Verify DIGraph was created
    assert mock_digraph_class.called

    # Verify create_dependency_digraph_rooted was called
    mock_graph.create_dependency_digraph_rooted.assert_called_once_with("root")

    # Verify Tree was created
    assert mock_tree_class.called

    # Should return the tree output
    assert result == "tree output"


def test_design_rich_tree_with_binding_sources():
    """Test design_rich_tree with binding sources."""
    with (
        patch("pinjected.cli_visualizations.tree.DIGraph") as mock_digraph_class,
        patch("rich.console.Console") as mock_console_class,
        patch("pinjected.cli_visualizations.tree.Tree") as mock_tree_class,
    ):
        mock_graph = Mock()
        mock_digraph_class.return_value = mock_graph

        # Mock create_dependency_digraph_rooted
        mock_dep_graph = Mock()
        mock_dep_graph.graph = Mock()
        mock_dep_graph.graph.edges = []  # Empty edges
        mock_graph.create_dependency_digraph_rooted.return_value = mock_dep_graph

        mock_graph.get_metadata.return_value = None
        mock_graph.__getitem__ = Mock(return_value="value")

        # Mock Console
        mock_console = Mock()
        mock_console.file = Mock()
        mock_console.file.getvalue.return_value = "tree output"
        mock_console_class.return_value = mock_console

        # Mock Tree
        mock_tree = Mock()
        mock_tree_class.return_value = mock_tree

        from pinjected import design

        test_design = design()
        binding_sources = {"test": "source.py:10"}

        # Call with binding sources
        result = design_rich_tree(test_design, "test", binding_sources=binding_sources)

        # The function should work with binding sources
        mock_digraph_class.assert_called_once()
        assert result == "tree output"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
