"""Simple tests for test_helper/test_aggregator.py module."""

import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
from dataclasses import is_dataclass

from pinjected.test_helper.test_aggregator import (
    check_design_variable,
    design_acceptor,
    TimeCachedFileData,
)


class TestCheckDesignVariable:
    """Test the check_design_variable function."""

    def test_check_design_variable_with_global(self):
        """Test check_design_variable with global __design__."""
        code = """
global __design__
__design__ = {"key": "value"}
"""
        with patch("builtins.open", mock_open(read_data=code)):
            result = check_design_variable("test.py")

        assert result is True

    def test_check_design_variable_with_assignment(self):
        """Test check_design_variable with direct assignment."""
        code = """
from pinjected import design
__design__ = design(name="test")
"""
        with patch("builtins.open", mock_open(read_data=code)):
            result = check_design_variable("test.py")

        assert result is True

    def test_check_design_variable_without_design(self):
        """Test check_design_variable without __design__."""
        code = """
def some_function():
    return 42
"""
        with patch("builtins.open", mock_open(read_data=code)):
            result = check_design_variable("test.py")

        assert result is False

    def test_check_design_variable_with_nested_assignment(self):
        """Test check_design_variable with assignment in function."""
        code = """
def setup():
    __design__ = {"key": "value"}
"""
        with patch("builtins.open", mock_open(read_data=code)):
            result = check_design_variable("test.py")

        # Should find it even inside function
        assert result is True

    def test_check_design_variable_empty_file(self):
        """Test check_design_variable with empty file."""
        with patch("builtins.open", mock_open(read_data="")):
            result = check_design_variable("test.py")

        assert result is False


class TestDesignAcceptor:
    """Test the design_acceptor function."""

    @patch("pinjected.test_helper.test_aggregator.check_design_variable")
    def test_design_acceptor_python_file_with_design(self, mock_check):
        """Test design_acceptor with Python file containing __design__."""
        mock_check.return_value = True
        file_path = Path("test.py")

        result = design_acceptor(file_path)

        assert result is True
        mock_check.assert_called_once_with(file_path)

    @patch("pinjected.test_helper.test_aggregator.check_design_variable")
    def test_design_acceptor_python_file_without_design(self, mock_check):
        """Test design_acceptor with Python file not containing __design__."""
        mock_check.return_value = False
        file_path = Path("test.py")

        result = design_acceptor(file_path)

        assert result is False

    def test_design_acceptor_non_python_file(self):
        """Test design_acceptor with non-Python file."""
        file_path = Path("test.txt")

        result = design_acceptor(file_path)

        assert result is False

    def test_design_acceptor_no_extension(self):
        """Test design_acceptor with file without extension."""
        file_path = Path("README")

        result = design_acceptor(file_path)

        assert result is False


class TestTimeCachedFileData:
    """Test the TimeCachedFileData class."""

    def test_time_cached_file_data_is_dataclass(self):
        """Test that TimeCachedFileData is a dataclass."""
        assert is_dataclass(TimeCachedFileData)

    def test_time_cached_file_data_creation(self):
        """Test creating TimeCachedFileData instance."""
        cache_path = Path("/tmp/cache")

        def file_to_data(f):
            return f.read_text()

        cached = TimeCachedFileData(cache_path=cache_path, file_to_data=file_to_data)

        assert cached.cache_path == cache_path
        assert cached.file_to_data is file_to_data

    def test_time_cached_file_data_is_generic(self):
        """Test that TimeCachedFileData is generic."""
        # Check that it has generic type parameter
        assert hasattr(TimeCachedFileData, "__parameters__")

    def test_time_cached_file_data_docstring(self):
        """Test TimeCachedFileData has proper docstring."""
        assert TimeCachedFileData.__doc__ is not None
        assert "cache" in TimeCachedFileData.__doc__
        assert "files" in TimeCachedFileData.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
