import asyncio
import json
from inspect import isawaitable
from pathlib import Path

from pinjected import Design, Injected, design
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.tools.add_overload import process_file
from pinjected.exception_util import unwrap_exception_group
from pinjected.exceptions import DependencyResolutionError, DependencyValidationError
from pinjected.helper_structure import MetaContext
from pinjected.logging_helper import disable_internal_logging
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path
from pinjected.run_helpers.run_injected import (
    PinjectedRunFailure,
    RunContext,
    a_get_run_context,
    a_run_with_notify,
    load_user_default_design,
    load_user_overrides_design,
    run_injected,
)


def run(
    var_path: str = None,
    design_path: str = None,
    overrides: str = None,
    meta_context_path: str = None,
    base64_encoded_json: str = None,
    **kwargs,
):
    """
    load the injected variable from var_path and run it with a design at design_path.
    If design_path is not provided, it will be inferred from var_path.
    design_path is inferred by looking at the module of var_path for a __design__ attribute in __pinjected__.py files.
    This command will ask __design__ to provide 'default_design_paths', and uses the first one.
    if __design__ is not found, it will recursively look for a __design__ attribute in the parent module.
    by default, __design__ is accumulated from all parent modules.
    Therefore, if any parent module has a __design__ attribute with a 'default_design_paths' attribute, it will be used.

    :param var_path: the path to the variable to be injected: e.g. "my_module.my_var"
    :param design_path: the path to the design to be used: e.g. "my_module.my_design"
    :param ovr: a string that can be converted to an Design in some way. This will gets concatenated to the design.
    :param kwargs: overrides for the design. e.g. "api_key=1234"

    """
    if base64_encoded_json is not None:
        import base64
        import json

        data: dict = json.loads(base64.b64decode(base64_encoded_json).decode())
        var_path = data.pop("var_path")
        design_path = data.pop("design_path", None)
        overrides = data.pop("overrides", None)
        meta_context_path = data.pop("meta_context_path", None)
        kwargs = data

    async def a_prep():
        with disable_internal_logging():
            kwargs_overrides = parse_kwargs_as_design(**kwargs)
            ovr = design()
            if meta_context_path is not None:
                mc = await MetaContext.a_gather_bindings_with_legacy(
                    Path(meta_context_path)
                )
                ovr += await mc.a_final_design
            ovr += parse_overrides(overrides)
            ovr += kwargs_overrides
            cxt: RunContext = await a_get_run_context(design_path, var_path)
            cxt = cxt.add_overrides(ovr)

        async def task(cxt: RunContext):
            return await cxt.a_run_with_clean_stacktrace()

        res = await a_run_with_notify(cxt, task)
        from pinjected.pinjected_logging import logger

        logger.info(f"result:\n<pinjected>\n{res}\n</pinjected>")
        # now we've got the function to call

    return asyncio.run(a_prep())


def check_config():
    from pinjected.pinjected_logging import logger

    default: Design = load_user_default_design()
    overrides = load_user_overrides_design()
    logger.info(f"displaying default design bindings:")
    logger.info(default.table_str())
    logger.info(f"displaying overrides design bindings:")
    logger.info(overrides.table_str())


def parse_kwargs_as_design(**kwargs):
    """
    When a value is in '{pkg.varname}' format, we import the variable and use it as the value.
    """
    res = design()
    for k, v in kwargs.items():
        if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
            v = v[1:-1]
            loaded = load_variable_by_module_path(v)
            res += design(**{k: loaded})
        else:
            res += design(**{k: v})
    return res


def parse_overrides(overrides) -> Design:
    match overrides:
        case str() if (
            ":" in overrides
        ):  # this needs to be a complete call to run_injected, at least, we need to take arguments...
            # hmm at this point, we should just run a script ,right?
            design_path, var = overrides.split(":")
            resolved = run_injected("get", var, design_path, return_result=True)
            assert isinstance(resolved, Design), (
                f"expected {design_path} to be a design, but got {resolved}"
            )
            return resolved
        case str() as path:  # a path of a design/injected
            var = ModuleVarPath(path).load()
            if isinstance(var, Design):
                return var
            if isinstance(var, (Injected, DelegatedVar)):
                resolved = run_injected("get", path, return_result=True)
                assert isinstance(resolved, Design), (
                    f"expected {path} to be a design, but got {resolved}"
                )
                return resolved
        case None:
            return design()


def decode_b64json(text):
    import base64
    import json

    data: dict = json.loads(base64.b64decode(text).decode())
    return data


