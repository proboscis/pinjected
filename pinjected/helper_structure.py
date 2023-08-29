from loguru import logger
from pathlib import Path

from dataclasses import dataclass
from typing import Dict, List, Union

from pydantic import BaseModel, validator

from pinjected import Design, Injected, Designed
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import ModuleVarSpec


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
    trace: List[ModuleVarSpec[Design]]
    accumulated: Design

    @staticmethod
    def gather_from_path(file_path: Path, meta_design_name: str = "__meta_design__"):
        if not isinstance(file_path,Path):
            file_path = Path(file_path)
        designs = list(walk_module_attr(file_path, meta_design_name))
        designs.reverse()
        res = Design()
        overrides = Design()
        for item in designs:
            logger.debug(f"{meta_design_name} at :{item.var_path}")
            res = res + item.var
            try:
                overrides += item.var.provide("overrides")
            except Exception as e:
                logger.debug(f"{item.var_path} does not contain overrides")
        from pinjected import instances
        res += instances(
            overrides=overrides
        )

        return MetaContext(
            trace=designs,
            accumulated=res
        )




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


try:
    # pydantic over version 2
    from pydantic import field_validator
except ImportError:
    from pydantic import validator as field_validator


class RunnableValue(BaseModel):
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
