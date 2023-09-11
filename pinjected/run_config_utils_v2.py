import asyncio
from dataclasses import dataclass
from typing import Coroutine

from pinjected import Injected, Design
from pinjected.helpers import get_design_path_from_var_path
from pinjected.module_var_path import load_variable_by_module_path


@dataclass
class RunInjected:
    var_path: str
    design_path: str = None

    def __post_init__(self):
        if self.design_path is None:
            self.design_path = get_design_path_from_var_path(self.var_path)

    def _var_design(self):
        var: Injected = Injected.ensure_injected(load_variable_by_module_path(self.var_path))
        design: Design = load_variable_by_module_path(self.design_path)
        return var, design

    def _get(self):
        var, design = self._var_design()
        return design.provide(var)

    def chain_call(self, *args, **kwargs):
        res = self._get()(*args, **kwargs)
        if isinstance(res, Coroutine):
            res = asyncio.run(res)
        return res

    def chain_get(self):
        res = self._get()
        if isinstance(res, Coroutine):
            res = asyncio.run(res)
        return res

    def get(self):
        from loguru import logger
        logger.info(f"injected get result\n{self.chain_get()}")

    def call(self, *args, **kwargs):
        from loguru import logger
        logger.info(f"injected get result\n{self.chain_call(*args, **kwargs)}")

    def visualize(self):
        from loguru import logger
        logger.info(f"visualizing {self.var_path} with design {self.design_path}")
        var, design = self._var_design()
        design.to_vis_graph().show_injected_html(var)
