"""
We store devin specific hacks here.
"""
import os
import base64
import re
from pathlib import Path
from typing import Final

from pinjected import instance, design, Injected, injected, IProxy


@injected
async def a_get_env(key: str):
    """
    Get the environment variable value for the given key.
    """
    assert key in os.environ, f"Environment variable {key} not found."
    return os.environ[key]


@injected
async def a_env_to_file(key: str, file_path: str | Path, permissions: int | None = None) -> Path:
    """
    Get the environment variable value for the given key and write it to a file.

    Args:
        key: Environment variable name
        file_path: Path to write the file to
        permissions: Optional file permissions (octal mode, e.g. 0o600 for private keys)
    """
    assert key in os.environ, f"Environment variable {key} not found."
    path = Path(file_path)
    with open(path, "w") as f:
        f.write(os.environ[key])

    if permissions is not None:
        os.chmod(path, permissions)

    return path


@injected
async def a_str_to_file(text: str, file_path: str | Path, permissions: int | None = None) -> Path:
    """
    Write the given content to a file at the specified path.

    Args:
        text: Content to write to the file
        file_path: Path to write the file to
        permissions: Optional file permissions (octal mode, e.g. 0o600 for private keys)
    """
    path = Path(file_path)
    with open(path, "w") as f:
        f.write(text)

    if permissions is not None:
        os.chmod(path, permissions)

    return path


@injected
async def a_base64_to_file(base64_str: str, file_path: str | Path, permissions: int | None = None) -> Path:
    """
    Decode a base64 string and write it to a file at the specified path.

    Args:
        base64_str: Base64 encoded string to decode and write
        file_path: Path to write the file to
        permissions: Optional file permissions (octal mode, e.g. 0o600 for private keys)

    Returns:
        Path object for the created file
    """
    path = Path(file_path)
    decoded_data = base64.b64decode(base64_str)

    with open(path, "wb") as f:
        f.write(decoded_data)

    if permissions is not None:
        os.chmod(path, permissions)

    return path


str_to_path = IProxy(Path)


