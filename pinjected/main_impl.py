import asyncio
import json
from pathlib import Path

from pinjected import Design, Injected, design
from pinjected.di.partially_injected import PartiallyInjectedFunction
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
    var_path: str | None = None,
    design_path: str | None = None,
    overrides: str | None = None,
    meta_context_path: str | None = None,
    base64_encoded_json: str | None = None,
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
    logger.info("displaying default design bindings:")
    logger.info(default.table_str())
    logger.info("displaying overrides design bindings:")
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


def call(function_path: str, iproxy_path: str):
    """
    Call an @injected function with an IProxy variable.

    This command applies an IProxy object to an @injected function and executes it,
    following the same pattern as the run function with RunContext.

    :param function_path: Full module path to the @injected function (e.g., 'my_module.my_function')
    :param iproxy_path: Full module path to the IProxy variable (e.g., 'my_module.my_iproxy')

    Example:
        pinjected call my_module.process_data my_config.data_proxy
    """
    from pinjected.pinjected_logging import logger

    async def a_prep():
        from pinjected.module_var_path import ModuleVarPath
        from pinjected.di.partially_injected import Partial

        # Load and validate the function
        func_var_path = ModuleVarPath(function_path)
        func = func_var_path.load()
        assert isinstance(func, (PartiallyInjectedFunction, Partial)), (
            f"expected {function_path} to be a PartiallyInjectedFunction or Partial, but got {type(func)}"
        )

        iproxy_var_path = ModuleVarPath(iproxy_path)
        iproxy = iproxy_var_path.load()

        # Apply the IProxy to the function and execute
        logger.info(f"Applying IProxy '{iproxy_path}' to function '{function_path}'")
        # Get the RunContext from the IProxy's path (IProxy contains the design/context)
        from pinjected.run_helpers.run_injected import (
            a_get_run_context,
            a_run_with_notify,
        )

        # Create a RunContext from the IProxy path - the IProxy provides the execution context
        cxt: RunContext = await a_get_run_context(None, iproxy_path)

        # Apply the IProxy to the function
        # The function[iproxy] pattern means we're binding the IProxy's design to the function
        call_result_proxy = func(iproxy)

        # Define the task to run with the IProxy's context
        async def task(cxt: RunContext):
            return await cxt.a_provide(call_result_proxy)

        # Execute with notification handling using the IProxy's context
        result = await a_run_with_notify(cxt, task)

        logger.info(f"Result:\n<pinjected>\n{result}\n</pinjected>")

    return asyncio.run(a_prep())


def json_graph(var_path: str | None = None, design_path: str | None = None, **kwargs):
    """
    Generate a JSON representation of the dependency graph for a variable.

    :param var_path: the path to the variable to visualize: e.g. "my_module.my_var"
    :param design_path: the path to the design to be used: e.g. "my_module.my_design"
    :param kwargs: additional parameters to pass to run_injected
    """
    return run_injected("json-graph", var_path, design_path, **kwargs)


def describe(var_path: str | None = None, design_path: str | None = None, **kwargs):
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


def describe_json(
    var_path: str | None = None, design_path: str | None = None, **kwargs
):
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


def list(var_path: str | None = None):
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


