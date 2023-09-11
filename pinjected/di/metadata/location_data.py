from dataclasses import dataclass
from pathlib import Path
from typing import Union

from pinjected.module_var_path import ModuleVarPath


@dataclass
class ModuleVarLocation:
    path: Path
    line: int
    column: int

CodeLocation = Union[
    ModuleVarPath,
    ModuleVarLocation
]
"""
a class to indicate the location of a python variable.
1. qualified_name i.e. ModuleVarPath: the qualified name of the variable.
2. file_path + line + column: the line and column of the variable.
"""
