import asyncio
import io
import os
import sys
import traceback
from collections.abc import Awaitable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field, replace
from pathlib import Path
from pprint import pformat

import cloudpickle
from beartype import beartype
from returns.maybe import Some
from returns.result import safe

from pinjected.module_inspector import ModuleVarSpec


class PinjectedConfigurationLoadFailure(Exception):
    """Raised when a pinjected configuration file (.pinjected.py) fails to load."""


class PinjectedRunFailure(Exception):
    """Raised when a pinjected run fails."""


from pinjected import Design, Designed, EmptyDesign, Injected, design, injected  # noqa: E402
from pinjected.cli_visualizations import design_rich_tree  # noqa: E402
from pinjected.compatibility.task_group import TaskGroup  # noqa: E402
from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE  # noqa: E402
from pinjected.di.proxiable import DelegatedVar  # noqa: E402
from pinjected.helper_structure import MetaContext  # noqa: E402
from pinjected.helpers import get_design_path_from_var_path  # noqa: E402
from pinjected.logging_helper import disable_internal_logging  # noqa: E402
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path  # noqa: E402
from pinjected.notification import notify  # noqa: E402
from pinjected.pinjected_logging import logger  # noqa: E402
from pinjected.module_var_path import load_variable_from_script  # noqa: E402
from pinjected.run_helpers.mp_util import run_in_process  # noqa: E402
from pinjected.schema.handlers import (  # noqa: E402
    PinjectedHandleMainException,
    PinjectedHandleMainResult,
)
from pinjected.v2.async_resolver import AsyncResolver  # noqa: E402
from pinjected.v2.callback import IResolverCallback  # noqa: E402
from pinjected.v2.keys import StrBindKey  # noqa: E402
from pinjected.visualize_di import DIGraph  # noqa: E402


def run_injected(cmd, var_path, design_path: str = None, *args, **kwargs):  # noqa: PLR0912, RUF013
    no_notification = kwargs.pop("no_notification", False)
    if no_notification:
        notify_impl = lambda msg, *args, **kwargs: None  # noqa: E731
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
            overrides = design()
        try:
            if design_path is None:
                design_path = get_design_path_from_var_path(var_path)
        except ValueError:
            logger.warning(
                f"No default design paths found for {var_path}. Proceeding with None design path."
            )
        logger.info(
            f"run_injected called with cmd:{cmd}, var_path:{var_path}, design_path:{design_path}, args:{args}, kwargs:{kwargs}"
        )
    return run_anything(
        cmd,
        var_path,
        design_path=design_path,
        return_result=return_result,
        overrides=overrides,
        notify=notify_impl,
    )


@beartype
async def a_run_target(var_path: str, design_path: str | None = None):
    print(f"running target:{var_path} with design {design_path}")
    cxt: RunContext = await a_get_run_context(design_path, var_path)
    # design, meta_overrides, var = await a_get_run_context(design_path, var_path)
    design = cxt.design + cxt.meta_overrides
    try:
        async with TaskGroup() as tg:
            dd = design + design(__task_group__=tg)
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
    import cloudpickle

    from pinjected.pinjected_logging import logger

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
    from pinjected.pinjected_logging import logger

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


