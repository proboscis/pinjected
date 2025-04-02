import pytest
from pinjected.helpers import get_design_path_from_var_path


def test_get_design_path_from_var_path_with_none():
    """Test that get_design_path_from_var_path returns None when var_path is None."""
    result = get_design_path_from_var_path(None)
    assert result is None


def test_get_design_path_from_var_path_with_invalid_module():
    """Test that get_design_path_from_var_path returns None for non-existent modules."""
    result = get_design_path_from_var_path("non.existent.module.path")
    assert result is None


def test_get_design_path_from_var_path_with_no_design_paths():
    """Test that get_design_path_from_var_path returns None when no design paths are found."""
    from unittest.mock import patch
    
    with patch('pinjected.helpers.find_default_design_paths', return_value=[]):
        result = get_design_path_from_var_path("pinjected.helpers")
        assert result is None