def call(
    var_path: str = None,
    design_path: str = None,
    overrides: str = None,
    meta_context_path: str = None,
    base64_encoded_json: str = None,
    call_kwargs_base64_json: str = None,
    **kwargs,
):
    """
    Now we have multiples similar functions and having hard time distinguishing them.
    run -> run_injected -> run_anything -> _run_target
    call -> run_injected -> run_anything -> call_impl
    # this is very complicated. we should clean this up.
    the cause I think is that 'run' has special kwargs and kwargs in common arguments.
    So first I need to separate options.
    - var_path
    - design_paths: list[str] to be accumulated
    - meta_context_path: str # a path to gather meta context from.
    """
    from pinjected.pinjected_logging import logger

    if base64_encoded_json is not None:
        data = decode_b64json(base64_encoded_json)
        var_path = data.pop("var_path")
        design_path = data.pop("design_path", None)
        overrides = data.pop("overrides", None)
        meta_context_path = data.pop("meta_context_path", None)
        kwargs = data
        logger.info(
            f"decoded {var_path=} {design_path=} {overrides=} {meta_context_path=} {kwargs=}"
        )

    # no_notification = kwargs.pop('pinjected_no_notification', False)
    async def a_prep():
        kwargs_overrides = parse_kwargs_as_design(**kwargs)
        ovr = design()
        if meta_context_path is not None:
            mc = await MetaContext.a_gather_bindings_with_legacy(
                Path(meta_context_path)
            )
            ovr += await mc.a_final_design
        ovr += parse_overrides(overrides)
        ovr += kwargs_overrides
        cxt: RunContext = await a_get_run_context(design_path, var_path)
        cxt = cxt.add_design(ovr)
        func = await cxt.a_run()
        if call_kwargs_base64_json is not None:
            call_kwargs = decode_b64json(call_kwargs_base64_json)
            logger.info(f"calling {var_path} with {call_kwargs}(decoded)")
            res = func(**call_kwargs)
            if isawaitable(res):
                res = await res
            logger.info(f"result:\n<pinjected>\n{res}\n</pinjected>")
        else:
            # now we've got the function to call
            def call_impl(*args, **call_kwargs):
                # here we wrap the original function so that it won't return anything for the `fire`
                logger.info(f"calling {var_path} with {args} {call_kwargs}")
                res = func(*args, **call_kwargs)
                if isawaitable(res):
                    res = asyncio.run(res)
                logger.info(f"result:\n<pinjected>\n{res}\n</pinjected>")

            # now, the resulting function canbe async, can fire handle that?
            return call_impl

    return asyncio.run(a_prep())


def json_graph(var_path: str = None, design_path: str = None, **kwargs):
    """
    Generate a JSON representation of the dependency graph for a variable.

    :param var_path: the path to the variable to visualize: e.g. "my_module.my_var"
    :param design_path: the path to the design to be used: e.g. "my_module.my_design"
    :param kwargs: additional parameters to pass to run_injected
    """
    return run_injected("json-graph", var_path, design_path, **kwargs)


def describe(var_path: str = None, design_path: str = None, **kwargs):
    """
    Generate a human-readable description of the dependency graph for a variable.
    Uses to_edges() of DIGraph to show dependencies with their documentation.

    :param var_path: Full module path to the variable to describe in the format 'full.module.path.var.name'.
                    This parameter is required and must point to an importable variable.
    :param design_path: Full module path to the design to be used in the format 'module.path.design'.
                      If not provided, it will be inferred from var_path.
    :param kwargs: Additional parameters to pass to run_injected.
    """
    if var_path is None:
        print(
            "Error: You must provide a variable path in the format 'full.module.path.var.name'"
        )
        print("Examples:")
        print("  pinjected describe my_module.my_submodule.my_variable")
        print("  pinjected describe --var_path=my_module.my_submodule.my_variable")
        return None

    return run_injected("describe", var_path, design_path, **kwargs)


def describe_json(var_path: str = None, design_path: str = None, **kwargs):
    """
    Generate a JSON representation of the dependency chain for an IProxy variable.
    Returns dependency information including metadata about where keys are bound.

    :param var_path: Full module path to the IProxy variable to describe in the format 'full.module.path.var.name'.
                    This parameter is required and must point to an importable IProxy object.
    :param design_path: Full module path to the design to be used in the format 'module.path.design'.
                      If not provided, it will be inferred from var_path.
    :param kwargs: Additional parameters to pass to run_injected.
    :return: JSON string containing dependency chain information with metadata.
    """
    if var_path is None:
        print(
            "Error: You must provide a variable path in the format 'full.module.path.var.name'"
        )
        print("Examples:")
        print("  pinjected describe-json my_module.my_submodule.my_iproxy_variable")
        print(
            "  pinjected describe-json --var_path=my_module.my_submodule.my_iproxy_variable"
        )
        return None

    return run_injected("describe_json", var_path, design_path, **kwargs)