def run_anything(  # noqa: C901, PLR0912, PLR0915
    cmd: str,
    var_path: str,
    design_path: str | None,
    overrides=design(),
    return_result=False,
    notify=lambda msg, *args, **kwargs: notify(msg, *args, **kwargs),
):
    # with disable_internal_logging():
    # design, meta_overrides, var = asyncio.run(a_get_run_context(design_path, var_path))
    cxt: RunContext = asyncio.run(a_get_run_context(design_path, var_path))
    cxt = cxt.add_overrides(overrides)
    D = cxt.get_final_design()
    logger.info(f"loaded design:{D}")
    logger.info(f"meta_overrides:{cxt.meta_overrides}")
    logger.info(f"running target:{var_path} with design {design_path}")
    res = None
    if cmd == "get":

        async def task(cxt):
            return await cxt.a_run()
    elif cmd == "visualize":

        async def task(cxt):
            logger.info(f"visualizing {var_path} with design {design_path}")
            logger.info(f"deps:{cxt.var.dependencies()}")
            from pinjected.di.injected import Injected
            from pinjected import design as design_func

            enhanced_design = D + design_func(
                __design__=Injected.pure(D),
                __resolver__=Injected.pure("__resolver__"),
            )
            DIGraph(enhanced_design).show_injected_html(cxt.var)
    elif cmd == "export_visualization_html":

        async def task(cxt):
            logger.info(f"exporting visualization {var_path} with design {design_path}")
            logger.info(f"deps:{cxt.var.dependencies()}")
            dst = Path(".pinjected_visualization/")
            from pinjected.di.injected import Injected
            from pinjected import design as design_func

            enhanced_design = D + design_func(
                __design__=Injected.pure(D),
                __resolver__=Injected.pure("__resolver__"),
            )
            res_html: Path = DIGraph(enhanced_design).save_as_html(cxt.var, dst)
            logger.info(f"exported to {res_html}")
    elif cmd == "to_script":

        async def task(cxt):
            logger.info(f"exporting visualization {var_path} with design {design_path}")
            logger.info(f"deps:{cxt.var.dependencies()}")
            from pinjected.di.injected import Injected
            from pinjected import design as design_func

            d = D + design_func(
                __root__=Injected.bind(cxt.var),
                __design__=Injected.pure(D),
                __resolver__=Injected.pure("__resolver__"),
            )
            print(DIGraph(d).to_python_script(var_path, design_path=design_path))
    elif cmd == "json-graph":

        async def task(cxt):
            import json

            logger.info(
                f"generating JSON graph for {var_path} with design {design_path}"
            )
            if hasattr(cxt.var, "dependencies"):
                logger.info(f"deps:{cxt.var.dependencies()}")
            json_graph = DIGraph(
                D, spec=Some(cxt.src_meta_context.spec_trace.accumulated)
            ).to_json_with_root_name(
                cxt.src_var_spec.var_path.split(".")[-1], list(cxt.var.dependencies())
            )
            print(json.dumps(json_graph, indent=2))
    elif cmd == "describe":

        async def task(cxt):
            generate_dependency_graph_description(var_path, design_path, cxt, D)
    elif cmd == "describe_json":

        async def task(cxt):
            generate_dependency_chain_json(var_path, design_path, cxt, D)
    else:
        raise Exception(f"unknown command: {cmd}")
    res = asyncio.run(a_run_with_notify(cxt, task, notify))
    if return_result:
        return res


def generate_dependency_graph_description(var_path, design_path, cxt, design):
    """
    Generate a human-readable description of the dependency graph for a variable.
    Uses to_edges() of DIGraph to show dependencies with their documentation.

    :param var_path: the path to the variable to describe
    :param design_path: the path to the design to be used
    :param cxt: the run context containing variable and design information
    :param design: the design object to use for dependency resolution
    """
    from returns.maybe import Some

    from pinjected.dependency_graph_description import (
        DependencyGraphDescriptionGenerator,
    )
    from pinjected.visualize_di import DIGraph

    logger.info(
        f"generating dependency graph description for {var_path} with design {design_path}"
    )

    from pinjected.di.injected import Injected
    from pinjected import design as design_func

    if design is None:
        raise ValueError("design parameter cannot be None. Pass a valid Design object.")
    
    enhanced_design = design + design_func(
        __design__=Injected.pure(design),
        __resolver__=Injected.pure("__resolver__"),
    )
    digraph = DIGraph(
        enhanced_design, spec=Some(cxt.src_meta_context.spec_trace.accumulated)
    )
    root_name = cxt.src_var_spec.var_path.split(".")[-1]

    if hasattr(cxt.var, "dependencies"):
        logger.info(f"deps:{cxt.var.dependencies()}")
        deps = list(cxt.var.dependencies())

        generator = DependencyGraphDescriptionGenerator(digraph, root_name, deps)
        generator.generate()
    else:
        logger.error(f"Object {root_name} doesn't have dependencies method")
        raise AttributeError(
            f"Object {root_name} must have a dependencies() method to use the describe command"
        )


