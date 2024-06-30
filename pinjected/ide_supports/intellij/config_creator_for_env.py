import shlex
from typing import Callable

import pinjected
from pinjected import injected
from pinjected.helper_structure import IdeaRunConfiguration
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import ModuleVarPath


class IRunner:
    async def run(self, cmd: str) -> str:
        pass


@injected
async def _run_command_with_env(env: IRunner, tgt_var_path: str ):
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
def add_configs_from_envs(
        interpreter_path,
        default_working_dir,
        /,
        tgt: ModuleVarSpec,
        environments: list[ModuleVarPath],

) -> list[IdeaRunConfiguration]:
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

