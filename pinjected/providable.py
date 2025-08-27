from collections.abc import Callable
from typing import TypeVar, Union

from pinjected.di.injected import Injected
from pinjected.di.proxiable import DelegatedVar

T = TypeVar("T")
# DelegatedVar = TypeVar("DelegatedVar")
# Injected = TypeVar("Injected")
# Designed = TypeVar("Designed")
Providable = Union[str, type[T], Injected[T], Callable, DelegatedVar]
