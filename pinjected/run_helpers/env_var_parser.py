"""Environment variable parser for PINJECTED_* variables."""

import os
from typing import Dict, Any
from loguru import logger
from pinjected import design
from pinjected.module_var_path import load_variable_by_module_path


def parse_kwargs_as_design(**kwargs):
    """
    When a value is in '{pkg.varname}' format, we import the variable and use it as the value.
    """
    res = design()
    for k, v in kwargs.items():
        if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
            v = v[1:-1]
            loaded = load_variable_by_module_path(v)
            res += design(**{k: loaded})
        else:
            res += design(**{k: v})
    return res


def parse_pinjected_env_vars() -> Dict[str, Any]:
    """
    Parse all PINJECTED_* environment variables into a kwargs dict.

    Converts environment variable names from PINJECTED_API_KEY format
    to api_key format (lowercase with underscores).

    Returns:
        Dictionary of kwargs ready for parse_kwargs_as_design()
    """
    env_kwargs = {}

    for env_name, env_value in os.environ.items():
        if env_name.startswith("PINJECTED_"):
            # Remove PINJECTED_ prefix and convert to lowercase
            key_name = env_name[10:].lower()  # Skip 'PINJECTED_'

            if not key_name:
                logger.warning(f"Skipping empty key from env var: {env_name}")
                continue

            env_kwargs[key_name] = env_value
            logger.debug(f"Parsed env var {env_name} -> {key_name}={env_value!r}")

    return env_kwargs
