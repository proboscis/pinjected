from dataclasses import dataclass

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
    pass
