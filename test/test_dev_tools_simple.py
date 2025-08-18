"""Simple tests for _dev_tools/__init__.py module."""

import pytest
from unittest.mock import patch, Mock

from pinjected._dev_tools import generate_merged_doc, __design__


class TestDevTools:
    """Test the _dev_tools module functionality."""

    def test_generate_merged_doc_is_instance(self):
        """Test that generate_merged_doc is an instance (IProxy)."""
        from pinjected.di.proxiable import DelegatedVar

        assert isinstance(generate_merged_doc, DelegatedVar)

    @patch("pinjected._dev_tools.doc_merger.Path")
    def test_generate_merged_doc_function(self, mock_path_class):
        """Test the generate_merged_doc function logic through DI."""
        from pinjected import design

        # Mock Path objects
        mock_docs_path = Mock()
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        mock_doc3 = Mock()

        # Set names for sorting
        mock_doc1.__str__ = Mock(return_value="docs/a.md")
        mock_doc2.__str__ = Mock(return_value="docs/b.md")
        mock_doc3.__str__ = Mock(return_value="docs/c.md")
        mock_doc1.__lt__ = lambda self, other: str(self) < str(other)
        mock_doc2.__lt__ = lambda self, other: str(self) < str(other)
        mock_doc3.__lt__ = lambda self, other: str(self) < str(other)

        # Setup read_text return values
        mock_doc1.read_text.return_value = "# Doc 1 Content"
        mock_doc2.read_text.return_value = "# Doc 2 Content"
        mock_doc3.read_text.return_value = "# Doc 3 Content"

        # Setup rglob to return mock documents
        mock_docs_path.rglob.return_value = [
            mock_doc2,
            mock_doc1,
            mock_doc3,
        ]  # Unsorted

        # Setup Path() calls
        mock_output_path = Mock()
        mock_path_class.side_effect = lambda x: {
            "docs": mock_docs_path,
            "merged_doc.md": mock_output_path,
        }.get(x, Mock())

        # Create a design with mock logger
        mock_logger = Mock()
        d = design(logger=mock_logger)
        g = d.to_graph()

        # Execute the function through DI
        g.provide(generate_merged_doc)

        # Verify logger was called
        mock_logger.info.assert_called_once()
        logged_docs = mock_logger.info.call_args[0][0]
        assert len(logged_docs) == 3
        assert logged_docs[0] is mock_doc1  # Should be sorted
        assert logged_docs[1] is mock_doc2
        assert logged_docs[2] is mock_doc3

        # Verify merged content was written
        expected_content = "# Doc 1 Content\n# Doc 2 Content\n# Doc 3 Content"
        mock_output_path.write_text.assert_called_once_with(expected_content)

    def test_design_configuration(self):
        """Test the __design__ configuration."""
        # __design__ should be a dict-like object
        assert __design__ is not None

        # Should have 'overrides' key based on the code
        # design(overrides=design()) creates a design with overrides
        assert hasattr(__design__, "__getitem__") or isinstance(__design__, dict)

    def test_module_imports_pinjected(self):
        """Test that the module imports from pinjected."""
        # Check that we have access to pinjected exports
        from pinjected._dev_tools import instance, design

        # These should be the decorators/functions from pinjected
        assert callable(instance)
        assert callable(design)

    @patch("pinjected._dev_tools.doc_merger.Path")
    def test_generate_merged_doc_empty_docs(self, mock_path_class):
        """Test generate_merged_doc with no markdown files."""
        from pinjected import design

        # Mock empty docs directory
        mock_docs_path = Mock()
        mock_docs_path.rglob.return_value = []

        mock_output_path = Mock()
        mock_path_class.side_effect = lambda x: {
            "docs": mock_docs_path,
            "merged_doc.md": mock_output_path,
        }.get(x, Mock())

        # Create a design with mock logger
        mock_logger = Mock()
        d = design(logger=mock_logger)
        g = d.to_graph()

        # Execute the function through DI
        g.provide(generate_merged_doc)

        # Should log empty list
        mock_logger.info.assert_called_once_with([])

        # Should write empty content
        mock_output_path.write_text.assert_called_once_with("")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