def list(var_path: str = None):
    """
    List all IProxy objects that are runnable in the specified module.

    :param var_path: Path to the module containing IProxy objects.

    Example:
        python -m pinjected list my.module.path
    """
    import importlib
    from pathlib import Path

    from pinjected import IProxy
    from pinjected.di.app_injected import InjectedEvalContext
    from pinjected.di.proxiable import DelegatedVar
    from pinjected.runnables import get_runnables

    if var_path is None:
        print("Error: You must provide a module path in the format 'full.module.path'")
        print("Examples:")
        print("  pinjected list my_module.my_submodule")
        print("  pinjected list --var_path=my_module.my_submodule")
        return None

    try:
        module = importlib.import_module(var_path)
        module_file = Path(module.__file__)

        runnables = get_runnables(module_file)

        iproxies = []
        for runnable in runnables:
            # Check if it's an IProxy object or a DelegatedVar with InjectedEvalContext
            if isinstance(runnable.var, IProxy) or (
                isinstance(runnable.var, DelegatedVar)
                and getattr(runnable.var, "context", None) == InjectedEvalContext
            ):
                iproxies.append(runnable.var_path)

        print(json.dumps(iproxies))
        return 0
    except ImportError as e:
        print(f"Error: Could not import module '{var_path}': {e!s}")
        return 1
    except Exception as e:
        print(f"Error: {e!s}")
        return 1


async def a_trace_key(key_name: str, var_path: str | None = None):
    """
    Async implementation of trace_key using MetaContext.
    """
    from pinjected.v2.keys import StrBindKey
    from pinjected.run_helpers.run_injected import (
        load_user_default_design,
        load_user_overrides_design,
    )

    # Convert string key to IBindKey
    bind_key = StrBindKey(key_name)

    # Determine the path to use
    if var_path:
        path = Path(ModuleVarPath(var_path).module_file_path)
    else:
        path = Path.cwd()

    # Use MetaContext to gather bindings and trace information
    meta_context = await MetaContext.a_gather_bindings_with_legacy(path)

    # Extract trace information for the specific key
    key_traces = []
    seen_paths = set()

    # First check user default design
    user_default = load_user_default_design()
    if bind_key in user_default.bindings:
        key_traces.append(
            {
                "path": "user_default_design (e.g., ~/.pinjected/defaults.py)",
                "has_key": True,
                "overrides_previous": False,
            }
        )

    # Go through the trace to find where this key is defined in module hierarchy
    for var_spec in meta_context.trace:
        if var_spec.var_path in seen_paths:
            continue
        seen_paths.add(var_spec.var_path)

        # Check if this var_spec contains our key
        # Skip __meta_design__ since it's deprecated - only trace __design__
        if var_spec.var_path.endswith("__design__"):
            design_obj = await _a_resolve_design(var_spec)
            if design_obj and bind_key in design_obj.bindings:
                key_traces.append(
                    {
                        "path": var_spec.var_path,
                        "has_key": True,
                        "overrides_previous": len(key_traces) > 0,
                    }
                )
        elif var_spec.var_path.endswith("__meta_design__"):
            # Skip __meta_design__ entries since they're deprecated
            continue

    # Finally check user overrides design
    user_overrides = load_user_overrides_design()
    if bind_key in user_overrides.bindings:
        key_traces.append(
            {
                "path": "user_overrides_design (e.g., ~/.pinjected/overrides.py)",
                "has_key": True,
                "overrides_previous": len(key_traces) > 0,
            }
        )

    # Check if key exists in final design
    final_design = await meta_context.a_final_design
    found_in_final = bind_key in final_design.bindings

    return key_traces, found_in_final


async def _a_resolve_design(var_spec):
    """Helper to resolve a design from a var spec."""
    from pinjected import EmptyDesign
    from pinjected.helper_structure import _a_resolve

    try:
        ovr = await _a_resolve(var_spec.var)
        return ovr
    except Exception:
        return EmptyDesign


def trace_key(key_name: str, var_path: str | None = None):
    """
    Trace where a binding key is defined and overridden in the design hierarchy.

    :param key_name: The binding key to trace
    :param var_path: Optional module path to use as context (defaults to current directory)

    Example:
        pinjected trace-key logger
        pinjected trace-key logger --var_path=my.module.path
    """
    from pinjected.pinjected_logging import logger

    if not key_name:
        _print_trace_key_error()
        return 1

    try:
        logger.info(f"Tracing key: '{key_name}'")
        key_traces, found = asyncio.run(a_trace_key(key_name, var_path))
        return _handle_trace_results(key_name, key_traces, found)
    except Exception as e:
        print(f"Error: {e!s}")
        return 1