def generate_dependency_chain_json(var_path, design_path, cxt, design):
    """
    Generate a JSON representation of the dependency chain for an IProxy variable.

    :param var_path: the path to the IProxy variable to describe
    :param design_path: the path to the design to be used
    :param cxt: the run context containing variable and design information
    :param design: the design object to use for dependency resolution
    """
    from returns.maybe import Some
    import json

    from pinjected.visualize_di import DIGraph
    from pinjected.di.injected import Injected
    from pinjected import design as design_func

    logger.info(
        f"generating dependency chain JSON for {var_path} with design {design_path}"
    )

    # Create enhanced design with resolver
    enhanced_design = design + design_func(
        __design__=Injected.pure(design),
        __resolver__=Injected.pure("__resolver__"),
    )

    # Create DIGraph with spec information
    digraph = DIGraph(
        enhanced_design, spec=Some(cxt.src_meta_context.spec_trace.accumulated)
    )

    root_name = cxt.src_var_spec.var_path.split(".")[-1]

    if hasattr(cxt.var, "dependencies"):
        logger.info(f"deps:{cxt.var.dependencies()}")
        deps = list(cxt.var.dependencies())

        # Build edges using DIGraph's to_edges method
        edges = digraph.to_edges(root_name, deps)

        # Create JSON structure
        result = {
            "root": root_name,
            "module_var_path": var_path,
            "dependency_chain": [edge.to_json_repr() for edge in edges],
        }

        # Print JSON output
        print(json.dumps(result, indent=2))
    else:
        error_msg = f"Object {root_name} must have a dependencies() method to use the describe-json command"
        logger.error(f"Object {root_name} doesn't have dependencies method")
        # Return error as JSON for IDE consumption
        error_result = {
            "error": error_msg,
            "root": root_name,
            "module_var_path": var_path,
        }
        print(json.dumps(error_result, indent=2))


def call_impl(call_args, call_kwargs, cxt, design):
    args = call_args or []
    kwargs = call_kwargs or {}
    var = Injected.ensure_injected(cxt.var).proxy
    logger.info(f"run_injected call with args:{args}, kwargs:{kwargs}")
    res = _run_target(design, var(*args, **kwargs), cxt)  # noqa: F821
    return res


class PinjectedRunFailure(Exception):
    """Raised when a pinjected run fails."""


@dataclass(frozen=True)
class RunContext:
    src_meta_context: MetaContext
    design: Design
    meta_overrides: Design
    var: Injected
    src_var_spec: ModuleVarSpec
    provision_callback: IResolverCallback | None
    overrides: Design = field(default_factory=design)

    def add_design(self, design: Design):
        return replace(self, design=self.design + design)

    def add_overrides(self, overrides: Design):
        return replace(self, overrides=self.overrides + overrides)

    def get_final_design(self):
        return self.design + self.meta_overrides + self.overrides

    async def a_provide(self, tgt, show_debug=True):  # noqa: C901, PLR0912
        final_design = self.get_final_design()
        if show_debug:
            logger.info(f"loaded design:{final_design}")
            logger.info(f"meta_overrides:{self.meta_overrides}")
            logger.info(f"running target:{self.var} with design {final_design}")

            # Combine binding sources from different origins
            binding_sources = {}

            # Module hierarchy bindings from MetaContext
            if hasattr(self.src_meta_context, "key_to_path"):
                binding_sources.update(self.src_meta_context.key_to_path)

            # Mark user default design bindings
            for key in self.meta_overrides.bindings:
                if key not in binding_sources or key in self.meta_overrides.bindings:
                    binding_sources[key] = "user default design"

            # Mark user override design bindings (these take precedence)
            for key in self.overrides.bindings:
                binding_sources[key] = "user overrides design"

            tree_str = design_rich_tree(final_design, self.var, binding_sources)
            logger.info(f"Dependency Tree:\n{tree_str}")
        dd = final_design
        resolver = AsyncResolver(
            dd,
            callbacks=[self.provision_callback] if self.provision_callback else [],
            spec=self.src_meta_context.spec_trace.accumulated,
        )
        _res = await resolver.provide(tgt)

        if isinstance(_res, Awaitable):
            _res = await _res

        from pinjected.di.partially_injected import PartiallyInjectedFunction

        if isinstance(_res, PartiallyInjectedFunction):
            logger.warning(
                f"You're directly requesting a function object '{self.src_var_spec.var_path}' which returns PartiallyInjectedFunction. "
                f"This is likely not what you intended. Instead, create an IProxy entrypoint variable and request it:\n\n"
                f"# Example:\n"
                f"# some.module.py\n"
                f"from pinjected import injected, IProxy\n"
                f"@injected\n"
                f"def something(dep1,/,arg):\n"
                f"    pass\n"
                f"entrypoint: IProxy = something('hello')\n\n"
                f"# Then request:\n"
                f"pinjected run some.module.entrypoint\n\n"
                f"Note: Only dependencies can be overridden in the 'pinjected run' command."
            )

        await resolver.destruct()
        return _res

    async def _a_run(self):
        return await self.a_provide(self.var)

    async def a_run(self):
        return await self._a_run()

    async def a_run_with_clean_stacktrace(self):
        return await self._a_run()

    def run(self):
        return asyncio.run(self.a_run())


