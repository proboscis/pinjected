import asyncio
import io
import os
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, replace, field
from pathlib import Path
from pprint import pformat
from typing import Awaitable, Optional

import cloudpickle
from beartype import beartype
from loguru import logger
from returns.result import safe, Result

from pinjected import instances, Injected, Design, providers, Designed, EmptyDesign
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.helpers import get_design_path_from_var_path
from pinjected.logging_helper import disable_internal_logging
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path
from pinjected.notification import notify
from pinjected.run_config_utils import load_variable_from_script
from pinjected.run_helpers.mp_util import run_in_process
from pinjected.v2.callback import IResolverCallback
from pinjected.v2.keys import StrBindKey
from pinjected.v2.resolver import AsyncResolver
from pinjected.visualize_di import DIGraph
from pinjected.cli_visualizations import design_rich_tree


def run_injected(cmd, var_path, design_path: str = None, *args, **kwargs):
    no_notification = kwargs.pop("no_notification", False)
    if no_notification:
        notify_impl = lambda msg, *args, **kwargs: None
    else:
        notify_impl = notify
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
        notify=notify_impl,
    )


@beartype
async def a_run_target(var_path: str, design_path: Optional[str] = None):
    print(f"running target:{var_path} with design {design_path}")
    cxt: RunContext = await a_get_run_context(design_path, var_path)
    # design, meta_overrides, var = await a_get_run_context(design_path, var_path)
    design = cxt.design + cxt.meta_overrides
    try:
        async with TaskGroup() as tg:
            dd = design + instances(__task_group__=tg)
            resolver = AsyncResolver(
                dd, callbacks=[cxt.provision_callback] if cxt.provision_callback else []
            )
            _res = await resolver.provide(cxt.var)
            if isinstance(_res, Awaitable):
                _res = await _res
        print(f"run_target {var_path} result:{_res}")
    finally:
        await resolver.destruct()
        print(f"destructed resolver")
    return _res


def _remote_test(var_path: str):
    from loguru import logger
    import cloudpickle

    stdout = io.StringIO()
    stderr = io.StringIO()
    logger.remove()
    logger.add(stderr)
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            res = asyncio.run(a_run_target(var_path=var_path))
            trace_str = None
    except Exception as e:
        res = str(e)
        trace_str = traceback.format_exc()
        logger.error(f"remote test failed with {e}")
    logger.remove()
    logger.add(sys.stderr)
    final_tuple = cloudpickle.dumps(
        (stdout.getvalue(), stderr.getvalue(), trace_str, res)
    )
    return final_tuple


_enter_count = 0


@beartype
async def a_run_target__mp(var_path: str):
    global _enter_count
    from loguru import logger

    _enter_count += 1
    if _enter_count == 1:
        logger.remove()
    res = await run_in_process(_remote_test, var_path)
    # I want to stream the stdout and stderr to the caller. but how?
    # I can return a set of Future and
    res = cloudpickle.loads(res)
    if _enter_count == 1:
        logger.add(sys.stderr)
    _enter_count -= 1
    return res




