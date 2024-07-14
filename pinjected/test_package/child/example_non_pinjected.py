from pinjected import *


def build_model(
        cfg,
        model_name: str,
        n_layers: int,
        n_features: int,
):
    from torch import nn
    return nn.Module


def model_1(cfg):
    return build_model(cfg, 'model_1', 10, 20)


def model_2(cfg):
    return build_model(cfg, 'model_2', 5, 3)


def model_3(cfg):
    return build_model(cfg, 'model_3', 7, 8)


def build_dataset(
        cfg,
        dataset_name: str,
        n_samples: int,
        # ...
):
    from torch.utils.data import Dataset
    return Dataset


def dataset_1(cfg):
    return build_dataset(cfg, 'dataset_1', 100)


def dataset_2(cfg):
    return build_dataset(cfg, 'dataset_2', 200)


def dataset_3(cfg):
    return build_dataset(cfg, 'dataset_3', 300)


@injected
def run_experiment(
        cfg,
        model,
        dataset
) -> float:
    return evaluate(cfg, model, dataset)


def experiment_1_1(cfg):
    return run_experiment(cfg, model_1(cfg), dataset_1(cfg))


def experiment_1_2(cfg):
    return run_experiment(cfg, model_1(cfg), dataset_2(cfg))


def experiment_1_3(cfg):
    return run_experiment(cfg, model_1(cfg), dataset_3(cfg))


def experiment_2_1(cfg):
    return run_experiment(cfg, model_2(cfg), dataset_1(cfg))


def experiment_2_2(cfg):
    return run_experiment(cfg, model_2(cfg), dataset_2(cfg))


def experiment_2_3(cfg):
    return run_experiment(cfg, model_2(cfg), dataset_3(cfg))


def experiment_3_1(cfg):
    return run_experiment(cfg, model_3(cfg), dataset_1(cfg))


def experiment_3_2(cfg):
    return run_experiment(cfg, model_3(cfg), dataset_2(cfg))


def experiment_3_3(cfg):
    return run_experiment(cfg, model_3(cfg), dataset_3(cfg))


def setup_parser():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--name', type=str, required=True)
    """
    add more arguments here
    """
    return arg_parser


if __name__ == '__main__':
    import sys

    parser = setup_parser()
    cfg = parser.parse_args()
    experiments = dict()
    for i in range(3):
        for j in range(3):
            experiments[f'{i}_{j}'] = getattr(sys.modules[__name__], f'experiment_{i + 1}_{j + 1}')
    experiments[cfg.name](cfg)