async def a_run_with_notify(  # noqa: C901, PLR0912
    cxt: RunContext,
    a_run,
    notify=lambda msg, *args, **kwargs: notify(msg, *args, **kwargs),
):
    """
    A context manager that runs a function and notifies the result.
    :param notify: A function to notify the result.
    """
    D = cxt.get_final_design()
    res = None
    try:
        res = await a_run(cxt)
    except Exception as e:
        with logger.contextualize(tag="PINJECTED RUN FAILURE"):
            if PinjectedHandleMainException.key in D:
                logger.warning(
                    f"Run failed with error:\n{e}\nHandling with {PinjectedHandleMainException.key.name} ..."
                )
                from pinjected import IProxy

                handler: IProxy[PinjectedHandleMainException] = injected(
                    PinjectedHandleMainException.key.name
                )
                handling = handler(cxt, e)
                try:
                    handled: str | None = await cxt.a_provide(
                        handling, show_debug=False
                    )
                    if handled:
                        logger.info(
                            f"exception is handled by {PinjectedHandleMainException.key.name}"
                        )
                except Exception as handle_error:
                    raise handle_error from e
                raise e
            logger.debug(
                f"Run failed. you can handle the exception with {PinjectedHandleMainException.key.name}"
            )
            notify(f"Run failed with error:\n{e}", sound="Frog")
            raise
    with logger.contextualize(tag="PINJECTED RUN SUCCESS"):
        logger.success(f"pinjected run result:\n{pformat(res)}")
        if PinjectedHandleMainResult.key in D:
            from pinjected import IProxy

            try:
                handler: IProxy[PinjectedHandleMainResult] = injected(
                    PinjectedHandleMainResult.key.name
                )
                handling = handler(cxt, res)
                await cxt.a_provide(handling, show_debug=False)
            except Exception:
                logger.exception(
                    f"failed to handle result with {PinjectedHandleMainResult.key.name}"
                )
                logger.warning(f"still returning the result")
        else:
            logger.info(
                f"Note: The result can be handled with {PinjectedHandleMainResult.key.name}"
            )
            notify(f"Run result:\n{str(res)[:100]}")
    return res


async def a_resolve_design(design_path, meta_cxt: MetaContext) -> Design:
    """Resolve design from design_path and meta_context"""
    if design_path is None:
        logger.info(f"using design from final_design in meta_context:{meta_cxt}")
        return await meta_cxt.a_final_design
    design_obj = load_variable_by_module_path(design_path)
    if not isinstance(design_obj, Design):
        logger.warning(f"{design_path} is not a Design")
    from pinjected import Injected

    logger.debug(f"loaded {design_path}")
    if isinstance(design_obj, Injected):
        logger.warning(f"{design_path} is an Injected")
        # if the design is injected, we need to resolve it.
        r = AsyncResolver(await meta_cxt.a_final_design)
        design_obj = await r.provide(design_obj)
    logger.debug(f"design:{design_obj}")
    return design_obj


