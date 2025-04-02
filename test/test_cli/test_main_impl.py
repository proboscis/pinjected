import io
import sys
from unittest.mock import patch

import pytest
import fire

from pinjected.main_impl import PinjectedCLI


def test_pinjected_cli_docstring():
    """Test that the PinjectedCLI class has the expected docstring."""
    cli = PinjectedCLI()
    
    assert "Pinjected: Python Dependency Injection Framework" in cli.__doc__
    assert "Available commands:" in cli.__doc__
    assert "run" in cli.__doc__
    assert "call" in cli.__doc__
    assert "check_config" in cli.__doc__
    assert "create_overloads" in cli.__doc__
    assert "json_graph" in cli.__doc__
    assert "describe" in cli.__doc__


def test_fire_help_output():
    """Test that the PinjectedCLI class has a comprehensive docstring for Fire help."""
    cli = PinjectedCLI()
    
    assert "Pinjected: Python Dependency Injection Framework" in cli.__doc__
    assert "Available commands:" in cli.__doc__
    assert "run" in cli.__doc__
    assert "call" in cli.__doc__
    assert "check_config" in cli.__doc__
    assert "create_overloads" in cli.__doc__
    assert "json_graph" in cli.__doc__
    assert "describe" in cli.__doc__
    assert "For more information on a specific command" in cli.__doc__
    assert "Example:" in cli.__doc__


def test_describe_command_help():
    """Test that the describe command docstring mentions the required format and both usage options."""
    from pinjected.main_impl import describe
    
    assert "full.module.path.var.name" in describe.__doc__
    assert "This parameter is required" in describe.__doc__
    assert "must point to an importable variable" in describe.__doc__
    
    cli = PinjectedCLI()
    assert "describe my_module.path.var" in cli.__doc__
    assert "describe --var_path=my_module.path.var" in cli.__doc__
