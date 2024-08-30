from pinjected import *

Model = object
Dataset = object

@injected
def build_model(
        logger,
        device,
        /,
        model_name: str,
        n_layers: int,
        n_features: int,
        # ...
):
    from torch import nn
    return nn.Module


model_1: IProxy[Model] = build_model('model_1', 10, 20)
model_2: IProxy[Model] = build_model('model_2', 5, 3)
model_3: IProxy[Model] = build_model('model_3', 7, 8)


@injected
def build_dataset(
        logger,
        device,
        /,
        dataset_name: str,
        n_samples: int,
        # ...
):
    from torch.utils.data import Dataset
    return Dataset


dataset_1: IProxy[Dataset] = build_dataset('dataset_1', 100)
dataset_2: IProxy[Dataset] = build_dataset('dataset_2', 200)
dataset_3: IProxy[Dataset] = build_dataset('dataset_3', 300)


@injected
def run_experiment(
        logger,
        evaluate,
        /,
        model,
        dataset
) -> float:
    return evaluate(model, dataset)


experiment_1_1: IProxy[float] = run_experiment(model_1, dataset_1)
experiment_1_2: IProxy[float] = run_experiment(model_1, dataset_2)
experiment_1_3: IProxy[float] = run_experiment(model_1, dataset_3)
experiment_2_1: IProxy[float] = run_experiment(model_2, dataset_1)
experiment_2_2: IProxy[float] = run_experiment(model_2, dataset_2)
experiment_2_3: IProxy[float] = run_experiment(model_2, dataset_3)
experiment_3_1: IProxy[float] = run_experiment(model_3, dataset_1)
experiment_3_2: IProxy[float] = run_experiment(model_3, dataset_2)
experiment_3_3: IProxy[float] = run_experiment(model_3, dataset_3)

run_all_experiments: IProxy[list[float]] = Injected.list(
    experiment_1_1, experiment_1_2, experiment_1_3,
    experiment_2_1, experiment_2_2, experiment_2_3,
    experiment_3_1, experiment_3_2, experiment_3_3
)
