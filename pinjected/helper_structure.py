from dataclasses import dataclass
from loguru import logger
from pathlib import Path
from typing import Dict, List

from pinjected import Design, Injected, instances, EmptyDesign
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
    async def a_gather_from_path(file_path: Path, meta_design_name: str = "__meta_design__"):
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        designs = list(walk_module_attr(file_path, meta_design_name))
        designs.reverse()
        res = EmptyDesign
        overrides = EmptyDesign
        for item in designs:
            logger.debug(f"{meta_design_name} at :{item.var_path}")
            res = res + item.var
            try:

                overrides += await item.var.to_resolver()["overrides"]
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

    @staticmethod
    def gather_from_path(file_path: Path, meta_design_name: str = "__meta_design__"):
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        designs = list(walk_module_attr(file_path, meta_design_name))
        designs.reverse()
        res = EmptyDesign
        overrides = EmptyDesign
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

    @property
    async def a_final_design(self):
        from pinjected.run_helpers.run_injected import load_user_default_design, load_user_overrides_design
        acc = self.accumulated
        g = acc.to_resolver()
        module_path = (await g['default_design_paths'])[0]
        design = load_variable_by_module_path(module_path)
        return load_user_default_design() + design + (await g['overrides']) + load_user_overrides_design()


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
