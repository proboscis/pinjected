"""
pinjected用のテスト関数モジュール

このモジュールは、pinjectedを使用したテストを簡単に書くためのユーティリティ関数を提供します。
"""
import asyncio
import inspect
from typing import Awaitable

from pinjected import Injected, Design, EmptyDesign, instance
from pinjected import instances
from pinjected.compatibility.task_group import TaskGroup
from pinjected.helper_structure import MetaContext
from pinjected import AsyncResolver


def injected_pytest(override: Design = EmptyDesign):
    """
    pinjectedを使用したテスト関数を作成するデコレータ
    
    このデコレータは、pinjectedのインスタンスをpytestで実行可能なテスト関数に変換します。
    
    Args:
        override: テスト実行時に上書きするデザイン
        
    Returns:
        デコレータ関数
    
    使用例:
        @pinjected_test()
        def test_some_function(some_dependency):
            return some_dependency.do_something()
            
    Note:
        このデコレータは、呼び出し元のファイルパスを自動的に取得します。
    """
    def impl(func):
        return _to_pytest(instance(func), override, inspect.getmodule(func).__file__)

    return impl


def _to_pytest(p: Injected, override: Design, caller_file: str):
    """
    pinjectedのインスタンスをpytestで実行可能なテスト関数に変換する内部関数
    
    Args:
        p: pinjectedのインスタンス
        override: テスト実行時に上書きするデザイン
        caller_file: 呼び出し元のファイルパス
        
    Returns:
        pytest互換のテスト関数
    """

    var_path: str

    async def impl():
        mc: MetaContext = await MetaContext.a_gather_from_path(caller_file)
        design = await mc.a_final_design + override
        async with TaskGroup() as tg:
            design += instances(
                __task_group__=tg
            )
            resolver = AsyncResolver(
                design,
                callbacks=[]
            )
            try:
                res = await resolver.provide(Injected.ensure_injected(p))
            except Exception as e:
                raise e
            if isinstance(res, Awaitable):
                res = await res
        await resolver.destruct()
        return res

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