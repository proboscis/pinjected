import pytest
from pinjected_openai import __version__

def test_version():
    """Test that the version is a string."""
    assert isinstance(__version__, str)
