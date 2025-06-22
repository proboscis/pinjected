from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from sqlitedict import SqliteDict

K = TypeVar("K")
V = TypeVar("V")

@dataclass
class CompressedPklSqliteDict:
    src: SqliteDict
    compress: Callable[[bytes], bytes]
    decompress: Callable[[bytes], bytes]
    loads: Callable[[bytes], Any]
    dumps: Callable[[Any], bytes]

    def __reduce__(
        self,
    ) -> tuple[
        type[CompressedPklSqliteDict],
        tuple[Callable[[bytes], bytes], Callable[[bytes], bytes], str],
    ]: ...
    @classmethod
    def from_path(
        cls,
        compress: Callable[[bytes], bytes],
        decompress: Callable[[bytes], bytes],
        path: str,
    ) -> CompressedPklSqliteDict: ...
    def __getitem__(self, item: K) -> V: ...
    def __setitem__(self, key: K, value: V) -> None: ...
    def __contains__(self, item: K) -> bool: ...
    def __delitem__(self, instance: K) -> None: ...
    def values(self) -> list[V]: ...
    def keys(self) -> list[K]: ...

def compress__lzma(data: bytes) -> bytes: ...
def lzma_sqlite(path: Path) -> CompressedPklSqliteDict: ...

__meta_design__: Any
