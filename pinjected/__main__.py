from pinjected import instances


def get_injected(
        var_path:str,
        design_path:str=None,
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
    :param kwargs: overrides for the design. e.g. "api_key=1234"
    """
    from pinjected.run_config_utils import run_injected
    overrides = instances(**kwargs)
    return run_injected("get",var_path, design_path,return_result=True,overrides=overrides)


if __name__ == '__main__':
    import fire
    fire.Fire(get_injected)