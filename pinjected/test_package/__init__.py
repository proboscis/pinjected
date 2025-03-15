from pinjected import *
from pinjected.module_inspector import ModuleVarSpec
from pinjected.helper_structure import IdeaRunConfiguration
from pinjected.test_helper.test_runner import test_tree


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

# 非同期関数を直接呼び出すのではなく、最初から非同期を処理できる形に変更
run_test_module:IProxy = Injected.bind(lambda: test_tree())


__meta_design__ = design(
    name="test_package.child.__init__",
    # custom_idea_config_creator = 'dummy'
    custom_idea_config_creator=Injected.bind(dummy_config_creator_for_test)
)
