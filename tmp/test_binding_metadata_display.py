"""Test that binding metadata is displayed in dependency trees"""

from pathlib import Path

from returns.maybe import Some

from pinjected import design
from pinjected.cli_visualizations.tree import design_rich_tree
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.metadata.location_data import ModuleVarLocation
from pinjected.helper_structure import InjectedPure


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
        "[from .../module/in/the/project/database.py:100]" in tree_str
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
