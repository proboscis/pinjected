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
    """
    A specification of bindings that provides validation and documentation.
    
    When adding specs together with the + operator, the right-hand spec takes precedence.
    This means if both specs have bindings for the same key, the binding from the
    right-hand side (the one being added) will be used.
    
    Example:
        spec1 + spec2  # spec2 takes precedence for any overlapping keys
    """
    def __add__(self, other: "DesignSpec") -> "DesignSpec":
        """
        Combine two design specs, with the right-hand side (other) taking precedence.
        If both specs define bindings for the same key, the binding from 'other' will be used.
        
        Args:
            other: The spec to add, which will override this spec for duplicate keys
            
        Returns:
            A new DesignSpec combining both specs with the right-hand side having precedence
        """
        pass

    def get_spec(self, key: IBindKey) -> Maybe[BindSpec]:
        """
        Get the binding specification for a given key.
        
        Args:
            key: The binding key to look up
            
        Returns:
            Maybe[BindSpec]: Just(spec) if the key is found, Nothing otherwise
        """
        pass

    @staticmethod
    def empty():
        from pinjected.di.design_spec.impl import DesignSpecImpl
        return DesignSpecImpl({})

    @staticmethod
    def new(**specs:BindSpec):
        from pinjected.di.design_spec.impl import DesignSpecImpl
        return DesignSpecImpl({StrBindKey(k):v for k,v in specs.items()})
