from typing import Callable

from returns.maybe import Maybe, Nothing

from pinjected import Injected
from pinjected.di.injected import PartialInjectedFunction, InjectedFunction
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey


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
            key = StrBindKey(binding_key) if binding_key is not None else StrBindKey(tgt.__name__)
            IMPLICIT_BINDINGS[key] = BindInjected(
                res,
                _metadata=meta
            )
            return res
        case _:
            return updated