async def a_get_run_context(design_path, var_path) -> RunContext:
    with logger.contextualize(tag="get_run_context"):
        var_spec = ModuleVarPath(var_path).to_spec()
        meta = safe(getattr)(var_spec.var, "__runnable_metadata__").value_or({})
        if not isinstance(meta, dict):
            meta = {}
        meta_overrides = meta.get("overrides", design())
        meta_cxt: MetaContext = await MetaContext.a_gather_bindings_with_legacy(
            ModuleVarPath(var_path).module_file_path
        )
        design_obj = await a_resolve_design(design_path, meta_cxt)
        # here, actually the loaded variable maybe an instance of Designed.
        # but it can also be a DelegatedVar[Designed] or a DelegatedVar[Injected] hmm,
        # what would be the operation between Designed + Designed? run them on separate process, or in the same session?
        match var_spec.var:
            case Injected() | DelegatedVar():
                var = Injected.ensure_injected(var_spec.var)
            case Designed():
                design_obj += var_spec.var.design
                var = var_spec.var.internal_injected
            case _:
                var = var_spec.var

        meta_design = design(overrides=design()) + meta_cxt.accumulated
        meta_resolver = AsyncResolver(meta_design)
        meta_overrides = (await meta_resolver.provide("overrides")) + meta_overrides
        # here we add __design__ directly to overrides.
        meta_overrides += meta_cxt.accumulated
        # add overrides from with block
        contextual_overrides = DESIGN_OVERRIDES_STORE.get_overrides(
            ModuleVarPath(var_path)
        )
        meta_overrides += (
            contextual_overrides  # obtain internal hooks from the meta_design
        )
        if StrBindKey("provision_callback") in meta_design:
            provision_callback = await meta_resolver.provide("provision_callback")
        else:
            provision_callback = None
        design_obj = load_user_default_design() + design_obj
        meta_overrides += load_user_overrides_design()
        return RunContext(
            src_meta_context=meta_cxt,
            design=design_obj,
            meta_overrides=meta_overrides,
            var=var,
            src_var_spec=var_spec,
            provision_callback=provision_callback,
        )


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


def load_design_from_paths(paths, design_name):
    res = design()
    for path in paths:
        if path.exists():
            logger.info(f"loading design from {path}:{design_name}.")
            try:
                res += load_variable_from_script(path, design_name)
            except AttributeError:
                logger.warning(f"{design_name} is not defined in {path}.")
                raise PinjectedConfigurationLoadFailure(
                    f"Failed to load '{design_name}' from {path}: {design_name} is not defined in the file."
                )
            except Exception as e:
                import traceback

                logger.warning(f"failed to load design from {path}:{design_name}.")
                logger.warning(e)
                logger.warning(traceback.format_exc())
                raise PinjectedConfigurationLoadFailure(
                    f"Failed to load '{design_name}' from {path}: {e!s}"
                )
        else:
            # logger.debug(f"design file {path} does not exist.")
            pass
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
    try:
        design_result = load_design_from_paths(
            find_dot_pinjected(), "default_design"
        ) + _load_design(design_path).value_or(design())
        # logger.info(f"loaded default design:{pformat(design_result.bindings.keys())}")
        return design_result
    except PinjectedConfigurationLoadFailure as e:
        if "default_design is not defined" in str(e):
            # logger.debug(f"default_design is not defined in {design_path}")
            return design()
        raise


@safe
def _load_design(design_path):
    if design_path == "":
        return EmptyDesign
    pairs = design_path.split("|")
    res = design()  # noqa: F823
    for pair in pairs:
        if pair == "":
            continue
        script_path, var_name = pair.split(":")
        design = load_variable_from_script(script_path, var_name)
        if design is not None:
            assert isinstance(design, Design), (
                f"design loaded from {script_path}:{var_name} is not a Design instance, but is {type(design)}."
            )
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
    try:
        design_obj = load_design_from_paths(
            find_dot_pinjected(), "overrides_design"
        ) + _load_design(design_path).value_or(design())
        logger.info(f"loaded override design:{pformat(design_obj.bindings.keys())}")
        return design_obj
    except PinjectedConfigurationLoadFailure as e:
        if "overrides_design is not defined" in str(e):
            # logger.debug(f"overrides_design is not defined in {design_path}")
            return design()
        raise e
