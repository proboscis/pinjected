"""Test package configuration utilities."""

from typing import TYPE_CHECKING, Protocol

from pinjected import injected
from pinjected.helper_structure import IdeaRunConfiguration
from pinjected.module_inspector import ModuleVarSpec

if TYPE_CHECKING:
    from loguru import Logger
    from returns.maybe import Maybe


class DummyConfigCreatorForTestProtocol(Protocol):
    def __call__(self, tgt: ModuleVarSpec) -> list[IdeaRunConfiguration]: ...


@injected(protocol=DummyConfigCreatorForTestProtocol)
def dummy_config_creator_for_test(
    runner_script_path: str,
    interpreter_path: str,
    default_working_dir: "Maybe[str]",
    logger: "Logger",
    /,
    tgt: ModuleVarSpec,
):
    """Create dummy IDE run configuration for testing."""
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
