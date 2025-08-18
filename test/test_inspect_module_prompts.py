"""Tests for llm_support/inspect_module_prompts.py module."""

import pytest


class TestInspectModulePrompts:
    """Tests for the inspect_module_prompts module."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        import pinjected.llm_support.inspect_module_prompts as prompts

        assert hasattr(prompts, "INSPECT_TEMPLATE")

    def test_inspect_template_content(self):
        """Test that INSPECT_TEMPLATE contains expected content."""
        from pinjected.llm_support.inspect_module_prompts import INSPECT_TEMPLATE

        # Check it's a string
        assert isinstance(INSPECT_TEMPLATE, str)

        # Check it contains key documentation elements
        assert "@injected" in INSPECT_TEMPLATE
        assert "dependency injection" in INSPECT_TEMPLATE
        assert "InjectedProxy" in INSPECT_TEMPLATE
        assert "Injected is a monad" in INSPECT_TEMPLATE
        assert "positional only arguments" in INSPECT_TEMPLATE

        # Check example code is present
        assert "def foo(dep1,dep2,/,x:int) -> int:" in INSPECT_TEMPLATE
        assert "foo: InjectedProxy[int -> int]" in INSPECT_TEMPLATE
        assert "foo_call_result: Injected[int] = foo(1)" in INSPECT_TEMPLATE

    def test_template_is_multiline(self):
        """Test that the template is a properly formatted multiline string."""
        from pinjected.llm_support.inspect_module_prompts import INSPECT_TEMPLATE

        lines = INSPECT_TEMPLATE.strip().split("\n")
        assert len(lines) > 5  # Should have multiple lines

        # Check there's an example section
        has_example = any("Example:" in line for line in lines)
        assert has_example

    def test_template_explains_key_concepts(self):
        """Test that the template explains key pinjected concepts."""
        from pinjected.llm_support.inspect_module_prompts import INSPECT_TEMPLATE

        # Key concepts that should be explained
        key_concepts = [
            "injected",
            "InjectedProxy",
            "Injected",
            "monad",
            "dependency",
            "framework",
        ]

        for concept in key_concepts:
            assert concept in INSPECT_TEMPLATE, f"Template should explain '{concept}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