def review_pinjected(fix: bool = False):
    """
    Review recently changed Python files for pinjected usage patterns and optionally fix issues.

    This command checks git status for changed Python files and reviews them for common
    pinjected issues such as:
    - Missing Protocol definitions for @injected functions
    - Incorrect usage of @injected functions within other @injected functions
    - Use of await inside @injected functions when calling other @injected
    - Missing a_ prefix for async @injected functions
    - Use of deprecated __design__
    - Default arguments in @instance functions
    - Missing type annotations with IProxy

    :param fix: If True, automatically fix detected issues. If False, only report them.

    Example:
        pinjected review-pinjected          # Review and report issues
        pinjected review-pinjected --fix    # Review and fix issues
    """
    import subprocess
    import ast
    import re
    from pathlib import Path
    from typing import List, Dict

    from pinjected.pinjected_logging import logger

    class PinjectedReviewer:
        def __init__(self, fix: bool = False):
            self.fix = fix
            self.issues: List[Dict] = []
            self.fixed_count = 0

        def get_changed_files(self) -> List[Path]:
            """Get list of changed Python files from git status."""
            try:
                # Get modified and added files
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                changed_files = []
                for line in result.stdout.splitlines():
                    if line.strip():
                        status = line[:2]
                        file_path = line[3:].strip()

                        # Include modified (M), added (A), and untracked (??) files
                        if (
                            "M" in status or "A" in status or "?" in status
                        ) and file_path.endswith(".py"):
                            changed_files.append(Path(file_path))

                return changed_files
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to get git status: {e}")
                return []

        def review_file(self, file_path: Path) -> List[Dict]:
            """Review a single file for pinjected issues."""
            try:
                with open(file_path, "r") as f:
                    content = f.read()

                tree = ast.parse(content)
                issues = []

                # Check for various patterns
                issues.extend(
                    self._check_injected_without_protocol(tree, file_path, content)
                )
                issues.extend(
                    self._check_injected_calling_injected(tree, file_path, content)
                )
                issues.extend(self._check_async_naming(tree, file_path, content))
                issues.extend(self._check_meta_design(content, file_path))
                issues.extend(self._check_instance_defaults(tree, file_path, content))

                return issues

            except Exception as e:
                logger.error(f"Failed to review {file_path}: {e}")
                return []

        def _check_injected_without_protocol(
            self, tree: ast.AST, file_path: Path, content: str
        ) -> List[Dict]:
            """Check for @injected functions without protocol parameter."""
            issues = []

            class InjectedVisitor(ast.NodeVisitor):
                def visit_FunctionDef(self, node):
                    if self._has_injected_decorator(
                        node
                    ) and not self._has_protocol_param(node):
                        issues.append(
                            {
                                "file": str(file_path),
                                "line": node.lineno,
                                "issue": f"@injected function '{node.name}' missing protocol parameter",
                                "severity": "high",
                                "fix_available": True,
                            }
                        )
                    self.generic_visit(node)

                def visit_AsyncFunctionDef(self, node):
                    if self._has_injected_decorator(
                        node
                    ) and not self._has_protocol_param(node):
                        issues.append(
                            {
                                "file": str(file_path),
                                "line": node.lineno,
                                "issue": f"@injected async function '{node.name}' missing protocol parameter",
                                "severity": "high",
                                "fix_available": True,
                            }
                        )
                    self.generic_visit(node)

                def _has_injected_decorator(self, node):
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, ast.Name)
                            and decorator.id == "injected"
                        ):
                            return True
                        if (
                            isinstance(decorator, ast.Call)
                            and isinstance(decorator.func, ast.Name)
                            and decorator.func.id == "injected"
                        ):
                            return True
                    return False

                def _has_protocol_param(self, node):
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, ast.Call)
                            and isinstance(decorator.func, ast.Name)
                            and decorator.func.id == "injected"
                        ):
                            for keyword in decorator.keywords:
                                if keyword.arg == "protocol":
                                    return True
                    return False

            visitor = InjectedVisitor()
            visitor.visit(tree)
            return issues

        def _check_injected_calling_injected(
            self, tree: ast.AST, file_path: Path, content: str
        ) -> List[Dict]:
            """Check for @injected functions calling other @injected without declaring as dependency."""
            issues = []
            # This is a complex check that would require more sophisticated analysis
            # For now, we'll do a simple pattern match

            lines = content.splitlines()
            in_injected = False
            func_name = ""

            for i, line in enumerate(lines):
                if "@injected" in line:
                    in_injected = True
                elif in_injected and "def " in line:
                    func_name = line.split("def ")[1].split("(")[0]
                elif in_injected and "/" in line and ")" in line:
                    in_injected = False
                elif (
                    in_injected
                    and "await " in line
                    and "(" in line
                    and re.search(r"await\s+[a-zA-Z_]\w*\s*\(", line)
                ):
                    issues.append(
                        {
                            "file": str(file_path),
                            "line": i + 1,
                            "issue": f"Possible await of @injected function inside @injected function '{func_name}'",
                            "severity": "medium",
                            "fix_available": False,
                        }
                    )

            return issues

        def _check_async_naming(
            self, tree: ast.AST, file_path: Path, content: str
        ) -> List[Dict]:
            """Check for async @injected functions without a_ prefix."""
            issues = []

            class AsyncVisitor(ast.NodeVisitor):
                def visit_AsyncFunctionDef(self, node):
                    if self._has_injected_decorator(node) and not node.name.startswith(
                        "a_"
                    ):
                        issues.append(
                            {
                                "file": str(file_path),
                                "line": node.lineno,
                                "issue": f"Async @injected function '{node.name}' should have 'a_' prefix",
                                "severity": "low",
                                "fix_available": True,
                            }
                        )
                    self.generic_visit(node)

                def _has_injected_decorator(self, node):
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, ast.Name)
                            and decorator.id == "injected"
                        ):
                            return True
                        if (
                            isinstance(decorator, ast.Call)
                            and isinstance(decorator.func, ast.Name)
                            and decorator.func.id == "injected"
                        ):
                            return True
                    return False

            visitor = AsyncVisitor()
            visitor.visit(tree)
            return issues

        def _check_meta_design(self, content: str, file_path: Path) -> List[Dict]:
            """Check for deprecated __meta_design__ usage."""
            issues = []
            lines = content.splitlines()

            for i, line in enumerate(lines):
                if "__meta_design__" in line:
                    issues.append(
                        {
                            "file": str(file_path),
                            "line": i + 1,
                            "issue": "__meta_design__ is deprecated, use __design__ instead",
                            "severity": "high",
                            "fix_available": True,
                        }
                    )

            return issues

        def _check_instance_defaults(
            self, tree: ast.AST, file_path: Path, content: str
        ) -> List[Dict]:
            """Check for @instance functions with default arguments."""
            issues = []

            class InstanceVisitor(ast.NodeVisitor):
                def visit_FunctionDef(self, node):
                    if self._has_instance_decorator(node) and node.args.defaults:
                        issues.append(
                            {
                                "file": str(file_path),
                                "line": node.lineno,
                                "issue": f"@instance function '{node.name}' should not have default arguments",
                                "severity": "medium",
                                "fix_available": False,
                            }
                        )
                    self.generic_visit(node)

                def _has_instance_decorator(self, node):
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, ast.Name)
                            and decorator.id == "instance"
                        ):
                            return True
                    return False

            visitor = InstanceVisitor()
            visitor.visit(tree)
            return issues

        def fix_issues(self, file_path: Path, issues: List[Dict]):
            """Apply fixes to the file for fixable issues."""
            try:
                with open(file_path, "r") as f:
                    content = f.read()

                lines = content.splitlines()
                tree = ast.parse(content)
                modified = False

                # Group issues by type for batch processing
                protocol_issues = [
                    i for i in issues if "missing protocol parameter" in i["issue"]
                ]
                async_naming_issues = [
                    i for i in issues if "should have 'a_' prefix" in i["issue"]
                ]
                meta_design_issues = [i for i in issues if "__design__" in i["issue"]]

                # Generate Protocol definitions for @injected functions
                if protocol_issues and self.fix:
                    protocols_to_add = []
                    imports_to_add = set()

                    class ProtocolGenerator(ast.NodeVisitor):
                        def visit_FunctionDef(self, node):
                            for issue in protocol_issues:
                                if issue["line"] == node.lineno:
                                    protocol_name = self._generate_protocol_name(
                                        node.name
                                    )
                                    protocol_def = self._generate_protocol_def(
                                        node, protocol_name
                                    )
                                    protocols_to_add.append(
                                        (node.lineno, protocol_def, protocol_name)
                                    )
                                    imports_to_add.add("from typing import Protocol")
                            self.generic_visit(node)

                        def visit_AsyncFunctionDef(self, node):
                            for issue in protocol_issues:
                                if issue["line"] == node.lineno:
                                    protocol_name = self._generate_protocol_name(
                                        node.name
                                    )
                                    protocol_def = self._generate_protocol_def(
                                        node, protocol_name, is_async=True
                                    )
                                    protocols_to_add.append(
                                        (node.lineno, protocol_def, protocol_name)
                                    )
                                    imports_to_add.add("from typing import Protocol")
                            self.generic_visit(node)

                        def _generate_protocol_name(self, func_name: str) -> str:
                            # Convert snake_case to PascalCase and add Protocol suffix
                            parts = func_name.split("_")
                            if parts[0] == "a" and len(parts) > 1:
                                parts = parts[1:]  # Remove 'a_' prefix
                            return "".join(p.capitalize() for p in parts) + "Protocol"

                        def _generate_protocol_def(
                            self, node, protocol_name: str, is_async: bool = False
                        ) -> str:
                            # Find the slash position to determine runtime args
                            slash_pos = None
                            for i, arg in enumerate(node.args.args):
                                if arg.arg == "/":
                                    slash_pos = i
                                    break

                            if slash_pos is None:
                                # Find posonlyargs count
                                slash_pos = len(node.args.posonlyargs)

                            # Get runtime args (after slash)
                            runtime_args = (
                                node.args.args[slash_pos:]
                                if slash_pos < len(node.args.args)
                                else []
                            )
                            defaults = (
                                node.args.defaults[-len(runtime_args) :]
                                if runtime_args
                                else []
                            )

                            # Build protocol definition
                            protocol_lines = [f"class {protocol_name}(Protocol):"]

                            # Build function signature
                            sig_parts = []
                            for i, arg in enumerate(runtime_args):
                                arg_str = f"{arg.arg}"
                                if arg.annotation:
                                    arg_str += f": {ast.unparse(arg.annotation)}"
                                if i < len(defaults) and defaults[i]:
                                    arg_str += f" = {ast.unparse(defaults[i])}"
                                sig_parts.append(arg_str)

                            return_type = ""
                            if node.returns:
                                return_type = f" -> {ast.unparse(node.returns)}"

                            async_prefix = "async " if is_async else ""
                            protocol_lines.append(
                                f"    {async_prefix}def __call__(self, {', '.join(sig_parts)}){return_type}: ..."
                            )

                            return "\n".join(protocol_lines)

                    # Generate protocols
                    generator = ProtocolGenerator()
                    generator.visit(tree)

                    # Add imports and protocols to the file
                    if protocols_to_add:
                        # Find where to insert imports
                        import_line = 0
                        for i, line in enumerate(lines):
                            if line.startswith("from ") or line.startswith("import "):
                                import_line = i + 1
                            elif line.strip() and not line.startswith("#"):
                                break

                        # Add imports if needed
                        for imp in imports_to_add:
                            if imp not in content:
                                lines.insert(import_line, imp)
                                import_line += 1
                                modified = True

                        # Add blank line after imports
                        if import_line > 0 and lines[import_line].strip():
                            lines.insert(import_line, "")
                            import_line += 1

                        # Add protocols before their functions
                        offset = 0
                        for func_line, protocol_def, protocol_name in sorted(
                            protocols_to_add
                        ):
                            # Find the actual line number with offset
                            insert_line = func_line - 1 + offset

                            # Find any decorators above the function
                            while insert_line > 0 and lines[
                                insert_line - 1
                            ].strip().startswith("@"):
                                insert_line -= 1

                            # Insert protocol definition
                            protocol_lines = protocol_def.split("\n")
                            for i, pline in enumerate(protocol_lines):
                                lines.insert(insert_line + i, pline)
                            lines.insert(insert_line + len(protocol_lines), "")
                            lines.insert(insert_line + len(protocol_lines) + 1, "")

                            # Update the decorator to include protocol parameter
                            decorator_line = insert_line + len(protocol_lines) + 2
                            while decorator_line < len(lines) and not lines[
                                decorator_line
                            ].strip().startswith("@injected"):
                                decorator_line += 1

                            if decorator_line < len(lines):
                                old_decorator = lines[decorator_line]
                                if (
                                    "@injected" in old_decorator
                                    and "protocol=" not in old_decorator
                                ):
                                    if old_decorator.strip() == "@injected":
                                        lines[decorator_line] = (
                                            f"@injected(protocol={protocol_name})"
                                        )
                                    else:
                                        # Handle @injected(...) case
                                        lines[decorator_line] = old_decorator.replace(
                                            "@injected(",
                                            f"@injected(protocol={protocol_name}, ",
                                        )

                            offset += len(protocol_lines) + 2
                            modified = True
                            self.fixed_count += 1

                # Fix __meta_design__ to __design__
                for issue in meta_design_issues:
                    if issue["fix_available"] and issue["file"] == str(file_path):
                        line_idx = issue["line"] - 1
                        if line_idx < len(lines):
                            lines[line_idx] = lines[line_idx].replace(
                                "__meta_design__", "__design__"
                            )
                            modified = True
                            self.fixed_count += 1

                # Fix async naming
                for issue in async_naming_issues:
                    if (
                        issue["fix_available"]
                        and issue["file"] == str(file_path)
                        and self.fix
                    ):
                        # This is more complex as we need to rename function and all its usages
                        # For now, just report it needs manual fixing
                        pass

                if modified and self.fix:
                    with open(file_path, "w") as f:
                        f.write("\n".join(lines) + "\n")

            except Exception as e:
                logger.error(f"Failed to fix issues in {file_path}: {e}")

        def run(self):
            """Run the review process."""
            changed_files = self.get_changed_files()

            if not changed_files:
                logger.info("No changed Python files found.")
                return 0

            logger.info(f"Found {len(changed_files)} changed Python files to review")

            all_issues = []
            for file_path in changed_files:
                logger.info(f"Reviewing {file_path}...")
                issues = self.review_file(file_path)
                all_issues.extend(issues)

                if self.fix and issues:
                    self.fix_issues(file_path, issues)

            # Report summary
            if all_issues:
                logger.warning(f"\nFound {len(all_issues)} pinjected usage issues:")

                # Group by severity
                high_issues = [i for i in all_issues if i["severity"] == "high"]
                medium_issues = [i for i in all_issues if i["severity"] == "medium"]
                low_issues = [i for i in all_issues if i["severity"] == "low"]

                if high_issues:
                    logger.error(f"\nHigh severity issues ({len(high_issues)}):")
                    for issue in high_issues:
                        logger.error(
                            f"  {issue['file']}:{issue['line']} - {issue['issue']}"
                        )

                if medium_issues:
                    logger.warning(f"\nMedium severity issues ({len(medium_issues)}):")
                    for issue in medium_issues:
                        logger.warning(
                            f"  {issue['file']}:{issue['line']} - {issue['issue']}"
                        )

                if low_issues:
                    logger.info(f"\nLow severity issues ({len(low_issues)}):")
                    for issue in low_issues:
                        logger.info(
                            f"  {issue['file']}:{issue['line']} - {issue['issue']}"
                        )

                if self.fix:
                    logger.info(f"\nFixed {self.fixed_count} issues automatically.")
                else:
                    fixable = sum(1 for i in all_issues if i["fix_available"])
                    if fixable:
                        logger.info(
                            f"\n{fixable} issues can be fixed automatically with --fix flag."
                        )

                return 1  # Exit with error code if issues found
            else:
                logger.info("No pinjected usage issues found!")
                return 0

    reviewer = PinjectedReviewer(fix=fix)
    return reviewer.run()


