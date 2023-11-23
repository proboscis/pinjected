from dataclasses import dataclass
from loguru import logger
from pathlib import Path
from typing import Dict, List

from pinjected import Design, Injected, instances
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import load_variable_by_module_path


@dataclass
class IdeaRunConfiguration:
    name: str
    script_path: str
    interpreter_path: str
    arguments: List[str]
    working_dir: str


@dataclass
class IdeaRunConfigurations:
    configs: Dict[str, List[IdeaRunConfiguration]]


@dataclass
class MetaContext:
    trace: List[ModuleVarSpec[Design]]
    accumulated: Design

    @staticmethod
    def gather_from_path(file_path: Path, meta_design_name: str = "__meta_design__"):
        if not isinstance(file_path, Path):
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
    @property
    def final_design(self):
        acc = self.accumulated
        design = load_variable_by_module_path(acc.provide('default_design_paths')[0])
        return design + acc.provide('overrides')


@dataclass
class RunnablePair:
    target: Injected
    design: Design

    def run(self):
        logger.info(f"running {self.target}")
        result = self.design.to_graph()[self.target]
        logger.info(f"result: {result}")
        return result

    def save_html(self, name: str = None, show=True):
        if name is None:
            name = "graph.html"
        self.design.to_vis_graph().save_as_html(self.target, name, show=show)


try:
    # pydantic over version 2
    from pydantic import field_validator
except ImportError:
    from pydantic import validator as field_validator

__meta_design__ = instances(
    default_design_paths=["pinjected.helper_structure.__meta_design__"]
)
