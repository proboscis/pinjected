import asyncio
from hashlib import sha256
from typing import TypeVar, Callable, Awaitable
import inspect

import jsonpickle
from returns.future import future_safe, FutureResultE
from returns.io import IOResultE, IOResult
from returns.pipeline import is_successful
from returns.result import safe, ResultE
from returns.unsafe import unsafe_perform_io

from pinjected import *
from pinjected.decoration import update_if_registered
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.util import get_code_location
from returns.maybe import Some

T = TypeVar('T')
U = TypeVar('U')

# pinjected-reviewer: ignore
@injected
def _async_batch_cached(
        injected_utils_default_hasher,
        logger,
        /,
        cache: dict,
        hasher: Callable[[T], str] = None
):
    """
    非同期バッチ処理のための内部キャッシュデコレータ実装。

    このデコレータは、バッチ処理の効率を向上させるために以下の機能を提供します：
    1. 入力アイテムごとにハッシュ値を計算し、キャッシュの有無を確認
    2. キャッシュが存在するアイテムはキャッシュから結果を取得
    3. キャッシュが存在しないアイテムのみを実際に計算
    4. 新しく計算した結果をキャッシュに保存
    5. すべてのアイテムの結果を元の順序で返却

    内部実装の特徴：
    - 依存性注入を使用してロガーとデフォルトハッシャーを取得
    - キャッシュミス時のログ出力機能
    - 可変長引数のバリデーション
    - 非同期処理のサポート

    :param injected_utils_default_hasher: デフォルトのハッシュ関数（依存性注入）
    :param logger: ロガーオブジェクト（依存性注入）
    :param cache: キャッシュとして使用する辞書オブジェクト
    :param hasher: カスタムハッシュ関数。指定しない場合はデフォルトのハッシュ関数が使用されます
    :return: デコレータ関数

    注意:
    - このデコレータは内部実装用です。外部からは async_batch_cached を使用してください
    - デコレートする関数は可変長引数（*args）を受け取る必要があります
    - デコレートする関数は非同期関数である必要があります
    """
    hasher = injected_utils_default_hasher if hasher is None else hasher

    def get_impl(func: Callable[[tuple[T]], Awaitable[list[U]]]):
        # funcの引数が*varargs（可変長引数）を持つことを確認
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        assert any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in params), \
            f"func must have *args parameter, but got {sig}"

        @future_safe
        async def safe_getitem(key):
            return await asyncio.to_thread(cache.__getitem__,key)

        async def impl(*items: list[T]) -> list[U]:
            # 1. 各アイテムのハッシュ値を計算
            keys = [hasher(i) for i in items]
            key_to_item = dict(zip(keys,items))
            # 2. 読み込みに失敗するものを特定
            loaded:list[IOResultE] = list(await asyncio.gather(*[safe_getitem(k) for k in keys]))
            io_results:dict[str,IOResultE] = dict(zip(keys,loaded))
            keys_to_calc = [k for k,v in io_results.items() if not is_successful(v)]
            for fk in keys_to_calc:
                logger.info(f"Cache miss: {key_to_item[fk]} {fk[:50]},{io_results[fk]}")

            # 3. キャッシュにないアイテムのみを計算
            inputs = [key_to_item[k] for k in keys_to_calc]
            if inputs:  # 計算が必要なアイテムがある場合のみ関数を実行
                results = await func(*inputs)
                # 4. 新しい結果をキャッシュに保存
                for k, r in zip(keys_to_calc, results):
                    cache[k] = r
                    io_results[k] = IOResult.from_value(r)
            # 5. すべての結果を返す（キャッシュ + 新規計算）
            return [unsafe_perform_io(io_results[k].unwrap()) for k in key_to_item.keys()]


        return impl

    return get_impl

def async_batch_cached(cache: IProxy[dict], hasher: Callable[[T], str] = None):
    """
    非同期バッチ処理用のキャッシュデコレータ。pinjectedフレームワークと統合されています。

    このデコレータは、バッチ処理の効率を向上させるために以下の機能を提供します：
    1. 入力アイテムごとにハッシュ値を計算し、キャッシュの有無を確認
    2. キャッシュが存在するアイテムはキャッシュから結果を取得
    3. キャッシュが存在しないアイテムのみを実際に計算
    4. 新しく計算した結果をキャッシュに保存
    5. すべてのアイテムの結果を元の順序で返却

    使用例:
    ```python
    @async_batch_cached(cache=dict())
    @injected
    async def process_items(*items):
        return [await process(item) for item in items]
    ```

    :param cache: IProxy[dict] キャッシュとして使用する辞書オブジェクト。pinjectedのIProxyとして提供する必要があります。
    :param hasher: Callable[[T], str] | None カスタムハッシュ関数。指定しない場合はデフォルトのJSON基準のハッシュ関数が使用されます。
    :return: デコレータ関数
    
    注意:
    - デコレートする関数は可変長引数（*args）を受け取る必要があります
    - デコレートする関数は非同期関数である必要があります
    - 返り値は入力と同じ順序で返される必要があります
    """
    parent_frame = inspect.currentframe().f_back
    "we need to update the global design binding"

    def impl(f: IProxy):
        res = _async_batch_cached(cache=cache, hasher=hasher)(f)
        res.__is_async_function__ = True
        return update_if_registered(
            Injected.ensure_injected(f),
            Injected.ensure_injected(res),
            Some(BindMetadata(code_location=Some(get_code_location(parent_frame))))
        )

    return impl


@async_batch_cached(cache=dict())
@injected
async def _test_function_batch_cached(*items):
    return items


run_test_function_batch_cached: IProxy = _test_function_batch_cached(1, 2, 3, 4, 5)

__meta_design__ = design(
    overrides=design(
        injected_utils_default_hasher=lambda item: sha256(jsonpickle.dumps(item).encode()).hexdigest()
    )
)
