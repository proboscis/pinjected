"""Test that binding locations are displayed correctly in dependency trees."""

from pinjected import design, injected
from pinjected.cli_visualizations.tree import design_rich_tree
from pinjected.v2.keys import StrBindKey


@injected
def service_a(config: str, /):
    """Service A that depends on config."""
    return f"ServiceA with {config}"


@injected
def service_b(service_a: str, database: str, /):
    """Service B that depends on service_a and database."""
    return f"ServiceB using {service_a} and {database}"


def test_binding_locations_displayed():
    """Test that binding locations are shown in the dependency tree."""

    # Create design with bindings
    test_design = design(
        config="test_config",
        database="test_db",
        service_a=service_a,
        service_b=service_b,
    )

    # Create binding sources with proper IBindKey objects
    binding_sources = {
        StrBindKey("config"): "/app/config/__pinjected__.py",
        StrBindKey("database"): "/app/database.py",
        StrBindKey("service_a"): "user default design",
    }

    # Generate the tree
    tree_str = design_rich_tree(test_design, service_b, binding_sources)

    # Verify no 'not found' errors
    assert "not found" not in tree_str

    # Verify binding locations are shown
    assert "[from" in tree_str
    assert "config/__pinjected__.py" in tree_str
    assert "database.py" in tree_str
    assert "user default design" in tree_str

    # Print tree for manual verification if needed
    print("\nGenerated tree:")
    print(tree_str)


def test_binding_locations_without_sources():
    """Test that tree works without binding sources."""

    # Create design
    test_design = design(
        config="test_config",
        service_a=service_a,
    )

    # Generate tree without binding sources
    tree_str = design_rich_tree(test_design, service_a)

    # Should work without errors
    assert "not found" not in tree_str

    # Should not have binding location info
    assert "[from" not in tree_str


def test_mixed_key_types():
    """Test handling of mixed key types in binding sources."""

    # Create design
    test_design = design(
        config="test_config",
        database="test_db",
    )

    # Mix of StrBindKey and string keys (to test backwards compatibility)
    binding_sources = {
        StrBindKey("config"): "/app/config.py",
        "database": "/app/database.py",  # String key (should not match)
    }

    # Generate tree
    tree_str = design_rich_tree(test_design, injected("config"), binding_sources)

    # Config should show location, database should not
    assert "config.py" in tree_str
    # Database binding location won't show because key type mismatch

    print("\nMixed key types tree:")
    print(tree_str)
