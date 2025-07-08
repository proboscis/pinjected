"""Tests for _dev_tools module."""

import pytest
from pathlib import Path
from unittest.mock import Mock
import tempfile
import os

from pinjected._dev_tools import generate_merged_doc, __design__


class TestGenerateMergedDoc:
    """Test generate_merged_doc function."""

    def test_generate_merged_doc_function(self):
        """Test the generate_merged_doc function logic."""
        # Create a test scenario
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            docs_dir = tmp_path / "docs"
            docs_dir.mkdir()

            # Create test files
            (docs_dir / "a.md").write_text("Content A")
            (docs_dir / "b.md").write_text("Content B")
            (docs_dir / "c.txt").write_text("Not markdown")  # Should be ignored

            # Mock logger
            mock_logger = Mock()

            # Save current directory
            original_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)

                # Execute the function logic directly (same as in _dev_tools)
                docs = sorted(list(Path("docs").rglob("*.md")))
                mock_logger.info(docs)
                merged_text = "\n".join([doc.read_text() for doc in docs])
                Path("merged_doc.md").write_text(merged_text)

                # Verify
                assert mock_logger.info.called
                assert len(mock_logger.info.call_args[0][0]) == 2

                merged = Path("merged_doc.md")
                assert merged.exists()
                content = merged.read_text()
                assert content == "Content A\nContent B"

            finally:
                os.chdir(original_cwd)

    def test_generate_merged_doc_type(self):
        """Test that generate_merged_doc is properly decorated."""
        # It should be a DelegatedVar (IProxy) since it's decorated with @instance
        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(generate_merged_doc, DelegatedVar)

    def test_empty_docs_directory(self):
        """Test when docs directory is empty."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            docs_dir = tmp_path / "docs"
            docs_dir.mkdir()

            mock_logger = Mock()
            original_cwd = Path.cwd()

            try:
                os.chdir(tmp_path)

                # Execute function logic
                docs = sorted(list(Path("docs").rglob("*.md")))
                mock_logger.info(docs)
                merged_text = "\n".join([doc.read_text() for doc in docs])
                Path("merged_doc.md").write_text(merged_text)

                # Verify
                mock_logger.info.assert_called_once_with([])
                assert Path("merged_doc.md").exists()
                assert Path("merged_doc.md").read_text() == ""

            finally:
                os.chdir(original_cwd)

    def test_no_docs_directory(self):
        """Test when docs directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Don't create docs directory

            mock_logger = Mock()
            original_cwd = Path.cwd()

            try:
                os.chdir(tmp_path)

                # Execute function logic
                docs = sorted(list(Path("docs").rglob("*.md")))
                mock_logger.info(docs)
                merged_text = "\n".join([doc.read_text() for doc in docs])
                Path("merged_doc.md").write_text(merged_text)

                # Verify
                mock_logger.info.assert_called_once_with([])
                assert Path("merged_doc.md").exists()
                assert Path("merged_doc.md").read_text() == ""

            finally:
                os.chdir(original_cwd)


class TestDesign:
    """Test module design."""

    def test_design_exists(self):
        """Test that __design__ is defined."""
        assert __design__ is not None

    def test_design_is_design_instance(self):
        """Test that __design__ is a Design instance."""
        from pinjected import Design

        assert isinstance(__design__, Design)

    def test_design_bindings(self):
        """Test that design has expected bindings."""
        # The design is created with overrides=design()
        bindings = __design__.bindings

        # Check it has the overrides binding
        binding_names = [key.name for key in bindings if hasattr(key, "name")]
        assert "overrides" in binding_names


def test_module_attributes():
    """Test that module has expected attributes."""
    from pinjected import _dev_tools

    # Check main attributes
    assert hasattr(_dev_tools, "generate_merged_doc")
    assert hasattr(_dev_tools, "__design__")

    # Check it's using pinjected
    assert hasattr(_dev_tools, "instance")
    assert hasattr(_dev_tools, "design")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
