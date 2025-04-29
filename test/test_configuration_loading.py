from pathlib import Path
from unittest.mock import patch

import pytest

from pinjected.run_helpers.run_injected import (
    PinjectedConfigurationLoadFailure,
    load_user_default_design,
    load_user_overrides_design,
)


def test_load_user_default_design_failure():
    """Test that load_user_default_design raises PinjectedConfigurationLoadFailure when loading fails."""
    with patch('pinjected.run_helpers.run_injected.find_dot_pinjected') as mock_find:
        mock_path = Path("/tmp/mock_pinjected.py")
        mock_path.touch()  # Create the file
        
        with open(mock_path, "w") as f:
            f.write("this is not valid python code :")
        
        mock_find.return_value = [mock_path]
        
        with pytest.raises(PinjectedConfigurationLoadFailure):
            load_user_default_design()
        
        mock_path.unlink()


def test_load_user_overrides_design_failure():
    """Test that load_user_overrides_design does not raise exception for missing variable but raises for syntax errors."""
    with patch('pinjected.run_helpers.run_injected.find_dot_pinjected') as mock_find:
        # Test case 1: Variable not found - should NOT raise exception
        mock_path = Path("/tmp/mock_pinjected.py")
        mock_path.touch()  # Create the file
        
        with open(mock_path, "w") as f:
            f.write("# Valid Python but no overrides_design variable defined")
        
        mock_find.return_value = [mock_path]
        
        # This should not raise exception
        result = load_user_overrides_design()
        assert result is not None
        
        # Test case 2: Syntax error - SHOULD raise exception
        with open(mock_path, "w") as f:
            f.write("this is not valid python code :")
        
        with pytest.raises(PinjectedConfigurationLoadFailure):
            load_user_overrides_design()
        
        mock_path.unlink()
