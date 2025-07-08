from dataclasses import dataclass
from typing import Optional, Any

from returns.maybe import Maybe

from pinjected.di.metadata.location_data import CodeLocation


@dataclass
class BindMetadata:
    """
    This is the metadata of a bind.
    """

    code_location: Maybe[CodeLocation] = None
    """
    The location of the binding location, this will be used by the IDE to jump to the binding location.
    """

    protocol: Optional[Any] = None
    """
    The Protocol class that defines the interface for this binding.
    Used for type checking and IDE support.
    """

    is_callable_instance: bool = False
    """
    Indicates whether this instance returns a callable object that should be called directly.
    Used by the linter to allow direct calls to the returned value.
    """