def run_anything(
    cmd: str,
    var_path: str,
    design_path: Optional[str],
    overrides=instances(),
    return_result=False,
    call_args=None,
    call_kwargs=None,
    notify=lambda msg, *args, **kwargs: notify(msg, *args, **kwargs),
):
    from loguru import logger

    # with disable_internal_logging():
    # design, meta_overrides, var = asyncio.run(a_get_run_context(design_path, var_path))
    cxt: RunContext = asyncio.run(a_get_run_context(design_path, var_path))
    design = cxt.design + cxt.meta_overrides + overrides
    logger.info(f"loaded design:{design}")
    logger.info(f"meta_overrides:{cxt.meta_overrides}")
    logger.info(f"running target:{var_path} with design {design_path}")
    tree_str = design_rich_tree(design, cxt.var)
    logger.info(f"Dependency Tree:\n{tree_str}")

    # logger.info(f"running target:{var} with cmd {cmd}, args {args}, kwargs {kwargs}")
    # logger.info(f"metadata obtained from pinjected: {meta}")

    # here we load the defaults and overrides from the user's environment
    # design = load_user_default_design() + design + load_user_overrides_design()

    res = None

    try:
        if cmd == "get":
            res = cxt.add_design(overrides).run()
        elif cmd == "fire":
            raise RuntimeError("fire is deprecated. use get.")
        elif cmd == "visualize":
            from loguru import logger

            logger.info(f"visualizing {var_path} with design {design_path}")
            logger.info(f"deps:{cxt.var.dependencies()}")
            DIGraph(design).show_injected_html(cxt.var)
        elif cmd == "export_visualization_html":
            from loguru import logger

            logger.info(f"exporting visualization {var_path} with design {design_path}")
            logger.info(f"deps:{cxt.var.dependencies()}")
            dst = Path(".pinjected_visualization/")
            res_html: Path = DIGraph(design).save_as_html(cxt.var, dst)
            logger.info(f"exported to {res_html}")

        elif cmd == "to_script":
            from loguru import logger

            d = design + providers(__root__=cxt.var)
            print(DIGraph(d).to_python_script(var_path, design_path=design_path))
    except Exception as e:
        import traceback

        notify(f"Run failed with error:\n{e}", sound="Frog")
        # trace = traceback.format_exc()
        # Path(f"run_failed_{var_path}.err.log").write_text(str(e) + "\n" + trace)
        # from rich.console import Console
        # console = Console()
        # console.print_exception(show_locals=False)
        raise e
    logger.success(f"pinjected run result:\n{pformat(res)}")
    notify(f"Run result:\n{str(res)[:100]}")
    if return_result:
        logger.info(f"delegating the result to fire..")
        return res


def call_impl(call_args, call_kwargs, cxt, design):
    args = call_args or []
    kwargs = call_kwargs or {}
    var = Injected.ensure_injected(cxt.var).proxy
    logger.info(f"run_injected call with args:{args}, kwargs:{kwargs}")
    res = _run_target(design, var(*args, **kwargs), cxt)
    return res


@dataclass(frozen=True)
class RunContext:
    design: Design
    meta_overrides: Design
    var: Injected
    provision_callback: Optional[IResolverCallback]
    overrides: Design = field(default_factory=instances)

    def add_design(self, design: Design):
        return replace(self, design=self.design + design)

    def add_overrides(self, overrides: Design):
        return replace(self, overrides=self.overrides + overrides)

    async def a_run(self):
        final_design = self.design + self.meta_overrides + self.overrides
        logger.info(f"loaded design:{final_design}")
        logger.info(f"meta_overrides:{self.meta_overrides}")
        logger.info(f"running target:{self.var} with design {final_design}")
        tree_str = design_rich_tree(final_design, self.var)
        logger.info(f"Dependency Tree:\n{tree_str}")
        async with TaskGroup() as tg:
            dd = final_design + instances(__task_group__=tg)
            resolver = AsyncResolver(
                dd,
                callbacks=[self.provision_callback] if self.provision_callback else [],
            )
            _res = await resolver.provide(self.var)

            if isinstance(_res, Awaitable):
                # logger.info(f"awaiting awaitable")
                _res = await _res
        await resolver.destruct()
        return _res

    def run(self):
        return asyncio.run(self.a_run())


