import pytest
import re
from pathlib import Path

def test_version_consistency():
    """Test that the version in pyproject.toml matches the __version__ in __init__.py."""
    # Get version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        pyproject_content = f.read()
    
    version_match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_content)
    pyproject_version = version_match.group(1) if version_match else None
    
    # Get version from __init__.py
    init_path = Path(__file__).parent.parent / "pinjected" / "__init__.py"
    with open(init_path, "r") as f:
        init_content = f.read()
    
    init_version_match = re.search(r'__version__\s*=\s*"([^"]+)"', init_content)
    init_version = init_version_match.group(1) if init_version_match else None
    
    # Assert versions match
    assert pyproject_version is not None, "Version not found in pyproject.toml"
    assert init_version is not None, "Version not found in pinjected/__init__.py"
    assert pyproject_version == init_version, f"Version mismatch: {pyproject_version} != {init_version}"
