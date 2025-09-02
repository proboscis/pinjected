from typing import Any
from pathlib import Path
from pinjected.di.design import Design, DesignSpec
from pinjected.di.injected import Injected
from pinjected.di.iproxy import IBindKey
from pinjected.v2.binds import DelegatedVar
from pinjected.module_path import ModuleVarSpec, ModuleVarPath

__design__: Any

def parse_pinjected_env_vars() -> dict[str, Any]: ...
def parse_kwargs_as_design_for_env(**kwargs) -> Any: ...
async def _a_resolve(tgt: Any | DelegatedVar | Injected) -> Any: ...

class IdeaRunConfigurations:
    configs: dict[str, list[IdeaRunConfiguration]]

class MetaContext:
    trace: list[ModuleVarSpec[Design]]
    accumulated: Design
    spec_trace: SpecTrace
    key_to_path: dict[IBindKey, str]
    async def a_gather_from_path(
        file_path: Path, meta_design_name: str = ...
    ) -> Any: ...
    async def a_gather_bindings_with_legacy(file_path) -> Any: ...
    def gather_from_path(file_path: Path, meta_design_name: str = ...) -> Any: ...
    def final_design(self) -> Any: ...
    async def a_final_design(self) -> Any: ...
    async def a_load_default_design_for_variable(var: ModuleVarPath | str) -> Any: ...
    def load_default_design_for_variable(var: ModuleVarPath | str) -> Any: ...
    async def a_design_for_variable(var: ModuleVarPath | str) -> Any: ...

class IdeaRunConfiguration:
    name: str
    script_path: str
    interpreter_path: str
    arguments: list[str]
    working_dir: str

class SpecTrace:
    trace: list[ModuleVarSpec[DesignSpec]]
    accumulated: DesignSpec
    async def a_gather_from_path(file_path: Path) -> Any: ...

class RunnablePair:
    target: Injected
    design: Design
    def run(self) -> Any: ...
    def save_html(self, name: str | None = ..., show=...) -> Any: ...
