from pinjected import design, DesignSpec, SimpleBindSpec

__design_spec__ = DesignSpec.new(
    default_design_path=SimpleBindSpec(
        documentation="The default design path used to run injected functions when no specific design path is provided."
    ),
    logger=SimpleBindSpec(
        documentation="Logger instance used for logging information during the execution of injected functions."
    )
)
