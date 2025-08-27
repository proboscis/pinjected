from asyncio import Event
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from injected_utils.async_caching.async_cached_function import AsyncCacheProtocol


@dataclass
class AsyncSqlite(AsyncCacheProtocol[bytes, bytes]):
    path: Path

    def __post_init__(self):
        self.table_created = None

    def get_conn(self):
        return aiosqlite.connect(self.path)

    async def _ensure_table_created(self, conn):
        if self.table_created is None:
            self.table_created = Event()
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS cache (key BLOB PRIMARY KEY, value BLOB)"
            )
            await conn.commit()
            self.table_created.set()
        else:
            await self.table_created.wait()

    async def a_set(self, key: bytes, value: bytes) -> None:
        assert isinstance(key, bytes), f"key:{type(key)} must be bytes"
        assert isinstance(value, bytes), f"value:{type(value)} must be bytes"
        async with self.get_conn() as conn:
            await self._ensure_table_created(conn)
            await conn.execute(
                "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", (key, value)
            )
            await conn.commit()

    async def a_get(self, key: bytes) -> bytes:
        assert isinstance(key, bytes), f"key:{type(key)} must be bytes"
        async with self.get_conn() as conn:
            await self._ensure_table_created(conn)
            async with conn.execute(
                "SELECT value FROM cache WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    raise KeyError(key)
            return row[0]

    async def a_contains(self, key: bytes) -> bool:
        assert isinstance(key, bytes), f"key:{type(key)} must be bytes"
        async with self.get_conn() as conn:
            await self._ensure_table_created(conn)
            async with conn.execute(
                "SELECT 1 FROM cache WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
