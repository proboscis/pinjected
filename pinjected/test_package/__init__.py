from pinjected import injected_function
from pinjected.di.util import instances, providers
from pinjected.module_inspector import ModuleVarSpec
from pinjected.helper_structure import IdeaRunConfiguration


@injected_function
def dummy_config_creator_for_test(
        runner_script_path,
        interpreter_path,
        default_working_dir,
        logger,
        /,
        tgt: ModuleVarSpec
):
    logger.info(f"custom config creator called")
    return [
        IdeaRunConfiguration(
            name="dummy for test_package.child.__init__",
            script_path=runner_script_path,
            interpreter_path=interpreter_path,
            arguments=[],
            working_dir=default_working_dir.value_or("."),
        )
    ]


__meta_design__ = instances(
    name="test_package.child.__init__",
    # custom_idea_config_creator = 'dummy'
) + providers(
    custom_idea_config_creator=dummy_config_creator_for_test
)
