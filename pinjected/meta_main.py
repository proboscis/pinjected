import warnings
from pinjected.ide_supports.create_configs import run_with_meta_context

if __name__ == "__main__":
    """
    An entrypoint for running a injected with __design__ integrated.
    This is used to create IDE configurations, and other metadata related tasks.
    
    DEPRECATED: This entry point is used by IDE plugins (PyCharm, VSCode) but will be
    deprecated in the future. IDE plugins should be updated to use direct pinjected 
    commands instead.
    
    NOTE: As of 2024, this automatically uses pinjected_internal_design when no 
    design_path is provided for backward compatibility with existing IDE plugins.
    """
    import fire

    warnings.warn(
        "meta_main is deprecated and only maintained for backward compatibility with IDE plugins. "
        "Please use direct pinjected commands instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    fire.Fire(run_with_meta_context)
