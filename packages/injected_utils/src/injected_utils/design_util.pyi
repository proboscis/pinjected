from pathlib import Path
from typing import Any

from pinjected import IProxy

async def a_get_env(key: str) -> str: ...
async def a_env_to_file(
    key: str, file_path: str | Path, permissions: int | None = None
) -> Path: ...
async def a_str_to_file(
    text: str, file_path: str | Path, permissions: int | None = None
) -> Path: ...
async def a_base64_to_file(
    base64_str: str, file_path: str | Path, permissions: int | None = None
) -> Path: ...

str_to_path: IProxy[Path]

__meta_design__: Any
