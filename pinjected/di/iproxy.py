from typing import TypeVar

from pinjected import DelegatedVar
from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.expr_util import Object

T = TypeVar("T")


class IProxy(DelegatedVar[T]):

    def __init__(self, value: T) -> None:
        # IProxyの初期化
        super().__init__(
            __value__ = Object(value),
            __cxt__ = InjectedEvalContext
        )