async def a_get_run_context(design_path, var_path) -> RunContext:
    loaded_var = load_variable_by_module_path(var_path)
    meta = safe(getattr)(loaded_var, "__runnable_metadata__").value_or({})
    if not isinstance(meta, dict):
        meta = {}
    meta_overrides = meta.get("overrides", instances())
    meta_cxt: MetaContext = await MetaContext.a_gather_from_path(
        ModuleVarPath(var_path).module_file_path
    )
    design = await a_resolve_design(design_path, meta_cxt)
    # here, actually the loaded variable maybe an instance of Designed.
    # but it can also be a DelegatedVar[Designed] or a DelegatedVar[Injected] hmm,
    # what would be the operation between Designed + Designed? run them on separate process, or in the same session?
    match (var := load_variable_by_module_path(var_path)):
        case Injected() | DelegatedVar():
            var = Injected.ensure_injected(var)
        case Designed():
            design += var.design
            var = var.internal_injected
    """
            I need to get the design overrides from with context and add it to the overrides
            """
    meta_design = instances(overrides=instances()) + meta_cxt.accumulated
    meta_resolver = AsyncResolver(meta_design)
    meta_overrides = (await meta_resolver.provide("overrides")) + meta_overrides
    # add overrides from with block
    contextual_overrides = DESIGN_OVERRIDES_STORE.get_overrides(ModuleVarPath(var_path))
    meta_overrides += contextual_overrides  # obtain internal hooks from the meta_design
    if StrBindKey("provision_callback") in meta_design:
        provision_callback = await meta_resolver.provide("provision_callback")
    else:
        provision_callback = None
    design = load_user_default_design() + design
    meta_overrides += load_user_overrides_design()
    return RunContext(design, meta_overrides, var, provision_callback)


async def a_resolve_design(design_path, meta_cxt):
    if design_path is None:
        if StrBindKey("default_design_paths") in meta_cxt.accumulated:
            design_paths = await AsyncResolver(meta_cxt.accumulated).provide(
                "default_design_paths"
            )
            if design_paths:
                design: Design = load_variable_by_module_path(design_paths[0])
            else:
                design: Design = EmptyDesign
        else:
            design: Design = EmptyDesign
    else:
        design: Design = load_variable_by_module_path(design_path)
    return design


def find_dot_pinjected():
    # 1. load the .pinjected.py at home directory
    # 2. load the .pinjected.py at current directory
    # hmm, we are currently only looking at the home and current directory.
    home_dot_pinjected = Path("~/.pinjected.py").expanduser().absolute()
    current_dot_pinjected = Path(".pinjected.py").absolute()
    return home_dot_pinjected, current_dot_pinjected


@safe
def load_design_from_paths(paths, design_name) -> Result:
    res = instances()
    for path in paths:
        if path.exists():
            logger.info(f"loading design from {path}:{design_name}.")
            try:
                res += load_variable_from_script(path, design_name)
            except AttributeError as ae:
                logger.warning(f"{design_name} is not defined in {path}.")
            except Exception as e:
                import traceback

                logger.warning(f"failed to load design from {path}:{design_name}.")
                logger.warning(e)
                logger.warning(traceback.format_exc())
        else:
            logger.debug(f"design file {path} does not exist.")
    return res


def load_user_default_design() -> Design:
    """
    This function loads user specific environment data from a python file.
    the syntax is :
    /path/to/python/file.py:design_variable_name
    example:
    /home/user/design.py:my_design
    :return:
    """
    design_path = os.environ.get("PINJECTED_DEFAULT_DESIGN_PATH", "")
    design = load_design_from_paths(find_dot_pinjected(), "default_design").value_or(
        instances()
    ) + _load_design(design_path).value_or(instances())
    logger.info(f"loaded default design:{pformat(design.bindings.keys())}")
    return design


@safe
def _load_design(design_path):
    if design_path == "":
        return EmptyDesign
    pairs = design_path.split("|")
    res = instances()
    for pair in pairs:
        if pair == "":
            continue
        script_path, var_name = pair.split(":")
        design = load_variable_from_script(script_path, var_name)
        if design is not None:
            assert isinstance(
                design, Design
            ), f"design loaded from {script_path}:{var_name} is not a Design instance, but is {type(design)}."
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
    design_path = os.environ.get("PINJECTED_OVERRIDE_DESIGN_PATH", "")
    design = load_design_from_paths(find_dot_pinjected(), "overrides_design").value_or(
        instances()
    ) + _load_design(design_path).value_or(instances())
    logger.info(f"loaded override design:{pformat(design.bindings.keys())}")
    return design
