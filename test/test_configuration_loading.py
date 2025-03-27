import os
import pytest
from pathlib import Path
from unittest.mock import patch

from pinjected.run_helpers.run_injected import (
    load_user_default_design,
    load_user_overrides_design,
    PinjectedConfigurationLoadFailure,
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
    """Test that load_user_overrides_design raises PinjectedConfigurationLoadFailure when loading fails."""
    with patch('pinjected.run_helpers.run_injected.find_dot_pinjected') as mock_find:
        mock_path = Path("/tmp/mock_pinjected.py")
        mock_path.touch()  # Create the file
        
        with open(mock_path, "w") as f:
            f.write("this is not valid python code :")
        
        mock_find.return_value = [mock_path]
        
        with pytest.raises(PinjectedConfigurationLoadFailure):
            load_user_overrides_design()
        
        mock_path.unlink()
