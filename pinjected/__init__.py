from pinjected.di.injected import Injected
from pinjected.di.decorators import injected_function, injected_instance, injected, instance, reload
from pinjected.di.util import EmptyDesign, instances, providers, classes, destructors, design
from pinjected.di.design_interface import Design
from pinjected.di.designed import Designed
from pinjected.di.proxiable import DelegatedVar as IProxy

__all__ = [
    "Injected",
    "EmptyDesign",
    "instances",
    "providers",
    "classes",
    "instance",
    "injected",
    "reload",
    "destructors",
    "Design",
    "IProxy",
    "design"
]
