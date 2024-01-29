import inspect
import os
from functools import wraps
from pathlib import Path

from pprint import pformat

import asyncio

from typing import Coroutine, Awaitable

from loguru import logger
from returns.result import safe

from pinjected import instances, Injected, Design, providers, Designed
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.helpers import get_design_path_from_var_path
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path
from pinjected.logging_helper import disable_internal_logging
from pinjected.notification import notify
from pinjected.run_config_utils import load_variable_from_script


def run_injected(
        cmd,
        var_path,
        design_path: str = None,
        *args,
        **kwargs
):
    logger.info(
        f"run_injected called with cmd:{cmd}, var_path:{var_path}, design_path:{design_path}, args:{args}, kwargs:{kwargs}"
    )
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
            f"run_injected called with cmd:{cmd}, var_path:{var_path}, design_path:{design_path}, args:{args}, kwargs:{kwargs}"
        )
    return run_anything(
        cmd,
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
        # here, actually the loaded variable maybe an instance of Designed.
        # but it can also be a DelegatedVar[Designed] or a DelegatedVar[Injected] hmm,
        # what would be the operation between Designed + Designed? run them on separate process, or in the same session?
        design: Design = load_variable_by_module_path(design_path)
        match (var := load_variable_by_module_path(var_path)):
            case Injected() | DelegatedVar():
                var = Injected.ensure_injected(var)
            case Designed():
                design: Design = load_variable_by_module_path(design_path)
                design += var.design
                var = var.internal_injected

        meta_design = instances(overrides=instances()) + meta_cxt.accumulated
        overrides += meta_design.provide("overrides")

    design += overrides
    logger.info(f"running target:{var} with {design_path} + {overrides}")
    logger.debug(design.keys())
    # logger.info(f"running target:{var} with cmd {cmd}, args {args}, kwargs {kwargs}")
    # logger.info(f"metadata obtained from pinjected: {meta}")

    # here we load the defaults and overrides from the user's environment
    design = load_user_default_design() + design + load_user_overrides_design()

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
            return_result = True
            res = design.provide(var)
            if isinstance(res, Coroutine):
                res = asyncio.run(res)
            logger.info(f"run_injected fire result:\n{res}")
            if inspect.iscoroutinefunction(res) or (hasattr(res, '__is_async__') and res.__is_async__):
                logger.info(f'{res} is a coroutine function, wrapping it with asyncio.run')
                src = res

                # @wraps(res)
                def synced(*args, **kwargs):
                    return asyncio.run(src(*args, **kwargs))

                res = synced
            else:
                logger.info(f"{res} is not a coroutine function.")
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
        # from rich.console import Console
        # console = Console()
        # console.print_exception(show_locals=False)
        raise e
    notify(f"Run result:\n{str(res)[:100]}")
    if return_result:
        return res


def find_dot_pinjected():
    # 1. load the .pinjected.py at home directory
    # 2. load the .pinjected.py at current directory
    # hmm, we are currently only looking at the home and current directory.
    home_dot_pinjected = Path("~/.pinjected.py").expanduser().absolute()
    current_dot_pinjected = Path(".pinjected.py").absolute()
    return home_dot_pinjected, current_dot_pinjected


def load_design_from_paths(paths, design_name) -> Design:
    res = instances()
    for path in paths:
        if path.exists():
            logger.info(f"loading design from {path}:{design_name}.")
            res += load_variable_from_script(path, design_name)
        else:
            logger.debug(f"design file {path} does not exist.")
    return res


def load_user_default_design():
    """
    This function loads user specific environment data from a python file.
    the syntax is :
    /path/to/python/file.py:design_variable_name
    example:
    /home/user/design.py:my_design
    :return:
    """
    design_path = os.environ.get('PINJECTED_DEFAULT_DESIGN_PATH', "")
    return load_design_from_paths(find_dot_pinjected(), "default_design") + _load_design(design_path)


def _load_design(design_path):
    if design_path == "":
        return Design()
    pairs = design_path.split("|")
    res = instances()
    for pair in pairs:
        if pair == "":
            continue
        script_path, var_name = pair.split(':')
        design = load_variable_from_script(script_path, var_name)
        if design is not None:
            assert isinstance(design,
                              Design), f"design loaded from {script_path}:{var_name} is not a Design instance, but is {type(design)}."
            res += design
    return res


def load_user_overrides_design():
    """
    This function loads user specific environment data from a python file.
    the syntax is :
    /path/to/python/file.py:design_variable_name
    example:
    /home/user/design.py:my_design
    :return:
    """
    design_path = os.environ.get('PINJECTED_OVERRIDE_DESIGN_PATH', "")
    return load_design_from_paths(find_dot_pinjected(), "overrides_design") + _load_design(design_path)
