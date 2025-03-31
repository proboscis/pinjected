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
from returns.maybe import Some
from returns.result import safe, Result

from pinjected.module_inspector import ModuleVarSpec


class PinjectedConfigurationLoadFailure(Exception):
    """Raised when a pinjected configuration file (.pinjected.py) fails to load."""
    pass


from pinjected import design, Injected, Design, Designed, EmptyDesign, injected
from pinjected.cli_visualizations import design_rich_tree
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE
from pinjected.di.design_spec.protocols import DesignSpec
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.helpers import get_design_path_from_var_path
from pinjected.logging_helper import disable_internal_logging
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path
from pinjected.notification import notify
from pinjected.pinjected_logging import logger
from pinjected.run_config_utils import load_variable_from_script
from pinjected.run_helpers.mp_util import run_in_process
from pinjected.schema.handlers import PinjectedHandleMainException, PinjectedHandleMainResult
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.v2.callback import IResolverCallback
from pinjected.v2.keys import StrBindKey
from pinjected.visualize_di import DIGraph


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
            overrides = design()
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
    from pinjected.pinjected_logging import logger
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


def run_anything(
        cmd: str,
        var_path: str,
        design_path: Optional[str],
        overrides=design(),
        return_result=False,
        notify=lambda msg, *args, **kwargs: notify(msg, *args, **kwargs),
):
    # with disable_internal_logging():
    # design, meta_overrides, var = asyncio.run(a_get_run_context(design_path, var_path))
    cxt: RunContext = asyncio.run(a_get_run_context(design_path, var_path))
    design = cxt.get_final_design()
    logger.info(f"loaded design:{design}")
    logger.info(f"meta_overrides:{cxt.meta_overrides}")
    logger.info(f"running target:{var_path} with design {design_path}")
    # tree_str = design_rich_tree(design, cxt.var)
    # logger.info(f"Dependency Tree:\n{tree_str}")

    # logger.info(f"running target:{var} with cmd {cmd}, args {args}, kwargs {kwargs}")
    # logger.info(f"metadata obtained from pinjected: {meta}")

    # here we load the defaults and overrides from the user's environment
    # design = load_user_default_design() + design + load_user_overrides_design()

    res = None

    # @logger.catch(exclude="pinjected")
    try:
        if cmd == "get":
            res = cxt.add_design(overrides).run()
        elif cmd == "fire":
            raise RuntimeError("fire is deprecated. use get.")
        elif cmd == "visualize":
            logger.info(f"visualizing {var_path} with design {design_path}")
            logger.info(f"deps:{cxt.var.dependencies()}")
            DIGraph(design).show_injected_html(cxt.var)
        elif cmd == "export_visualization_html":
            logger.info(f"exporting visualization {var_path} with design {design_path}")
            logger.info(f"deps:{cxt.var.dependencies()}")
            dst = Path(".pinjected_visualization/")
            res_html: Path = DIGraph(design).save_as_html(cxt.var, dst)
            logger.info(f"exported to {res_html}")
        elif cmd == "to_script":
            d = design + design(__root__=Injected.bind(cxt.var))
            print(DIGraph(d).to_python_script(var_path, design_path=design_path))
        elif cmd == "json-graph":
            import json
            logger.info(f"generating JSON graph for {var_path} with design {design_path}")
            if hasattr(cxt.var, 'dependencies'):
                logger.info(f"deps:{cxt.var.dependencies()}")
            json_graph = DIGraph(
                design,
                spec = Some(cxt.src_meta_context.spec_trace.accumulated)
            ).to_json_with_root_name(cxt.src_var_spec.var_path.split(".")[-1],list(cxt.var.dependencies()))
            print(json.dumps(json_graph, indent=2))
        elif cmd == "describe":
            generate_dependency_graph_description(var_path, design_path, cxt, design)
    except Exception as e:
        with logger.contextualize(tag="PINJECTED RUN FAILURE"):
            if PinjectedHandleMainException.key in design:
                logger.warning(
                    f"Run failed with error:\n{e}\nHandling with {PinjectedHandleMainException.key.name} ...")
                from pinjected import IProxy
                handler: IProxy[PinjectedHandleMainException] = injected(PinjectedHandleMainException.key.name)
                handling = handler(e)
                handled: Optional[str] = asyncio.run(cxt.a_provide(handling, show_debug=False))
                if handled:
                    logger.info(f"exception is handled by {PinjectedHandleMainException.key.name}")
                raise e
            else:
                logger.debug(f"Run failed. you can handle the exception with {PinjectedHandleMainException.key.name}")
                notify(f"Run failed with error:\n{e}", sound="Frog")
                raise e
    with logger.contextualize(tag="PINJECTED RUN SUCCESS"):
        logger.success(f"pinjected run result:\n{pformat(res)}")
        if PinjectedHandleMainResult.key in design:
            from pinjected import IProxy
            handler: IProxy[PinjectedHandleMainResult] = injected(PinjectedHandleMainResult.key.name)
            handling = handler(res)
            asyncio.run(cxt.a_provide(handling, show_debug=False))
        else:
            logger.info(f"Note: The result can be handled with {PinjectedHandleMainResult.key.name}")
            notify(f"Run result:\n{str(res)[:100]}")
        if return_result:
            logger.info(f"delegating the result to fire..")
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
    from rich.console import Console
    from rich.tree import Tree
    from rich.panel import Panel
    from rich.text import Text
    from returns.maybe import Nothing, Some
    import re
    
    logger.info(f"generating dependency graph description for {var_path} with design {design_path}")
    
    digraph = DIGraph(
        design,
        spec = Some(cxt.src_meta_context.spec_trace.accumulated)
    )
    root_name = cxt.src_var_spec.var_path.split(".")[-1]
    
    if hasattr(cxt.var, 'dependencies'):
        logger.info(f"deps:{cxt.var.dependencies()}")
        deps = list(cxt.var.dependencies())
        edges = digraph.to_edges(root_name, deps)
    else:
        logger.error(f"Object {root_name} doesn't have dependencies method")
        raise AttributeError(f"Object {root_name} must have a dependencies() method to use the describe command")
    
    console = Console()
    root_tree = Tree(f"[bold blue]{root_name}[/bold blue]")
    
    processed_nodes = set()
    
    def format_maybe(value):
        """Format Maybe objects (Some/Nothing) to clean representation."""
        if value == Nothing:
            return "None"
        elif hasattr(value, 'unwrap'):  # Check if it's a Some instance
            return format_value(value.unwrap())
        return format_value(value)
    
    def format_value(value):
        """Format values to clean representation."""
        if value is None:
            return "None"
        
        value_str = str(value)
        
        if isinstance(value, dict) and 'documentation' in value:
            if value['documentation']:
                doc = value['documentation']
                doc = doc.replace('\\n', '\n')
                doc = re.sub(r'[ \t]+', ' ', doc)
                value['documentation'] = doc
                value_str = str(value)
        
        return value_str
    
    def add_node_to_tree(parent_tree, edge):
        if edge.key in processed_nodes:
            return
        
        processed_nodes.add(edge.key)
        
        metadata_text = ""
        if edge.metadata:
            metadata_text = f"\n[dim]Metadata:[/dim] {format_maybe(edge.metadata)}"
        
        spec_text = ""
        if edge.spec:
            spec_text = f"\n[dim]Spec:[/dim] {format_maybe(edge.spec)}"
        
        node_text = f"[bold green]{edge.key}[/bold green]{metadata_text}{spec_text}"
        
        node_tree = parent_tree.add(node_text)
        
        for dep in edge.dependencies:
            node_tree.add(f"[yellow]→ {dep}[/yellow]")
            
            for child_edge in edges:
                if child_edge.key == dep:
                    add_node_to_tree(node_tree, child_edge)
    
    for edge in edges:
        if edge.key == root_name:
            for dep in edge.dependencies:
                root_tree.add(f"[yellow]→ {dep}[/yellow]")
                
                for child_edge in edges:
                    if child_edge.key == dep:
                        add_node_to_tree(root_tree, child_edge)
    
    console.print("\n[bold]Dependency Graph Description:[/bold]")
    console.print(root_tree)
    console.print("\n[bold]Edge Details:[/bold]")
    
    console.print(Panel(f"[bold blue]{root_name}[/bold blue]", title="Root Node"))
    
    for edge in edges:
        if edge.key != root_name:  # Skip root as it's already shown
            title = Text(edge.key, style="bold green")
            content = Text()
            
            content.append("\nDependencies: ")
            if edge.dependencies:
                content.append(", ".join(edge.dependencies), style="yellow")
            else:
                content.append("None", style="dim")
            
            if edge.metadata:
                content.append("\nMetadata: ")
                content.append(format_maybe(edge.metadata))
            
            if edge.spec:
                content.append("\nSpec: ")
                spec_value = format_maybe(edge.spec)
                
                if "documentation" in spec_value:
                    try:
                        import ast
                        spec_dict = ast.literal_eval(spec_value)
                        doc = spec_dict.get('documentation', '')
                        
                        if doc:
                            clean_spec = {k: v for k, v in spec_dict.items() if k != 'documentation'}
                            content.append(str(clean_spec))
                            
                            console.print(Panel(content, title=title))
                            
                            console.print(Panel(doc, title=f"{edge.key} Documentation", border_style="blue"))
                            continue
                    except Exception as e:
                        logger.debug(f"Failed to parse documentation: {e}")
                        logger.debug(f"Spec value: {spec_value}")
                
                content.append(spec_value)
            
            console.print(Panel(content, title=title))


