from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import cloudpickle
import jsonpickle
from sqlitedict import SqliteDict

from pinjected import injected


@dataclass
class CompressedPklSqliteDict:
    src: SqliteDict
    compress: Callable[[bytes], bytes]
    decompress: Callable[[bytes], bytes]
    loads: Callable[[str], object] = field(default=cloudpickle.loads)
    dumps: Callable[[object], str] = field(default=cloudpickle.dumps)

    def __reduce__(self):
        return CompressedPklSqliteDict.from_path, (
            self.compress,
            self.decompress,
            self.src.filename,
        )

    @classmethod
    def from_path(cls, compress, decompress, path):
        return cls(
            SqliteDict(path, autocommit=True),
            compress,
            decompress,
        )

    def __getitem__(self, item):
        key = jsonpickle.dumps(item)
        raw_data = self.src[key]
        uncompressed = self.decompress(raw_data)
        return self.loads(uncompressed)

    def __setitem__(self, key, value):
        key = jsonpickle.dumps(key)
        raw_data = self.dumps(value)
        compressed = self.compress(raw_data)
        self.src[key] = compressed

    def __contains__(self, item):
        key = jsonpickle.dumps(item)
        return key in self.src

    def __delitem__(self, instance):
        key = jsonpickle.dumps(instance)
        del self.src[key]

    def values(self):
        return [self.loads(self.decompress(v)) for v in self.src.values()]

    def keys(self):
        return [jsonpickle.loads(k) for k in self.src.keys()]


@injected
def compress__lzma(logger, /, data: bytes):
    import lzma

    src_mb = len(data) / 1024 / 1024
    # logger.info(f"Compressing {src_mb} MB")
    res = lzma.compress(data)
    res_mb = len(res) / 1024 / 1024
    # logger.info(f"Compressed: {src_mb} MB -> {res_mb} MB")
    return res


@injected
def lzma_sqlite(compress__lzma, /, path: Path):
    import lzma

    return CompressedPklSqliteDict(
        src=SqliteDict(path, autocommit=True),
        compress=compress__lzma,
        decompress=lzma.decompress,
    )
