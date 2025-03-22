import pytest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pinjected_niji_voice import hello

def test_hello():
    assert hello() == "Hello from pinjected-niji-voice!"
