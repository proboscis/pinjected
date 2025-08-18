"""Tests for cli_visualizations.__init__ module."""


class TestCliVisualizationsInit:
    """Test cli_visualizations.__init__ module."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        import pinjected.cli_visualizations

        assert pinjected.cli_visualizations is not None

    def test_design_rich_tree_import(self):
        """Test that design_rich_tree is imported."""
        from pinjected.cli_visualizations import design_rich_tree

        assert design_rich_tree is not None
        assert callable(design_rich_tree)

    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        import pinjected.cli_visualizations

        assert hasattr(pinjected.cli_visualizations, "__all__")
        assert pinjected.cli_visualizations.__all__ == ["design_rich_tree"]

    def test_reexport_consistency(self):
        """Test that the re-exported function is the same as the original."""
        from pinjected.cli_visualizations import design_rich_tree
        from pinjected.cli_visualizations.tree import design_rich_tree as original

        assert design_rich_tree is original

    def test_no_unexpected_exports(self):
        """Test that no unexpected symbols are exported."""
        import pinjected.cli_visualizations

        # Get all public attributes
        public_attrs = [
            attr
            for attr in dir(pinjected.cli_visualizations)
            if not attr.startswith("_")
        ]

        # Both design_rich_tree and tree module should be public
        expected = {"design_rich_tree", "tree"}
        assert set(public_attrs) == expected