class PinjectedCLI:
    """Pinjected: Python Dependency Injection Framework

    Available commands:
      run            - Run an injected variable with a specified design
      resolve        - Alias for 'run' command (dependency resolution and object construction)
      call           - Call an @injected function with an IProxy variable
                       Requires: function_path and iproxy_path
                       Can be used as: call my_module.func my_module.iproxy
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
      review_pinjected - Review recently changed Python files for pinjected usage patterns
                       Checks for common issues like missing Protocols, incorrect @injected usage, etc.
                       Can optionally fix issues with --fix flag
                       Can be used as: review_pinjected or review_pinjected --fix

    For more information on a specific command, run:
      pinjected COMMAND --help

    Example:
      pinjected run --var_path=my_module.my_var
      pinjected call my_module.my_function my_module.my_iproxy
      pinjected resolve --var_path=my_module.my_var
      pinjected describe --var_path=my_module.my_submodule.my_variable
      pinjected describe_json --var_path=my_module.my_submodule.my_iproxy_variable
      pinjected list my_module.my_submodule
      pinjected trace_key logger
      pinjected trace_key database --var_path=my_module.path
      pinjected review_pinjected
      pinjected review_pinjected --fix
    """

    def __init__(self):
        self.run = run
        self.resolve = run  # Add 'resolve' as an alias to 'run'
        self.call = call
        self.check_config = check_config
        self.create_overloads = process_file
        self.json_graph = json_graph
        self.describe = describe
        self.describe_json = describe_json
        self.list = list
        self.trace_key = trace_key
        self.review_pinjected = review_pinjected


def main():
    try:
        import inspect

        import fire

        try:

            def patched_info(component):
                try:
                    import IPython
                    from IPython.core import oinspect

                    try:
                        ipython_version = tuple(
                            map(int, IPython.__version__.split(".")[:2])
                        )
                    except ValueError:
                        ipython_version = (0, 0)

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
