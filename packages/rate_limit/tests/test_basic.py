import pytest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pinjected_rate_limit import __version__

def test_version():
    assert __version__ == "0.1.0"
