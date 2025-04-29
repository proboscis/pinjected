from typing import TypeVar

from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.expr_util import Object
from pinjected.di.proxiable import DelegatedVar

T = TypeVar("T")


class IProxy(DelegatedVar[T]):
    def __init__(self, value: T) -> None:
        # IProxyの初期化
        super().__init__(__value__=Object(value), __cxt__=InjectedEvalContext)
