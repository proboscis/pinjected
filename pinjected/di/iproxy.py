from typing import TypeVar, Union, Any

from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.expr_util import Object
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.injected import Injected

T = TypeVar("T")


class IProxy(DelegatedVar[T]):
    def __init__(self, value: T) -> None:
        # IProxyの初期化
        super().__init__(__value__=Object(value), __cxt__=InjectedEvalContext)

    @staticmethod
    def tuple(*srcs: Union["IProxy", "Injected", Any]) -> "IProxy[tuple]":
        """
        Creates an IProxy wrapping a tuple from multiple sources.

        This method takes multiple arguments which can be IProxy instances, Injected instances,
        or plain values, and returns an IProxy that wraps a tuple containing all the values.

        :param srcs: Variable number of sources (IProxy, Injected, or plain values)
        :return: An IProxy instance wrapping a tuple

        Example:
        ```python
        a = IProxy(1)
        b = Injected.by_name('b')
        c = 3
        result = IProxy.tuple(a, b, c)  # IProxy wrapping tuple of (1, value_of_b, 3)
        ```
        """

        def _ensure_injected(src):
            if isinstance(src, IProxy):
                return src.eval()
            elif isinstance(src, Injected):
                return src
            else:
                return Injected.pure(src)

        injected_srcs = [_ensure_injected(s) for s in srcs]
        return IProxy(Injected.tuple(*injected_srcs))

    @staticmethod
    def dict(**kwargs: Union["IProxy", "Injected", Any]) -> "IProxy[dict]":
        """
        Creates an IProxy wrapping a dictionary from keyword arguments.

        This method takes keyword arguments where values can be IProxy instances,
        Injected instances, or plain values, and returns an IProxy that wraps a
        dictionary with the same keys and resolved values.

        :param kwargs: Keyword arguments where values are IProxy, Injected, or plain values
        :return: An IProxy instance wrapping a dictionary

        Example:
        ```python
        a = IProxy(1)
        b = Injected.by_name('b')
        result = IProxy.dict(key_a=a, key_b=b, key_c=3)
        # IProxy wrapping dict {'key_a': 1, 'key_b': value_of_b, 'key_c': 3}
        ```
        """

        def _ensure_injected(src):
            if isinstance(src, IProxy):
                return src.eval()
            elif isinstance(src, Injected):
                return src
            else:
                return Injected.pure(src)

        injected_kwargs = {k: _ensure_injected(v) for k, v in kwargs.items()}
        return IProxy(Injected.dict(**injected_kwargs))

    @staticmethod
    def list(*srcs: Union["IProxy", "Injected", Any]) -> "IProxy[list]":
        """
        Creates an IProxy wrapping a list from multiple sources.

        This method takes multiple arguments which can be IProxy instances, Injected instances,
        or plain values, and returns an IProxy that wraps a list containing all the values.

        :param srcs: Variable number of sources (IProxy, Injected, or plain values)
        :return: An IProxy instance wrapping a list

        Example:
        ```python
        a = IProxy(1)
        b = Injected.by_name('b')
        c = 3
        result = IProxy.list(a, b, c)  # IProxy wrapping list of [1, value_of_b, 3]
        ```
        """

        def _ensure_injected(src):
            if isinstance(src, IProxy):
                return src.eval()
            elif isinstance(src, Injected):
                return src
            else:
                return Injected.pure(src)

        injected_srcs = [_ensure_injected(s) for s in srcs]
        return IProxy(Injected.list(*injected_srcs))

    @staticmethod
    def procedure(*targets: Union["IProxy", "Injected"]) -> "IProxy":
        """
        Runs the targets in order and returns the last one.

        This is useful for running IProxy/Injected instances that perform side effects.
        The procedure executes all targets in sequence and returns the result of the last one.

        :param targets: Variable number of IProxy or Injected instances to execute
        :return: An IProxy instance wrapping the result of the last target

        Example:
        ```python
        setup = IProxy(setup_function())
        main_task = IProxy(main_function())
        cleanup = IProxy(cleanup_function())
        result = IProxy.procedure(setup, main_task, cleanup)
        # Executes setup, then main_task, then cleanup, and returns cleanup's result
        ```
        """

        def _ensure_injected(src):
            if isinstance(src, IProxy):
                return src.eval()
            elif isinstance(src, Injected):
                return src
            else:
                raise TypeError(
                    f"procedure only accepts IProxy or Injected instances, got {type(src)}"
                )

        if not targets:
            return IProxy(Injected.pure(None))

        injected_targets = [_ensure_injected(t) for t in targets]
        return IProxy(Injected.procedure(*injected_targets))
