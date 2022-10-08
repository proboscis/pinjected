import uuid
from dataclasses import dataclass, field

from pinject.scoping import BindableScopes


@dataclass
class ISessionScope:

    def provide(self, bidning_key, default_provider_fn):
        pass


@dataclass
class SessionScope(ISessionScope):
    cache: dict = field(default_factory=dict)

    def __post_init__(self):
        self._id = uuid.uuid4()

    def provide(self, binding_key, default_provider_fn):
        #logger.info(f"{self} provide {binding_key}")
        if not binding_key in self.cache:
            self.cache[binding_key] = default_provider_fn()
        return self.cache[binding_key]

    def __str__(self):
        return f"SessionScope:{str(self._id)[:5]}"

    def __contains__(self, item):
        return item in self.cache


@dataclass
class ChildScope(ISessionScope):
    parent: SessionScope
    override_targets:set
    cache: dict = field(default_factory=dict)

    def __post_init__(self):
        self._id = uuid.uuid4()

    def __str__(self):
        return f"{self.parent}=>{str(self._id)[:5]}"

    def provide(self, binding_key, default_provider_fn):
        #logger.info(f"{self} provide {binding_key}")
        if binding_key not in self.cache:
            if binding_key in self.override_targets:
                self.cache[binding_key] = default_provider_fn()
            elif binding_key in self.parent:
                return self.parent.provide(binding_key,default_provider_fn)
            else:
                # things which are not created in parent will be deleted after this scope.
                self.cache[binding_key] = default_provider_fn()
        return self.cache[binding_key]


    def __contains__(self, item):
        return item in self.cache or item in self.parent


@dataclass
class OverridenBindableScopes:
    parent: BindableScopes
    override_targets:set

    def __post_init__(self):
        self.scopes = dict()

    def get_sub_scope(self, binding):
        if binding.scope_id not in self.scopes:
            parent_scope = self.parent.get_sub_scope(binding)
            self.scopes[binding.scope_id] = ChildScope(parent_scope,self.override_targets)
        return self.scopes[binding.scope_id]

