from typing import Optional, Set, Union
from pinjected import AsyncResolver, Design
from pinjected.di.proxiable import DelegatedVar
from pinjected.compatibility.task_group import TaskGroup

def register_fixtures_from_design(
    design_obj: Union[Design, DelegatedVar[Design]],
    scope: str = ...,
    prefix: str = ...,
    include: Optional[Set[str]] = ...,
    exclude: Optional[Set[str]] = ...,
) -> DesignFixtures: ...

class ResolverContext:
    def __init__(self, resolver: AsyncResolver, task_group: TaskGroup): ...
    async def close(self): ...

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
