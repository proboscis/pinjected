from dataclasses import dataclass
from typing import Dict, List, Union

from pydantic import BaseModel, validator

from pinject_design import Design, Injected, Designed
from pinject_design.module_inspector import ModuleVarSpec


class IdeaRunConfiguration(BaseModel):
    name: str
    script_path: str
    interpreter_path: str
    arguments: List[str]
    working_dir: str
    # we need dependency python librarrie's paths.
    # this needs to be checked from intellij side

class IdeaRunConfigurations(BaseModel):
    configs: Dict[str, List[IdeaRunConfiguration]]


@dataclass
class MetaContext:
    trace: List[ModuleVarSpec]
    accumulated: Design


@dataclass
class RunnablePair:
    target: Injected
    design: Design

    def run(self):
        return self.design.to_graph()[self.target]

    def save_html(self, name: str = None, show=True):
        if name is None:
            name = "graph.html"
        self.design.to_vis_graph().save_as_html(self.target, name, show=show)


class RunnableValue(BaseModel):
    """
    I think it is easier to make as much configuration as possible on this side.
    """
    src: ModuleVarSpec[Union[Injected, Designed]]
    design_path: str

    @validator('src')
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

