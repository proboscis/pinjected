import shlex

import pinjected
from pinjected import injected
from pinjected.helper_structure import IdeaRunConfiguration
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import ModuleVarPath
from pinjected.run_config_utils import IdeaConfigCreator


class IRunner:
    async def run(self, cmd: str) -> str:
        pass


class LocalRunner(IRunner):
    async def run(self, cmd: str) -> str:
        import subprocess
        return subprocess.run(cmd, shell=True, capture_output=True).stdout.decode()


TEST_ENV = injected(LocalRunner)()


@injected
async def _run_command_with_env(env: IRunner, tgt_var_path: str):
    assert hasattr(env, "run"), f"env {env} does not have run method"
    cmd = f"python -m pinjected run {tgt_var_path}"
    if hasattr(env, "pinjected_additional_args"):
        for k, v in env.pinjected_additional_args.items():
            cmd += f" --{k}={shlex.quote(v)}"
    return await env.run(cmd)


# this is the entry point
run_command_with_env = _run_command_with_env(
    injected('target_environment'),
    injected('target_variable'),
)


@injected
def idea_config_creator_from_envs(
        interpreter_path,
        default_working_dir,
        /,
        environments: list[ModuleVarPath | str],
) -> IdeaConfigCreator:
    def impl(tgt: ModuleVarSpec) -> list[IdeaRunConfiguration]:
        res = []
        tgt_script_path = ModuleVarPath(tgt.var_path).module_file_path
        for env in environments:
            if isinstance(env, str):
                env = ModuleVarPath(env)
            var_name = tgt.var_path.split(".")[-1]

            res.append(
                IdeaRunConfiguration(
                    name=f"submit {var_name} to env: {env.var_name}",
                    script_path=str(pinjected.__file__).replace("__init__.py", "__main__.py"),
                    interpreter_path=interpreter_path,
                    arguments=[
                        "run",
                        "pinjected.ide_supports.intellij.config_creator_for_env.run_command_with_env",
                        f"--meta-context-path={tgt_script_path}",
                        f"--target-environment={{{env.path}}}",
                        f"--target-variable={tgt.var_path}",
                    ],
                    working_dir=default_working_dir.value_or("."),
                )
            )
        return res

    return impl