def call_impl(call_args, call_kwargs, cxt, design):
    args = call_args or []
    kwargs = call_kwargs or {}
    var = Injected.ensure_injected(cxt.var).proxy
    logger.info(f"run_injected call with args:{args}, kwargs:{kwargs}")
    res = _run_target(design, var(*args, **kwargs), cxt)
    return res


@dataclass(frozen=True)
class RunContext:
    src_meta_context: MetaContext
    design: Design
    meta_overrides: Design
    var: Injected
    src_var_spec: ModuleVarSpec
    provision_callback: Optional[IResolverCallback]
    overrides: Design = field(default_factory=design)

    def add_design(self, design: Design):
        return replace(self, design=self.design + design)

    def add_overrides(self, overrides: Design):
        return replace(self, overrides=self.overrides + overrides)

    def get_final_design(self):
        return self.design + self.meta_overrides + self.overrides

    async def a_provide(self, tgt, show_debug=True):
        final_design = self.get_final_design()
        if show_debug:
            logger.info(f"loaded design:{final_design}")
            logger.info(f"meta_overrides:{self.meta_overrides}")
            logger.info(f"running target:{self.var} with design {final_design}")
            tree_str = design_rich_tree(final_design, self.var)
            logger.info(f"Dependency Tree:\n{tree_str}")
        async with TaskGroup() as tg:
            dd = final_design + design(__task_group__=tg)
            resolver = AsyncResolver(
                dd,
                callbacks=[self.provision_callback] if self.provision_callback else [],
                spec=self.src_meta_context.spec_trace.accumulated
            )
            _res = await resolver.provide(tgt)

            if isinstance(_res, Awaitable):
                _res = await _res
        await resolver.destruct()
        return _res

    async def _a_run(self):
        return await self.a_provide(self.var)

    async def a_run(self):
        return await self._a_run()

    def run(self):
        return asyncio.run(self.a_run())


