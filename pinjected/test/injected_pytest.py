"""
pinjected用のテスト関数モジュール

このモジュールは、pinjectedを使用したテストを簡単に書くためのユーティリティ関数を提供します。
"""

import asyncio
import inspect
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Union

from pinjected import AsyncResolver, Design, EmptyDesign, Injected, instance
from pinjected.compatibility.task_group import CompatibleExceptionGroup, TaskGroup
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext


def unwrap_exception_group(exc):
    """Unwrap exception from ExceptionGroup if it's the only exception."""
    while isinstance(exc, CompatibleExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc


UNWRAP_EXCEPTIONS = os.environ.get("PINJECTED_UNWRAP_EXCEPTIONS", "True").lower() in (
    "true",
    "1",
    "yes",
)


def injected_pytest(
    override_or_func: Union[Callable, Design, DelegatedVar[Design]] = EmptyDesign,
):
    """
    pinjectedを使用したテスト関数を作成するデコレータ

    このデコレータは、pinjectedのインスタンスをpytestで実行可能なテスト関数に変換します。

    Args:
        override_or_func:
            - When used without parentheses (@injected_pytest): the function being decorated
            - When used with parentheses: Design or DelegatedVar[Design] to override, or EmptyDesign

    Returns:
        デコレータ関数

    使用例:
        @injected_pytest()
        def test_some_function(some_dependency):
            return some_dependency.do_something()

        @injected_pytest
        def test_without_parentheses(some_dependency):
            return some_dependency.do_something()

        @injected_pytest(IProxy(my_design))
        def test_with_proxy(some_dependency):
            return some_dependency.do_something()

    Note:
        このデコレータは、呼び出し元のファイルパスを自動的に取得します。
    """
    # If the decorator is used without parentheses, override_or_func will be the function to decorate
    if callable(override_or_func) and not isinstance(
        override_or_func, (Design, DelegatedVar)
    ):
        func = override_or_func
        module = inspect.getmodule(func)
        if module is None or not hasattr(module, "__file__"):
            raise ValueError("Could not determine caller module for function")
        return _to_pytest(instance(func), EmptyDesign, module.__file__)

    # Otherwise, override_or_func should be a Design, DelegatedVar[Design], or EmptyDesign
    override = override_or_func
    assert isinstance(
        override, (Design, DelegatedVar)
    ), """override must be a Design or DelegatedVar[Design] instance. perhaps you forgot to use parentheses?
     For example: @injected_pytest. you must use @injected_pytest() or @injected_pytest(override=<design or proxy>)
     """

    def impl(func):
        module = inspect.getmodule(func)
        if module is None or not hasattr(module, "__file__"):
            raise ValueError("Could not determine caller module for function")
        return _to_pytest(instance(func), override, module.__file__)

    return impl


def _to_pytest(
    p: Injected, override: Union[Design, DelegatedVar[Design]], caller_file: str
):
    """
    pinjectedのインスタンスをpytestで実行可能なテスト関数に変換する内部関数

    Args:
        p: pinjectedのインスタンス
        override: テスト実行時に上書きするデザイン (Design, DelegatedVar[Design], or EmptyDesign)
        caller_file: 呼び出し元のファイルパス

    Returns:
        pytest互換のテスト関数
    """

    async def impl():
        caller_path = Path(caller_file)
        mc: MetaContext = await MetaContext.a_gather_bindings_with_legacy(caller_path)
        final_design = await mc.a_final_design

        # Resolve DelegatedVar[Design] if needed
        resolved_override = override
        if isinstance(override, DelegatedVar):
            # Create temporary resolver with current design context
            temp_resolver = AsyncResolver(final_design, callbacks=[])
            try:
                resolved_override = await temp_resolver.provide(override)
                if not isinstance(resolved_override, Design):
                    raise TypeError(
                        f"DelegatedVar must resolve to a Design instance, "
                        f"got {type(resolved_override).__name__}"
                    )
            finally:
                await temp_resolver.destruct()

        # Continue with resolved design
        design = final_design + resolved_override
        resolver = None
        try:
            async with TaskGroup() as tg:
                from pinjected import design as design_fn

                design += design_fn(__task_group__=tg)
                resolver = AsyncResolver(design, callbacks=[])
                res = await resolver.provide(Injected.ensure_injected(p))
                if isinstance(res, Awaitable):
                    res = await res
                return res
        except Exception as e:
            # doing this causes stack trace to become very deep. because it adds
            # `During handling of the above exception, another exception occurred:`
            # to the stack trace.
            # To prevent this, we throw from e.
            if UNWRAP_EXCEPTIONS:
                raise unwrap_exception_group(e) from None
            raise e
        finally:
            if resolver is not None:
                await resolver.destruct()

    def test_impl():
        return asyncio.run(impl())

    return test_impl


# テスト例
@injected_pytest()
def test_example(logger):
    """
    pinjected_testの使用例

    Args:
        logger: 注入されるロガー

    Returns:
        テスト結果
    """
    logger.info("pinjected_testの使用例")
    return "テスト成功"


# テスト例（括弧なし）
@injected_pytest
def test_example_no_parens(logger):
    """
    pinjected_testの使用例（括弧なし）

    Args:
        logger: 注入されるロガー
    """
    logger.info("pinjected_testの使用例（括弧なし）")
    return "テスト成功（括弧なし）"
