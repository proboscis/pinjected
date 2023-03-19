from pinject_design.module_inspector import get_project_root


def test_get_project_root():
    root = get_project_root(
        "/Users/kento/repos/archpainter/archpainter/style_transfer/iccv_artifacts.py",
    )
    assert root == "/Users/kento/repos/archpainter"
