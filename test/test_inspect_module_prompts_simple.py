"""Simple tests for llm_support/inspect_module_prompts.py module."""

import pytest

from pinjected.llm_support.inspect_module_prompts import INSPECT_TEMPLATE


class TestInspectModulePrompts:
    """Test the inspect module prompts constants."""

    def test_inspect_template_exists(self):
        """Test that INSPECT_TEMPLATE exists and is a string."""
        assert INSPECT_TEMPLATE is not None
        assert isinstance(INSPECT_TEMPLATE, str)

    def test_inspect_template_content(self):
        """Test that INSPECT_TEMPLATE contains expected content."""
        # Should contain information about injected decorator
        assert "@injected" in INSPECT_TEMPLATE
        assert "dependency injection" in INSPECT_TEMPLATE
        assert "InjectedProxy" in INSPECT_TEMPLATE
        assert "Injected" in INSPECT_TEMPLATE

    def test_inspect_template_has_example(self):
        """Test that INSPECT_TEMPLATE includes an example."""
        assert "def foo(" in INSPECT_TEMPLATE
        assert "dep1,dep2,/,x:int" in INSPECT_TEMPLATE
        assert "Example:" in INSPECT_TEMPLATE

    def test_inspect_template_explains_monad(self):
        """Test that INSPECT_TEMPLATE explains Injected monad."""
        assert "monad" in INSPECT_TEMPLATE
        assert "positional only arguments" in INSPECT_TEMPLATE
        assert "dependencies" in INSPECT_TEMPLATE

    def test_inspect_template_not_empty(self):
        """Test that INSPECT_TEMPLATE is not empty."""
        assert len(INSPECT_TEMPLATE) > 100  # Should be a substantial template
        assert INSPECT_TEMPLATE.strip() != ""

    def test_can_import_template(self):
        """Test that we can import the template."""
        from pinjected.llm_support import inspect_module_prompts

        assert hasattr(inspect_module_prompts, "INSPECT_TEMPLATE")
        assert inspect_module_prompts.INSPECT_TEMPLATE == INSPECT_TEMPLATE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
