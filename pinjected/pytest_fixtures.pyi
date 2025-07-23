from typing import Optional, Set, Union
from pinjected import Design
from pinjected.di.proxiable import DelegatedVar

def register_fixtures_from_design(
    design_obj: Union[Design, DelegatedVar[Design]],
    scope: str = ...,
    prefix: str = ...,
    include: Optional[Set[str]] = ...,
    exclude: Optional[Set[str]] = ...,
) -> DesignFixtures: ...

class SharedTestState:
    def __init__(self) -> None: ...
    async def close(self) -> None: ...

class DesignFixtures:
    def __init__(
        self,
        design_obj: Union[Design, DelegatedVar[Design]],
        caller_file: Optional[str] = ...,
    ): ...
    def register(
        self, binding_name: str, scope: str = ..., fixture_name: Optional[str] = ...
    ) -> None: ...
    def register_all(
        self,
        scope: str = ...,
        prefix: str = ...,
        include: Optional[Set[str]] = ...,
        exclude: Optional[Set[str]] = ...,
    ) -> None: ...
