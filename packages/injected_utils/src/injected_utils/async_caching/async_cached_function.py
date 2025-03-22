import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Generic, ParamSpec, TypeVar, Awaitable, Protocol, Optional, Tuple
from loguru import logger
from typing import MutableMapping

P = ParamSpec('P')
U = TypeVar('U')
T = TypeVar('T')
Key = TypeVar('Key', contravariant=True)  # contravariantに変更

ParamToKey = Callable[[P], Awaitable[Key]]
IsErrorToRetry = Callable[[Exception], Awaitable[str]]
InvalidateValue = Callable[[tuple[P.args, P.kwargs], U], Awaitable[str]]


class AsyncCacheProtocol(Protocol, Generic[Key, U]):
    async def a_set(self, key: Key, value: U) -> None:
        ...

    async def a_get(self, key: Key) -> U:
        ...

    async def a_contains(self, key: Key) -> bool:
        ...

@dataclass
class ValueMappedAsyncCache(AsyncCacheProtocol[Key, U], Generic[Key, T, U]):
    src: AsyncCacheProtocol[Key, U]
    a_mapper: Callable[[U], Awaitable[T]]
    a_inverse_mapper: Callable[[T], Awaitable[U]]

    async def a_set(self, key: Key, value: T) -> None:
        _value = await self.a_mapper(value)
        await self.src.a_set(key, _value)

    async def a_get(self, key: Key) -> U:
        _value = await self.src.a_get(key)
        return await self.a_inverse_mapper(_value)

    async def a_contains(self, key: Key) -> bool:
        return await self.src.a_contains(key)


@dataclass
class BlockingDictAsyncCache(AsyncCacheProtocol[Key, U]):
    """
    A simple in-memory cache using a dictionary. This is a blocking cache, so it is not suitable for high-throughput
    """
    src: dict[Key, U]

    async def a_set(self, key: Key, value: U) -> None:
        self.src[key] = value

    async def a_get(self, key: Key) -> U:
        return self.src[key]

    async def a_contains(self, key: Key) -> bool:
        return key in self.src


@dataclass
class ThreadPooledDictAsyncCache(AsyncCacheProtocol[Key, U]):
    """
    A simple cache using dict-like interface. This is a thread-pooled cache, so it is suitable for high-throughput
    (if the io is GIL-free)
    """
    src: MutableMapping[Key, U]
    n_threads: Optional[int] = field(default=None)

    def __post_init__(self):
        if self.n_threads is None:
            self.n_threads = os.cpu_count()
        self.pool = ThreadPoolExecutor(self.n_threads)

    async def a_set(self, key: Key, value: U) -> None:
        return await asyncio.get_event_loop().run_in_executor(self.pool, lambda: self.src.__setitem__(key, value))

    async def a_get(self, key: Key) -> U:
        return await asyncio.get_event_loop().run_in_executor(self.pool, lambda: self.src.__getitem__(key))

    async def a_contains(self, key: Key) -> bool:
        return await asyncio.get_event_loop().run_in_executor(self.pool, lambda: key in self.src)


@dataclass
class AsyncCachedFunctionV2(Generic[Key, U, P]):
    """非同期関数のキャッシュを提供するクラス。

    重要な設計ポイント:
    1. キャッシュキー:
        - キーはハッシュ可能な型である必要がある(文字列、数値、タプルなど)
        - 辞書などのハッシュ不可能な型をキーに含めることはできない
        - a_param_to_keyでパラメータからキーへの変換を行う

    2. エラーハンドリング:
        - キャッシュ読み込み時のエラーのみをリトライする
        - 関数実行時のエラーは上位に伝播させる
        - これにより、一時的なキャッシュの問題と、実際の関数のエラーを適切に区別する

    3. キャッシュの動作:
        - キャッシュミス時は関数を実行し、結果をキャッシュに保存
        - キャッシュヒット時は保存された値を返す
        - キャッシュ読み込みエラー時はa_is_error_to_retryに基づいてリトライを判断

    4. キャッシュの無効化:
        - キャッシュヒット時にa_invalidate_valueで値の妥当性を確認
        - 無効化条件を満たす場合、キャッシュを破棄して再計算
        - 無効化の理由をログに記録して追跡可能に

    Attributes:
        a_func: キャッシュする非同期関数
        a_param_to_key: 関数パラメータからキャッシュキーを生成する非同期関数
        cache: キャッシュの実装(AsyncCacheProtocolを実装したオブジェクト)
        a_is_error_to_retry: エラー発生時にリトライするかを判断する非同期関数。
            エラーをリトライする場合はその理由を文字列で返し、リトライしない場合は空文字列を返す。
        a_invalidate_value: キャッシュされた値の無効化条件を判断する非同期関数。
            引数は((args, kwargs), value)の形式で、argsとkwargsは元の関数呼び出しの引数、
            valueはキャッシュされている値。
            値を無効化する場合はその理由を文字列で返し、有効な場合は空文字列を返す。

    動作フロー:
    1. キャッシュキーの生成:
        a_param_to_keyを使用してキーを生成

    2. キャッシュの確認:
        - キャッシュミス → 関数を実行して結果をキャッシュ
        - キャッシュヒット → 以下のステップへ

    3. 値の取得と検証:
        a. キャッシュから値を取得
        b. a_invalidate_valueで値の妥当性を確認
        c. 無効な場合は再計算、有効な場合はキャッシュ値を返す

    4. エラー処理:
        - キャッシュ操作でエラー発生時、a_is_error_to_retryで判断
        - リトライ可能な場合は関数を再実行
        - それ以外はエラーを伝播
    """
    a_func: Callable[P, Awaitable[U]]
    a_param_to_key: Callable[P, Awaitable[Key]]
    cache: AsyncCacheProtocol[Key, U]
    a_is_error_to_retry: Callable[[Exception], Awaitable[str]]
    a_invalidate_value: Callable[[Tuple[P.args, P.kwargs], U], Awaitable[str]]

    async def _calc_cache_with_set(self, inputs: Tuple[P.args, P.kwargs], key: Key) -> U:
        value = await self.a_func(*inputs[0], **inputs[1])
        await self.cache.a_set(key, value)
        return value

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> U:
        key = await self.a_param_to_key(*args, **kwargs)

        if not await self.cache.a_contains(key):
            return await self._calc_cache_with_set((args, kwargs), key)
        try:
            value = await self.cache.a_get(key)
            if invalidate := await self.a_invalidate_value((args, kwargs), value):
                logger.warning(f"Invalidating cache for {key}. Reason: {invalidate}")
                return await self._calc_cache_with_set((args, kwargs), key)
            return value
        except Exception as e:
            handler = self.a_is_error_to_retry
            if handler is not None and (retry_msg := await handler(e)):
                logger.warning(f"Error occurred for {key}. Retrying msg: {retry_msg}")
                value = await self.a_func(*args, **kwargs)
                await self.cache.a_set(key, value)
                return value
            raise e
