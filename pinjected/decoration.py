from typing import Callable

from returns.maybe import Maybe, Nothing

from pinjected import Injected
from pinjected.di.injected import PartialInjectedFunction
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.partially_injected import Partial
from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey



def update_if_registered(
        func: Injected[Callable],
        updated: Injected[Callable],
        meta: Maybe[BindMetadata] = Nothing,
        binding_key: str = None
):
    match func:
        #case Partial(InjectedFunction(tgt, mapping)):
        case p if isinstance(p, Partial):
            tgt = p.src_function
            #res = PartialInjectedFunction(updated)
            from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
            key = StrBindKey(binding_key) if binding_key is not None else StrBindKey(tgt.__name__)
            IMPLICIT_BINDINGS[key] = BindInjected(
                updated,
                _metadata=meta
            )
            return updated.proxy
        case _:
            return PartialInjectedFunction(updated)
