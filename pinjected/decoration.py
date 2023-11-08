from typing import Callable

from returns.maybe import Maybe, Nothing

from pinjected import Injected
from pinjected.di.bindings import BindMetadata, InjectedBind
from pinjected.di.injected import PartialInjectedFunction, InjectedFunction


def update_if_registered(
        func: Injected[Callable],
        updated: Injected[Callable],
        meta: Maybe[BindMetadata] = Nothing,
        binding_key: str = None
):
    match func:
        case PartialInjectedFunction(InjectedFunction(tgt, mapping)):
            res = PartialInjectedFunction(updated)
            from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
            key = binding_key if binding_key is not None else tgt.__name__
            IMPLICIT_BINDINGS[key] = InjectedBind(
                res,
                metadata=meta
            )
            return res
        case _:
            return updated
