import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures.process import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from injected_utils.async_caching.async_cached_function import AsyncCacheProtocol
from injected_utils.async_caching.async_sqlite import AsyncSqlite
from pinjected import *


@dataclass
class CompressedAsyncCache(AsyncCacheProtocol[bytes, bytes]):
    src: AsyncCacheProtocol[bytes, bytes]
    a_compress: Callable[[bytes], Awaitable[bytes]]
    a_decompress: Callable[[bytes], Awaitable[bytes]]

    async def a_set(self, key: bytes, value: bytes) -> None:
        assert isinstance(key, bytes), f"key:{type(key)} must be bytes"
        assert isinstance(value, bytes), f"value:{type(value)} must be bytes"
        compressed = await self.a_compress(value)
        await self.src.a_set(key, compressed)

    async def a_get(self, key: bytes) -> bytes:
        compressed = await self.src.a_get(key)
        return await self.a_decompress(compressed)

    async def a_contains(self, key: bytes) -> bool:
        return await self.src.a_contains(key)


def compress_lzma(data: bytes) -> bytes:
    import lzma

    return lzma.compress(data)


def decompress_lzma(data: bytes) -> bytes:
    import lzma

    return lzma.decompress(data)


@injected
async def async_lzma_sqlite(path: Path):
    pool = ProcessPoolExecutor()
    loop = asyncio.get_event_loop()

    async def a_compress(data: bytes):
        return await loop.run_in_executor(pool, compress_lzma, data)

    async def a_decompress(data: bytes):
        return await loop.run_in_executor(pool, decompress_lzma, data)

    return CompressedAsyncCache(
        src=AsyncSqlite(path), a_compress=a_compress, a_decompress=a_decompress
    )


@instance
async def test_lzma_sqlite(async_lzma_sqlite):
    key = b"key"
    value = b"value"
    path = Path("test.db")
    cache: AsyncCacheProtocol = await async_lzma_sqlite(path)
    await cache.a_set(key, value)
    assert await cache.a_get(key) == value
    assert await cache.a_get(key) == value

    path.unlink()


__meta_design__ = design()
