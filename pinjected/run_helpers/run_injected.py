from pathlib import Path

from pprint import pformat

import asyncio

from typing import Coroutine, Awaitable

from loguru import logger
from returns.result import safe

from pinjected import instances, Injected, Design, providers
from pinjected.helper_structure import MetaContext
from pinjected.helpers import get_design_path_from_var_path
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path
from pinjected.logging_helper import disable_internal_logging
from pinjected.notification import notify


def run_injected(
        cmd,
        var_path,
        design_path: str = None,
        *args,
        **kwargs
):
    logger.info(
        f"run_injected called with cmd:{cmd}, var_path:{var_path}, design_path:{design_path}, args:{args}, kwargs:{kwargs}")
    # TODO refactor to merge run_injected and run_anything
    with disable_internal_logging():
        if "return_result" in kwargs:
            return_result = kwargs.pop("return_result")
        else:
            return_result = False
        if "overrides" in kwargs:
            overrides = kwargs.pop("overrides")
        else:
            overrides = instances()
        if design_path is None:
            design_path = get_design_path_from_var_path(var_path)
        logger.info(
            f"run_injected called with cmd:{cmd}, var_path:{var_path}, design_path:{design_path}, args:{args}, kwargs:{kwargs}")
    return run_anything(cmd,
                        var_path,
                        design_path=design_path,
                        return_result=return_result,
                        overrides=overrides,
                        call_args=args,
                        call_kwargs=kwargs,
                        )


def run_anything(
        cmd: str,
        var_path,
        design_path,
        overrides=instances(),
        return_result=False,
        call_args=None,
        call_kwargs=None,
        notify=lambda msg, *args, **kwargs: notify(msg, *args, **kwargs)
):
    from loguru import logger
    with disable_internal_logging():

        loaded_var = load_variable_by_module_path(var_path)
        meta = safe(getattr)(loaded_var, "__runnable_metadata__").value_or({})
        if not isinstance(meta, dict):
            meta = {}
        overrides += meta.get("overrides", instances())

        meta_cxt: MetaContext = MetaContext.gather_from_path(ModuleVarPath(var_path).module_file_path)
        if design_path is None:
            design_path = meta_cxt.accumulated.provide("default_design_paths")[0]

        var: Injected = Injected.ensure_injected(load_variable_by_module_path(var_path))
        design: Design = load_variable_by_module_path(design_path)
        meta_design = instances(overrides=instances()) + meta_cxt.accumulated
        overrides += meta_design.provide("overrides")

    design = design + overrides
    logger.info(f"running target:{var} with {design_path} + {overrides}")
    logger.debug(design.keys())
    # logger.info(f"running target:{var} with cmd {cmd}, args {args}, kwargs {kwargs}")
    # logger.info(f"metadata obtained from pinjected: {meta}")

    res = None
    try:
        if cmd == 'call':
            args = call_args or []
            kwargs = call_kwargs or {}
            logger.info(f"run_injected call with args:{args}, kwargs:{kwargs}")
            res = design.provide(var)(*args, **kwargs)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected call result:\n{res}")
            if isinstance(res, Awaitable):
                async def impl():
                    return await res
                logger.info(f"awaiting awaitable")
                res = asyncio.run(impl())
        elif cmd == 'get':
            logger.info(f"providing...")
            res = design.provide(var)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            if isinstance(res, Awaitable):
                async def impl():
                    return await res
                logger.info(f"awaiting awaitable")
                res = asyncio.run(impl())
            if not return_result:
                logger.info(f"run_injected get result:\n{pformat(res)}")
        elif cmd == 'fire':
            res = design.provide(var)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected fire result:\n{res}")
        elif cmd == 'visualize':
            from loguru import logger
            logger.info(f"visualizing {var_path} with design {design_path}")
            logger.info(f"deps:{var.dependencies()}")
            design.to_vis_graph().show_injected_html(var)
        elif cmd == 'to_script':
            from loguru import logger
            d = design + providers(
                __root__=var
            )
            print(d.to_vis_graph().to_python_script(var_path, design_path=design_path))
    except Exception as e:
        import traceback
        notify(f"Run failed with error:\n{e}", sound='Frog')
        trace = traceback.format_exc()
        Path(f"run_failed_{var_path}.err.log").write_text(str(e) + "\n" + trace)
        from rich.console import Console
        console = Console()
        console.print_exception(show_locals=True)
        raise e
    notify(f"Run result:\n{str(res)[:100]}")
    if return_result:
        return res
