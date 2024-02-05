from pinjected import instances, Design, Injected, providers
from pinjected.di.proxiable import DelegatedVar
from pinjected.module_var_path import ModuleVarPath, load_variable_by_module_path
from pinjected.run_helpers.run_injected import run_injected, load_user_default_design, load_user_overrides_design


def run(
        var_path: str,
        design_path: str = None,
        overrides: str = None,
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
    :param _overrides_: a string that can be converted to an Design in some way. This will gets concatenated to the design.
    :param kwargs: overrides for the design. e.g. "api_key=1234"

    """
    # TODO parse overrides
    # TODO parse kwargs from cli.

    kwargs_overrides = parse_kwargs_as_design(**kwargs)
    overrides = parse_overrides(overrides)
    overrides += kwargs_overrides
    return run_injected("get", var_path, design_path, return_result=True, overrides=overrides)

def check_config():
    from loguru import logger
    from pprint import pformat
    default:Design = load_user_default_design()
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


if __name__ == '__main__':
    import fire

    fire.Fire(dict(
        run=run,
        check_config=check_config
    ))
