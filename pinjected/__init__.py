from pinjected.di.decorators import (
    injected,
    injected_instance,
    instance,
    register,
    reload,
)
from pinjected.di.design_interface import Design
from pinjected.di.design_spec.impl import SimpleBindSpec
from pinjected.di.design_spec.protocols import DesignSpec
from pinjected.di.designed import Designed
from pinjected.di.injected import Injected
from pinjected.di.iproxy import IProxy
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.util import (
    EmptyDesign,
    classes,
    design,
    destructors,
    instances,
    providers,
)
from pinjected.v2.async_resolver import AsyncResolver

# I want to use IProxy() as constructor. and also type check. what can i do?

__version__ = "0.2.252"

__all__ = [
    "AsyncResolver",
    "DelegatedVar",
    "Design",
    "DesignSpec",
    "Designed",
    "EmptyDesign",
    "IProxy",
    "Injected",
    "SimpleBindSpec",
    "classes",
    "design",
    "destructors",
    "injected",
    "injected_instance",
    "instance",
    "instances",
    "providers",
    "register",
    "reload",
]
