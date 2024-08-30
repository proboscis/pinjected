import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field



@dataclass
class ISessionScope(ABC):
    @abstractmethod
    def provide(self, bidning_key, default_provider_fn):
        pass


@dataclass
class SessionScope(ISessionScope):
    cache: dict = field(default_factory=dict)

    def __post_init__(self):
        self._id = uuid.uuid4()
        self.provide_depth = 0
        self.pending = []

    def provide(self, binding_key, default_provider_fn):
        # logger.info(f"{self} provide {binding_key}")
        if not binding_key in self.cache:
            from loguru import logger
            self.provide_depth += 1
            indent = "| " * self.provide_depth
            self.pending.append(binding_key)
            logger.debug(f'Providing:{"<-".join([k._name for k in self.pending])}')
            #logger.debug(f"SessionScope: {indent} -> {binding_key._name}")
            value = default_provider_fn()
            self.cache[binding_key] = value
            self.pending.pop()
            logger.debug(f'Remaining:{"<-".join([k._name for k in self.pending])} {binding_key}={str(value)[:100]}')
            #logger.debug(f"SessionScope: {indent} <- {binding_key._name}")
            self.provide_depth -= 1
        return self.cache[binding_key]

    def __str__(self):
        return f"SessionScope:{str(self._id)[:5]}"

    def __contains__(self, item):
        return item in self.cache

    def cached(self, binding_key) -> bool:
        return binding_key in self.cache


@dataclass
class ChildScope(ISessionScope):
    parent: SessionScope
    override_targets: set
    cache: dict = field(default_factory=dict)

    def __post_init__(self):
        self._id = uuid.uuid4()

    def __str__(self):
        return f"{self.parent}=>{str(self._id)[:5]}"

    def provide(self, binding_key, default_provider_fn):
        # logger.info(f"{self} provide {binding_key}")
        if binding_key not in self.cache:
            from loguru import logger
            logger.debug(f"ChildScope: -> {binding_key}")
            if binding_key in self.override_targets:
                self.cache[binding_key] = default_provider_fn()
            elif binding_key in self.parent:  # this means that this thing is already cached in the parent
                return self.parent.provide(binding_key, default_provider_fn)
            else:
                # things which are not created in parent will be deleted after this scope.
                self.cache[binding_key] = default_provider_fn()
            logger.debug(f"ChildScope: <- {binding_key}")
        return self.cache[binding_key]

    def __contains__(self, item):
        return item in self.cache or item in self.parent
