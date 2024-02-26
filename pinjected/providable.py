from typing import Union, Type, Callable, TypeVar

from pinjected import Injected
from pinjected.di.proxiable import DelegatedVar

T = TypeVar("T")
#DelegatedVar = TypeVar("DelegatedVar")
#Injected = TypeVar("Injected")
#Designed = TypeVar("Designed")
Providable = Union[str, Type[T], Injected[T], Callable, DelegatedVar]