async def a_resolve_design(design_path, meta_cxt: MetaContext) -> Design:
    """Resolve design from design_path and meta_context"""
    if design_path is None:
        logger.info(f"using design from final_design in meta_context:{meta_cxt}")
        return await meta_cxt.a_final_design
    else:
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
        contextual_overrides = DESIGN_OVERRIDES_STORE.get_overrides(ModuleVarPath(var_path))
        meta_overrides += contextual_overrides  # obtain internal hooks from the meta_design
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
            except AttributeError as ae:
                logger.warning(f"{design_name} is not defined in {path}.")
                raise PinjectedConfigurationLoadFailure(
                    f"Failed to load '{design_name}' from {path}: {design_name} is not defined in the file.")
            except Exception as e:
                import traceback

                logger.warning(f"failed to load design from {path}:{design_name}.")
                logger.warning(e)
                logger.warning(traceback.format_exc())
                raise PinjectedConfigurationLoadFailure(f"Failed to load '{design_name}' from {path}: {str(e)}")
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
    try:
        design_result = load_design_from_paths(find_dot_pinjected(), "default_design") + _load_design(
            design_path).value_or(
            design()
        )
        # logger.info(f"loaded default design:{pformat(design_result.bindings.keys())}")
        for k, v in design_result.bindings.items():
            logger.info(f"User overrides :{k} -> {type(v)}")
        return design_result
    except PinjectedConfigurationLoadFailure as e:
        if 'default_design is not defined' in str(e):
            logger.debug(f"default_design is not defined in {design_path}")
            return design()
        raise




@safe
def _load_design(design_path):
    if design_path == "":
        return EmptyDesign
    pairs = design_path.split("|")
    res = design()
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
    try:
        design_obj = load_design_from_paths(find_dot_pinjected(), "overrides_design") + _load_design(design_path).value_or(
            design()
        )
        logger.info(f"loaded override design:{pformat(design_obj.bindings.keys())}")
        return design_obj
    except PinjectedConfigurationLoadFailure as e:
        if 'overrides_design is not defined' in str(e):
            logger.debug(f"overrides_design is not defined in {design_path}")
            return design()
        raise e
