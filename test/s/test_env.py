from pinjected import Injected, design
from pinjected.ide_supports.intellij.config_creator_for_env import idea_config_creator_from_envs



test_entrypoint = Injected.pure("x")

__meta_design__ = design(
    custom_idea_config_creator=idea_config_creator_from_envs(
        [
            "pinjected.ide_supports.intellij.config_creator_for_env.TEST_ENV"
        ]
    )
)

