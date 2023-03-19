from pinject_design import Injected
from pinject_design.di.util import instances
from pinject_design.run_config_utils import create_configurations, run_injected, find_module_attr


def test_create_configurations():
    create_configurations(
        "/Users/kento/repos/archpainter/archpainter/style_transfer/iccv_artifacts.py",
        default_design_path="dummy_path"
    )


test_design = instances(x=0)
test_var = Injected.by_name("x")


def test_run_injected():
    res = run_injected(
        "get",
        "archpainter.style_transfer.iccv_artifacts.prepare_deception_samples_to_df",
        "archpainter.style_transfer.iccv_experiments.iccv_experiment_design"
    )
    print(res)
    assert res==0

