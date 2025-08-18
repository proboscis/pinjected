"""Test package with custom configuration."""

from pinjected import IProxy, Injected, design
from pinjected.test_helper.test_runner import test_tree
from pinjected.test_package.config import dummy_config_creator_for_test

__all__ = ["dummy_config_creator_for_test", "run_test_module"]

# 非同期関数を直接呼び出すのではなく、最初から非同期を処理できる形に変更
run_test_module: IProxy = Injected.bind(lambda: test_tree())


__design__ = design(
    name="test_package.child.__init__",
    # custom_idea_config_creator = 'dummy'
    custom_idea_config_creator=dummy_config_creator_for_test,
)
