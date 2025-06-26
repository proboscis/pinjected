"""Test that binding metadata is displayed in dependency trees"""

from pathlib import Path

from returns.maybe import Some

from pinjected import design
from pinjected.cli_visualizations.tree import (
    design_rich_tree,
    format_path_for_display,
    get_binding_location_info,
)
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.metadata.location_data import ModuleVarLocation, ModuleVarPath
from pinjected.di.injected import InjectedPure
from pinjected.visualize_di import DIGraph


def test_format_path_for_display():
    """Test the path formatting helper function"""
    # Short paths should not be changed
    assert format_path_for_display("/app/config.py") == "/app/config.py"

    # Long paths should be shortened
    long_path = (
        "/very/long/path/to/some/deeply/nested/module/in/the/project/database.py"
    )
    assert format_path_for_display(long_path) == ".../the/project/database.py"

    # Custom max length
    assert (
        format_path_for_display("/app/config.py", max_length=10) == "/app/config.py"
    )  # Still under custom limit
    assert (
        format_path_for_display("/app/module/submodule/config.py", max_length=20)
        == ".../submodule/config.py"
    )


def test_get_binding_location_info_with_metadata():
    """Test getting binding location from metadata"""
    # Create a design with metadata
    d = design(value=InjectedPure("test"))

    metadata = BindMetadata(
        code_location=Some(
            ModuleVarLocation(path=Path("/app/config.py"), line=42, column=0)
        )
    )

    d_with_metadata = d.add_metadata(value=metadata)

    # Create DIGraph
    enhanced_design = d_with_metadata + design(__design__=InjectedPure(d_with_metadata))
    di_graph = DIGraph(enhanced_design)

    # Test location extraction
    location_info = get_binding_location_info(di_graph, "value")
    assert location_info == " [from /app/config.py:42]"


def test_get_binding_location_info_with_module_path():
    """Test getting binding location from ModuleVarPath"""
    # Create a design with ModuleVarPath metadata
    d = design(value=InjectedPure("test"))

    metadata = BindMetadata(code_location=Some(ModuleVarPath("app.config.module")))

    d_with_metadata = d.add_metadata(value=metadata)

    # Create DIGraph
    enhanced_design = d_with_metadata + design(__design__=InjectedPure(d_with_metadata))
    di_graph = DIGraph(enhanced_design)

    # Test location extraction
    location_info = get_binding_location_info(di_graph, "value")
    assert location_info == " [from app.config.module]"


def test_get_binding_location_info_fallback():
    """Test fallback to binding_sources when no metadata"""
    # Create a design without metadata
    d = design(value=InjectedPure("test"))

    # Create DIGraph
    enhanced_design = d + design(__design__=InjectedPure(d))
    di_graph = DIGraph(enhanced_design)

    # Test with binding_sources
    binding_sources = {"value": "user default design"}
    location_info = get_binding_location_info(di_graph, "value", binding_sources)
    assert location_info == " [from user default design]"

    # Test with long path in binding_sources
    binding_sources = {"value": "/very/long/path/to/some/deeply/nested/module.py"}
    location_info = get_binding_location_info(di_graph, "value", binding_sources)
    assert location_info == " [from .../deeply/nested/module.py]"


def test_get_binding_location_info_no_location():
    """Test when no location info is available"""
    # Create a design without metadata
    d = design(value=InjectedPure("test"))

    # Create DIGraph
    enhanced_design = d + design(__design__=InjectedPure(d))
    di_graph = DIGraph(enhanced_design)

    # Test without binding_sources
    location_info = get_binding_location_info(di_graph, "value")
    assert location_info == ""


def test_binding_metadata_display():
    """Test that binding metadata with file:line info is displayed in the dependency tree"""
    # Create a design with some bindings
    d = design(value1=InjectedPure("test1"), value2=InjectedPure("test2"))

    # Add metadata to the bindings
    metadata1 = BindMetadata(
        code_location=Some(
            ModuleVarLocation(path=Path("/app/config.py"), line=42, column=0)
        )
    )

    metadata2 = BindMetadata(
        code_location=Some(
            ModuleVarLocation(
                path=Path(
                    "/very/long/path/to/some/deeply/nested/module/in/the/project/database.py"
                ),
                line=100,
                column=5,
            )
        )
    )

    # Add metadata to design
    d_with_metadata = d.add_metadata(value1=metadata1, value2=metadata2)

    # Create a target that uses these values
    @d_with_metadata.injectable
    def target(value1, value2):
        return f"{value1}-{value2}"

    # Get the dependency tree
    tree_str = design_rich_tree(d_with_metadata, "target")

    # Verify metadata is displayed
    assert "[from /app/config.py:42]" in tree_str
    assert (
        "[from .../the/project/database.py:100]" in tree_str
    )  # Long path should be shortened


def test_fallback_to_binding_sources():
    """Test that binding_sources is used when metadata is not available"""
    # Create a design without metadata
    d = design(value1=InjectedPure("test1"), value2=InjectedPure("test2"))

    @d.injectable
    def target(value1, value2):
        return f"{value1}-{value2}"

    # Provide binding_sources manually
    binding_sources = {"value1": "user default design", "value2": "/app/module.py"}

    # Get the dependency tree
    tree_str = design_rich_tree(d, "target", binding_sources)

    # Verify binding_sources is used as fallback
    assert "[from user default design]" in tree_str
    assert "[from /app/module.py]" in tree_str


def test_metadata_takes_precedence_over_binding_sources():
    """Test that metadata takes precedence over binding_sources when both are available"""
    # Create a design with metadata
    d = design(value1=InjectedPure("test1"))

    metadata = BindMetadata(
        code_location=Some(
            ModuleVarLocation(path=Path("/actual/location.py"), line=10, column=0)
        )
    )

    d_with_metadata = d.add_metadata(value1=metadata)

    @d_with_metadata.injectable
    def target(value1):
        return value1

    # Provide conflicting binding_sources
    binding_sources = {"value1": "wrong location"}

    # Get the dependency tree
    tree_str = design_rich_tree(d_with_metadata, "target", binding_sources)

    # Verify metadata takes precedence
    assert "[from /actual/location.py:10]" in tree_str
    assert "[from wrong location]" not in tree_str