def _print_trace_key_error():
    """Print error message for missing key name."""
    print("Error: You must provide a key name to trace")
    print("Examples:")
    print("  pinjected trace-key logger")
    print("  pinjected trace-key --key_name=database_connection")


def _handle_trace_results(key_name: str, key_traces: list, found: bool) -> int:
    """Handle and display trace results."""
    if not found:
        print(f"Key '{key_name}' not found in the design hierarchy")
        return 0

    if not key_traces:
        print(f"Key '{key_name}' exists but no trace information available")
        return 0

    print(f"\nTracing key: '{key_name}'")
    print("Found in:")
    for i, trace in enumerate(key_traces, 1):
        override_note = " (overrides previous)" if trace["overrides_previous"] else ""
        print(f"  {i}. {trace['path']}{override_note}")

    print(f"\nFinal binding source: {key_traces[-1]['path']}")
    return 0


class PinjectedRunDependencyResolutionFailure(Exception):
    pass


class PinjectedCLI:
    """Pinjected: Python Dependency Injection Framework

    Available commands:
      run            - Run an injected variable with a specified design
      resolve        - Alias for 'run' command (dependency resolution and object construction)
      check_config   - Display the current configuration
      create_overloads - Create type hint overloads for injected functions
      json_graph     - Generate a JSON representation of the dependency graph
      describe       - Generate a human-readable description of a dependency graph.
                       Requires a full module path in the format: full.module.path.var.name
                       Can be used as: describe my_module.path.var or describe --var_path=my_module.path.var
      describe_json  - Generate a JSON representation of the dependency chain for an IProxy variable.
                       Returns dependency information including metadata about where keys are bound.
                       Can be used as: describe_json my_module.path.var or describe_json --var_path=my_module.path.var
      list           - List all IProxy objects that are runnable in the specified module.
                       Requires a module path in the format: full.module.path
                       Can be used as: list my_module.path or list --var_path=my_module.path
      trace_key      - Trace where a binding key is defined and overridden in the design hierarchy
                       Requires a key name and optional module path
                       Can be used as: trace_key logger or trace_key logger --var_path=my.module.path

    For more information on a specific command, run:
      pinjected COMMAND --help

    Example:
      pinjected run --var_path=my_module.my_var
      pinjected resolve --var_path=my_module.my_var
      pinjected describe --var_path=my_module.my_submodule.my_variable
      pinjected describe_json --var_path=my_module.my_submodule.my_iproxy_variable
      pinjected list my_module.my_submodule
      pinjected trace_key logger
      pinjected trace_key database --var_path=my_module.path
    """

    def __init__(self):
        self.run = run
        self.resolve = run  # Add 'resolve' as an alias to 'run'
        self.check_config = check_config
        self.create_overloads = process_file
        self.json_graph = json_graph
        self.describe = describe
        self.describe_json = describe_json
        self.list = list
        self.trace_key = trace_key


def main():
    try:
        import inspect

        import fire

        try:
            original_info = fire.inspectutils.Info

            def patched_info(component):
                try:
                    import IPython
                    from IPython.core import oinspect

                    ipython_version = tuple(map(int, IPython.__version__.split(".")))

                    if ipython_version >= (9, 0):
                        inspector = oinspect.Inspector(theme_name="Neutral")
                    else:
                        inspector = oinspect.Inspector()

                    info = inspector.info(component)

                    if info["docstring"] == "<no docstring>":
                        info["docstring"] = None
                except ImportError:
                    info = fire.inspectutils._InfoBackup(component)

                try:
                    unused_code, lineindex = inspect.findsource(component)
                    info["line"] = lineindex + 1
                except (TypeError, OSError):
                    info["line"] = None

                if "docstring" in info:
                    info["docstring_info"] = fire.docstrings.parse(info["docstring"])

                return info

            fire.inspectutils.Info = patched_info
        except (ImportError, AttributeError):
            pass

        cli = PinjectedCLI()
        fire.Fire(cli)
        return cli
    except Exception as e:
        e = unwrap_exception_group(e)
        if isinstance(e, PinjectedRunFailure):
            e = unwrap_exception_group(e.__cause__)
            if isinstance(e, DependencyResolutionError):
                raise PinjectedRunDependencyResolutionFailure(str(e)) from None
            if isinstance(e, DependencyValidationError):
                raise PinjectedRunDependencyResolutionFailure(
                    f"Dependency validation failed: {e!s}"
                ) from None
        raise
