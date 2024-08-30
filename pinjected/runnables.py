from dataclasses import dataclass
from pathlib import Path
from typing import List

from pydantic import validator as field_validator

from pinjected import Injected, Designed
from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.proxiable import DelegatedVar
from pinjected.module_inspector import ModuleVarSpec, inspect_module_for_type
from beartype import beartype

@beartype
def get_runnables(module_path:Path) -> List[ModuleVarSpec]:
    def accept(name, tgt):
        match (name, tgt):
            case (n, _) if n.startswith("provide"):
                return True
            case (_, Injected()):
                return True
            case (_, Designed()):
                return True
            case (_, DelegatedVar(value, cxt)) if cxt == InjectedEvalContext:
                return True
            case (_, DelegatedVar(value, cxt)):
                return False
            case (_, item) if hasattr(item, "__runnable_metadata__") and isinstance(item.__runnable_metadata__, dict):
                return True
            case _:
                return False

    runnables = inspect_module_for_type(module_path, accept)
    return runnables


@dataclass
class RunnableValue:
    """
    I think it is easier to make as much configuration as possible on this side.
    """
    src: ModuleVarSpec
    design_path: str

    @field_validator('src')
    def validate_src_type(cls, value):
        match value:
            case ModuleVarSpec(Injected(), _):
                return value
            case ModuleVarSpec(Designed(), _):
                return value
            case _:
                raise ValueError(f"src must be an instance of Injected of ModuleVarSpec, but got {value}")

    class Config:
        arbitrary_types_allowed = True
