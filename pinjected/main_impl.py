import asyncio
from inspect import isawaitable
from pathlib import Path

from pinjected import Design, instances, providers, Injected
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.tools.add_overload import process_file
from pinjected.helper_structure import MetaContext
from pinjected.logging_helper import disable_internal_logging
from pinjected.module_var_path import load_variable_by_module_path, ModuleVarPath
from pinjected.run_helpers.run_injected import run_injected, load_user_default_design, load_user_overrides_design, \
    a_get_run_context, RunContext


def run(
        var_path: str = None,
        design_path: str = None,
        overrides: str = None,
        meta_context_path: str = None,
        base64_encoded_json: str = None,
        **kwargs
):
    """
    load the injected variable from var_path and run it with a design at design_path.
    If design_path is not provided, it will be inferred from var_path.
    design_path is inferred by looking at the module of var_path for a __meta_design__ attribute.
    This command will ask __meta_design__ to provide 'default_design_paths', and uses the first one.
    if __meta_design__ is not found, it will recursively look for a __meta_design__ attribute in the parent module.
    by default, __meta_design__ is accumulated from all parent modules.
    Therefore, if any parent module has a __meta_design__ attribute with a 'default_design_paths' attribute, it will be used.

    :param var_path: the path to the variable to be injected: e.g. "my_module.my_var"
    :param design_path: the path to the design to be used: e.g. "my_module.my_design"
    :param ovr: a string that can be converted to an Design in some way. This will gets concatenated to the design.
    :param kwargs: overrides for the design. e.g. "api_key=1234"

    """
    if base64_encoded_json is not None:
        import json
        import base64
        data: dict = json.loads(base64.b64decode(base64_encoded_json).decode())
        var_path = data.pop('var_path')
        design_path = data.pop('design_path', None)
        overrides = data.pop('overrides', None)
        meta_context_path = data.pop('meta_context_path', None)
        kwargs = data

    async def a_prep():
        with disable_internal_logging():
            kwargs_overrides = parse_kwargs_as_design(**kwargs)
            ovr = instances()
            if meta_context_path is not None:
                mc = await MetaContext.a_gather_from_path(Path(meta_context_path))
                ovr += await mc.a_final_design
            ovr += parse_overrides(overrides)
            ovr += kwargs_overrides
            cxt: RunContext = await a_get_run_context(design_path, var_path)
            cxt = cxt.add_overrides(ovr)
        res = await cxt.a_run()
        from loguru import logger
        logger.info(f"result:\n<pinjected>\n{res}\n</pinjected>")
        # now we've got the function to call

    return asyncio.run(a_prep())


def check_config():
    from loguru import logger
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
    res = instances()
    for k, v in kwargs.items():
        if isinstance(v, str) and v.startswith('{') and v.endswith('}'):
            v = v[1:-1]
            loaded = load_variable_by_module_path(v)
            res += providers(
                **{k: loaded}
            )
        else:
            res += instances(
                **{k: v}
            )
    return res


def parse_overrides(overrides) -> Design:
    match overrides:
        case str() if ':' in overrides:  # this needs to be a complete call to run_injected, at least, we need to take arguments...
            # hmm at this point, we should just run a script ,right?
            design, var = overrides.split(':')
            resolved = run_injected("get", var, design, return_result=True)
            assert isinstance(resolved, Design), f"expected {design} to be a design, but got {resolved}"
            return resolved
        case str() as path:  # a path of a design/injected
            var = ModuleVarPath(path).load()
            if isinstance(var, Design):
                return var
            elif isinstance(var, (Injected, DelegatedVar)):
                resolved = run_injected("get", path, return_result=True)
                assert isinstance(resolved, Design), f"expected {path} to be a design, but got {resolved}"
                return resolved
        case None:
            return instances()


def decode_b64json(text):
    import json
    import base64
    data: dict = json.loads(base64.b64decode(text).decode())
    return data


def call(
        var_path: str = None,
        design_path: str = None,
        overrides: str = None,
        meta_context_path: str = None,
        base64_encoded_json: str = None,
        call_kwargs_base64_json: str = None,
        **kwargs
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
    from loguru import logger
    if base64_encoded_json is not None:
        data = decode_b64json(base64_encoded_json)
        var_path = data.pop('var_path')
        design_path = data.pop('design_path', None)
        overrides = data.pop('overrides', None)
        meta_context_path = data.pop('meta_context_path', None)
        kwargs = data
        logger.info(f"decoded {var_path=} {design_path=} {overrides=} {meta_context_path=} {kwargs=}")

    # no_notification = kwargs.pop('pinjected_no_notification', False)
    async def a_prep():
        kwargs_overrides = parse_kwargs_as_design(**kwargs)
        ovr = instances()
        if meta_context_path is not None:
            mc = await MetaContext.a_gather_from_path(Path(meta_context_path))
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


def main():
    import fire

    fire.Fire(dict(
        run=run,
        call=call,
        check_config=check_config,
        create_overloads=process_file
    ))
