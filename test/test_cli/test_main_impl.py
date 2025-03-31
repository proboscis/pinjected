import io
import sys
from unittest.mock import patch

import pytest

from pinjected.main_impl import PinjectedCLI, display_help


def test_display_help():
    """Test that the display_help function prints the expected help message."""
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    display_help()
    
    output = captured_output.getvalue()
    
    sys.stdout = sys.__stdout__
    
    assert "Pinjected: Python Dependency Injection Framework" in output
    assert "Available commands:" in output
    assert "run" in output
    assert "call" in output
    assert "check_config" in output
    assert "create_overloads" in output
    assert "json_graph" in output
    assert "describe" in output


def test_pinjected_cli_default():
    """Test that the PinjectedCLI class calls display_help when called directly."""
    cli = PinjectedCLI()
    
    with patch('pinjected.main_impl.display_help') as mock_display_help:
        cli()
        mock_display_help.assert_called_once()
