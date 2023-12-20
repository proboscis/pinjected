import os

from pinjected import Design
from pinjected.run_config_utils import load_variable_from_script


def load_user_default_design():
    """
    This function loads user specific environment data from a python file.
    the syntax is :
    /path/to/python/file.py:design_variable_name
    example:
    /home/user/design.py:my_design
    :return:
    """
    design_path = os.environ['PINJECTED_DEFAULT_DESIGN_PATH']
    return _load_design(design_path)


def _load_design(design_path):
    if design_path == "":
        return Design()
    script_path, var_name = design_path.split(':')
    design = load_variable_from_script(script_path, var_name)
    assert isinstance(design, Design), f"design loaded from {design_path} is not a Design instance"
    return design


def load_user_overrides_design():
    """
    This function loads user specific environment data from a python file.
    the syntax is :
    /path/to/python/file.py:design_variable_name
    example:
    /home/user/design.py:my_design
    :return:
    """
    return _load_design(os.environ['PINJECTED_OVERRIDE_DESIGN_PATH'])
