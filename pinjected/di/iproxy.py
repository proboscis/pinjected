from typing import TypeVar

from pinjected import DelegatedVar
from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.expr_util import Object

T = TypeVar("T")


class IProxy(DelegatedVar[T]):
    def __new__(cls, item: T) -> 'IProxy[T]':
        # DelegatedVarのインスタンスを作成
        instance = super().__new__(cls)
        # インスタンスの初期化
        instance.__value__ = Object(item)
        instance.__cxt__ = InjectedEvalContext
        return instance
