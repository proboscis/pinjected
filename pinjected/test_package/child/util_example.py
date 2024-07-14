from typing import Callable

from pinjected import *


def memoize(cache: Injected[dict]):
    def impl(func: Injected[Callable]):
        return MemoizedFunction(func, cache)
    return impl


def sqlite_dict(path: Injected[Path]):
    return SqliteDict(path)


def wandb_artifact(artifact_name: Injected[str]):
    return WandbArtifactMemo(artifact_name)


@injected
def test_experiment(a: int, b: int):
    return a + b


sqlite_cached_experiment:IProxy[Callable] = memoize(sqlite_dict(
    injected("experiment_cache_sqlite_path")
))(test_experiment)
wandb_cached_experiment:IProxy[Callable] = memoize(wandb_artifact(
    injected("experiment_cache_artifact_name")
))(test_experiment)

@memoize(sqlite_dict(injected("evaluation_cache_path")))
@injected
def evaluate(model,dataset):
    pass
evaluation1 = evaluate(some_model,some_dataset)


experiment1 = sqlite_cached_experiment(1, 2)
experiment2 = wandb_cached_experiment(1, 2)

