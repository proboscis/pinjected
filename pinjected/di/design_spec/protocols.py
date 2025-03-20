from typing import Protocol, TypeVar, Callable, runtime_checkable

from returns.future import FutureResultE
from returns.maybe import Maybe

from pinjected.v2.keys import IBindKey, StrBindKey

T = TypeVar('T')

ValidatorType = Callable[[IBindKey, T], FutureResultE[str]]
SpecDocProviderType = Callable[[IBindKey], FutureResultE[str]]


class BindSpec(Protocol[T]):
    """
    A specification of a binding, to provide documentation, and validation for a design.
    """

    """
    Called when an object is instantiated, before providing it to the consumer.
    Success[str] means validation pass.
    Failure[str] means validation failed.
    """
    validator: Maybe[ValidatorType]
    """
    Called when user requests for information about the binding
    """
    spec_doc_provider: Maybe[SpecDocProviderType]

@runtime_checkable
class DesignSpec(Protocol):
    def __add__(self, other: "DesignSpec") -> "DesignSpec":
        pass

    def get_spec(self, key: IBindKey) -> Maybe[BindSpec]:
        pass

    @staticmethod
    def empty():
        from pinjected.di.design_spec.impl import DesignSpecImpl
        return DesignSpecImpl({})

    @staticmethod
    def new(**specs:BindSpec):
        from pinjected.di.design_spec.impl import DesignSpecImpl
        return DesignSpecImpl({StrBindKey(k):v for k,v in specs.items()})
