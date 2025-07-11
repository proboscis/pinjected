from pathlib import Path

from beartype import beartype
from pydantic import BaseModel, ConfigDict, field_validator

from pinjected import Designed, Injected
from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.proxiable import DelegatedVar
from pinjected.module_inspector import ModuleVarSpec, inspect_module_for_type


@beartype
def get_runnables(module_path: Path) -> list[ModuleVarSpec]:
    def accept(name, tgt):
        match (name, tgt):
            case (n, _) if n.startswith("provide"):
                return True
            case (_, Injected()):
                return True
            case (_, Designed()):
                return True
            case (_, DelegatedVar(_, cxt)) if cxt == InjectedEvalContext:
                return True
            case (_, DelegatedVar(_, _)):
                return False
            case (_, item) if hasattr(item, "__runnable_metadata__") and isinstance(
                item.__runnable_metadata__, dict
            ):
                return True
            case _:
                return False

    runnables = inspect_module_for_type(module_path, accept)
    return runnables


class RunnableValue(BaseModel):
    """
    I think it is easier to make as much configuration as possible on this side.
    """

    src: ModuleVarSpec
    design_path: str

    @field_validator("src")
    def validate_src_type(cls, value):
        match value:
            case ModuleVarSpec(Injected(), _):
                return value
            case ModuleVarSpec(Designed(), _):
                return value
            case _:
                raise ValueError(
                    f"src must be an instance of Injected of ModuleVarSpec, but got {value}"
                )

    model_config = ConfigDict(arbitrary_types_allowed=True)
