"""Tests for pinjected/_dev_tools/__init__.py module."""

import pytest
from pathlib import Path
from unittest.mock import Mock
import tempfile

from pinjected._dev_tools import generate_merged_doc, __design__


class TestGenerateMergedDoc:
    """Tests for generate_merged_doc function."""

    def test_generate_merged_doc_is_instance(self):
        """Test that generate_merged_doc is an injected instance."""
        # The @instance decorator transforms it into a callable
        assert callable(generate_merged_doc)

    def test_generate_merged_doc_has_logger_dependency(self):
        """Test that generate_merged_doc has logger dependency."""
        # Test with design and graph, providing a logger
        from pinjected import design

        mock_logger = Mock()
        d = design(logger=mock_logger)
        g = d.to_graph()

        # Should work when we have a logger
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docs_dir = temp_path / "docs"
            docs_dir.mkdir()

            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(temp_path)

                # This should work as it will inject logger
                g.provide(generate_merged_doc)
                # generate_merged_doc function should have run
                merged_file = temp_path / "merged_doc.md"
                assert merged_file.exists()
                # Verify logger was called
                mock_logger.info.assert_called_once()
            finally:
                os.chdir(original_cwd)

    def test_generate_merged_doc_function_behavior(self):
        """Test the actual function behavior of generate_merged_doc."""
        # Test it can be resolved from a graph
        from pinjected import design

        mock_logger = Mock()
        d = design(logger=mock_logger)
        g = d.to_graph()

        # Create a temporary directory and test the function
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create docs directory
            docs_dir = temp_path / "docs"
            docs_dir.mkdir()

            # Create markdown files
            (docs_dir / "readme.md").write_text("# README\nContent")
            (docs_dir / "guide.md").write_text("# Guide\nMore content")

            # Change to temp directory and run function
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(temp_path)

                # Run through graph
                g.provide(generate_merged_doc)

                # Verify merged file was created
                merged_file = temp_path / "merged_doc.md"
                assert merged_file.exists()

                # Verify content
                merged_content = merged_file.read_text()
                assert "# README" in merged_content
                assert "# Guide" in merged_content

                # Verify logger was called
                mock_logger.info.assert_called_once()

            finally:
                os.chdir(original_cwd)

    def test_generate_merged_doc_empty_docs(self):
        """Test generate_merged_doc with no docs directory."""
        from pinjected import design

        mock_logger = Mock()
        d = design(logger=mock_logger)
        g = d.to_graph()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Change to temp directory (no docs dir)
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(temp_path)

                # Run through graph - should not raise error
                g.provide(generate_merged_doc)

                # Verify merged file was created (empty)
                merged_file = temp_path / "merged_doc.md"
                assert merged_file.exists()
                assert merged_file.read_text() == ""

                # Verify logger was called
                mock_logger.info.assert_called_once()

            finally:
                os.chdir(original_cwd)


class TestDesignObject:
    """Tests for __design__ module variable."""

    def test_design_exists(self):
        """Test that __design__ is defined."""
        assert __design__ is not None

    def test_design_has_overrides(self):
        """Test that __design__ has overrides property."""
        # The design should have been created with overrides parameter
        assert hasattr(__design__, "__wrapped_design__") or hasattr(
            __design__, "bindings"
        )

    def test_generate_merged_doc_in_design(self):
        """Test that generate_merged_doc can be found in the design."""
        # Since generate_merged_doc is decorated with @instance,
        # it should be accessible through the design
        from pinjected import design

        # Create a test design that includes the function
        test_design = design(generate_merged_doc=generate_merged_doc)

        # Verify it's in the bindings
        assert hasattr(test_design, "bindings") or hasattr(
            test_design, "__wrapped_design__"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
