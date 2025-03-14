from dataclasses import dataclass

from beartype import beartype
from pinjected.pinjected_logging import logger
from pathlib import Path
from typing import Dict, List

from pinjected import Design, Injected, design, EmptyDesign
from pinjected.module_helper import walk_module_attr
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import load_variable_by_module_path, ModuleVarPath
from pinjected.v2.keys import StrBindKey
from pinjected.v2.async_resolver import AsyncResolver


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
        with logger.contextualize(tag="gather_meta_context"):
            from pinjected import design
            if not isinstance(file_path, Path):
                file_path = Path(file_path)
            designs = list(walk_module_attr(file_path, meta_design_name))
            designs.reverse()
            res = EmptyDesign
            overrides = EmptyDesign
            key_to_src = dict()
            for item in designs:
                logger.info(f"Added {meta_design_name} at :{item.var_path}")
                for k,v in item.var.bindings.items():
                    logger.info(f"Binding {k} from {item.var_path}")
                logger.trace(f"Current design bindings before: {res.bindings if hasattr(res, 'bindings') else 'EmptyDesign'}")
                # First collect any overrides
                overrides += (new_d:=await AsyncResolver(item.var).provide_or("overrides", EmptyDesign))
                for k,v in new_d.bindings.items():
                    key_to_src[k] = item.var_path
                # Then apply the design itself to ensure its bindings (like 'name') take precedence
                res = res + item.var
                logger.trace(f"Current design bindings after: {res.bindings if hasattr(res, 'bindings') else 'EmptyDesign'}")
            for k,v in key_to_src.items():
                logger.debug(f"Override Key {k} from {v}")
            # Apply overrides last
            res = res + design(overrides=overrides)
            return MetaContext(
                trace=designs,
                accumulated=res
            )

    @staticmethod
    @beartype
    def gather_from_path(file_path: Path, meta_design_name: str = "__meta_design__"):
        import asyncio
        return asyncio.run(MetaContext.a_gather_from_path(file_path, meta_design_name))

    @property
    def final_design(self):
        import asyncio
        return asyncio.run(self.a_final_design)

    @property
    async def a_final_design(self):
        with logger.contextualize(tag="design_preparation"):
            from pinjected.run_helpers.run_injected import load_user_default_design, load_user_overrides_design
            acc = self.accumulated
            # g = acc.to_resolver()
            r = AsyncResolver(acc)
            # First get any overrides from the accumulated design
            overrides = await r.provide_or('overrides', EmptyDesign)

            # Then load design from default_design_paths if specified
            if StrBindKey('default_design_paths') in acc:
                module_path = (await r['default_design_paths'])[0]
                design = load_variable_by_module_path(module_path)
            else:
                design = EmptyDesign

            # Apply in order: user defaults, loaded design, accumulated design (for name binding), overrides, user overrides
            return load_user_default_design() + design + acc + overrides + load_user_overrides_design()

    @staticmethod
    def load_default_design_for_variable(var: ModuleVarPath | str):
        from pinjected.run_helpers.run_injected import load_user_default_design, load_user_overrides_design
        if isinstance(var, str):
            var = ModuleVarPath(var)
        design = MetaContext.gather_from_path(var.module_file_path).final_design
        return design

    @staticmethod
    async def a_design_for_variable(var: ModuleVarPath | str):
        from pinjected.run_helpers.run_injected import load_user_default_design, load_user_overrides_design
        if isinstance(var, str):
            var = ModuleVarPath(var)
        design = await (await MetaContext.a_gather_from_path(var.module_file_path)).a_final_design
        return design


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

__meta_design__ = design(
    default_design_paths=["pinjected.helper_structure.__meta_design__"]
)
