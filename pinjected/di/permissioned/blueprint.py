from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, List, Any, Callable

from returns.maybe import Maybe, Nothing, Some

from pinjected import Injected, injected_function
from returns import maybe as raybe

from pinjected.di.graph import IObjectGraph, Providable


def maybe__or__(self, other):
    match self:
        case Some(x):
            return self
        case raybe.Nothing:
            return other


def maybe_filter(self: Maybe, flag_to_keep):
    match self.map(flag_to_keep):
        case Some(True):
            return self
        case _:
            return Nothing


Maybe.__or__ = maybe__or__
Maybe.filter = maybe_filter


class ResourceManifest(ABC):
    """
    determines who can access this resource.
    determines any metadata of this resource.
    """
    pass


class RequesterManifest(ABC):
    """
    determines who is requesting a resource
    metadata of a requester.
    """
    pass


@dataclass(frozen=True)
class ResourcePathManifest(ResourceManifest):
    path: str


@dataclass(frozen=True)
class RequesterPathManifest(RequesterManifest):
    path: str


@dataclass(frozen=True)
class DirectRequesterManifest(RequesterManifest):
    pass


REQUESTER_NO_MANIFEST = DirectRequesterManifest()


@dataclass(frozen=True)
class BindingKey:
    name: str
    manifest: ResourceManifest


@dataclass(frozen=True)
class Binding:
    # a binding uses this manifest to request other dependencies
    src: Injected
    manifest: RequesterManifest


@dataclass(frozen=True)
class Blueprint:
    bindings: Dict[BindingKey, Binding]
    pass


@dataclass
class PermissionManager:
    def is_allowed(self, requester: RequesterManifest, resource: ResourceManifest) -> bool:
        return namespace_permission_rule(requester, resource)
        # return True

    def prioritize(self, manifests: List[ResourceManifest], requester: RequesterManifest) -> List[ResourceManifest]:
        return manifests


class HasPath(ABC):
    __match_args__ = ("path",)

    @classmethod
    def __subclasshook__(cls, C):
        return not hasattr(C, "path")


def namespace_permission_rule(requester: RequesterManifest, resource: ResourceManifest) -> bool:
    """
    check for a full path of the resource and a full path of the requester.
    if a requester lives inside a resource's module, then it is allowed.
    :param requester:
    :param resource:
    :return:
    """
    match requester, resource:
        case (HasPath(path=req_path), HasPath(path=res_path)):
            res_mod = '.'.join(res_path.split(".")[:-1])
            if req_path.startswith(res_mod):
                return True
            else:
                return False
        case _:
            return False


GLOBAL_BINDINGS: Dict[BindingKey, Binding] = dict()


class IBPScope(ABC):
    @abstractmethod
    def provide(self,
                key: BindingKey,
                provider_func: Callable[[], Any],
                trace: list
                ) -> Optional[Providable]:
        pass


@dataclass
class Resolver:
    blueprint: Blueprint
    permission_manager: PermissionManager

    @staticmethod
    def find_binding(
            bindings: Dict[BindingKey, Binding],
            permission_manager: PermissionManager,
            key: str,
            requester: RequesterManifest
    ):
        matched = [k for k in bindings.keys() if
                   k.name == key and permission_manager.is_allowed(requester, k.manifest)]
        if len(matched) == 0:
            return Nothing
        else:
            matched = Resolver.prioritize_binding_keys(permission_manager, matched, requester)
            return Some(bindings[matched[0]])

    @staticmethod
    def prioritize_binding_keys(permission_manager, keys: List[BindingKey], requester):
        """
        prioritize the binding keys according to the requester
        :param keys:
        :param requester:
        :return:
        """
        m2k = {k.manifest: k for k in keys}
        sorted_manifests = permission_manager.prioritize(list(m2k.keys()), requester)
        sorted_keys = [m2k[m] for m in sorted_manifests]
        return sorted_keys

    def find_allowed_binding_key(self, key: str, requester: RequesterManifest) -> Maybe[Binding]:
        """
        find a bindingkey that matches the key and is allowed by the requester
        :param key:
        :param requester:
        :return:
        """
        return self.find_binding(
            self.blueprint.bindings,
            self.permission_manager,
            key,
            requester
        )

    def find_global_default_binding_key(self, key: str, requester: RequesterManifest) -> Maybe[Binding]:
        return self.find_binding(
            GLOBAL_BINDINGS,
            self.permission_manager,
            key,
            requester
        )

    def resolve(self, key: str, requester: RequesterManifest = REQUESTER_NO_MANIFEST):
        assert isinstance(key, str)
        assert isinstance(requester, RequesterManifest)
        binding = self.find_allowed_binding_key(key, requester) | self.find_global_default_binding_key(key, requester)
        match binding:
            case Some(Binding(src, manifest)):
                src: Injected
                deps = src.dependencies()
                resources = {k: self.resolve(k, manifest) for k in deps}
                return src.get_provider()(**resources)
            case raybe.Nothing:
                raise RuntimeError(f"cannot find a binding for key: {key} using {requester}")
            case _:
                raise RuntimeError("unexpected case: %s" % binding)


@dataclass
class BlueprintGraph(IObjectGraph):

    def provide(self, target: Providable, level: int = 2):
        pass

    def child_session(self, overrides=None) -> "IObjectGraph":
        pass

    @property
    def design(self):
        """
        in order to convert a blueprint into a design,
        we need to first resolve the binding key assignments.
        iterate through all the bindings and find appropriate binding so that it can be resolved later using Design.
        I think we should remove this property from an ObjectGraph interface.
        :return:
        """
        raise NotImplementedError("BlueprintGraph does not have a design and this property will be deprecated")


# now let's make a binding key and a bind!

def binding(func):
    src = injected_function(func)
    # get the module path which this function is called.
    import inspect
    frame = inspect.currentframe()
    caller_frame = frame.f_back
    caller_module = inspect.getmodule(caller_frame)
    caller_path = caller_module.__name__
    key = BindingKey(func.__name__, ResourcePathManifest(caller_path))
    bind = Binding(src, RequesterPathManifest(caller_path))
    GLOBAL_BINDINGS[key] = bind
    return bind


"""
Now we have a resolver.
Next thing we need:
1. a Session to manage the instance lifecycle
2. adding a metadata to an injected function.
3. making a blueprint from a design -> abandone
"""

"""
we can actually use this in later,
however, for my current need,
I think it is okey for me to hack
'injected_funcion' to add a namespace metadata
and then make Design implicitly look for it...
hmm,, however, this has some problem after pickling...
since the GLOBAL_BINDINGS won't be pickled over serialization,
the Design has no way of telling the implicit bindings after deserialization.
A solution is to freeze the design with global_bindings on pickling.
Actually, since the Design cannot hold non unique string key, we still need to use a naming of util functions that are unique.
to overcome this, we can use a func name with full module path as a binding key.
and then, use '__' to let the resolver know that the functions should be implicitly resolved.
"""
