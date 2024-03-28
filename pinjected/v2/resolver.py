import asyncio
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Union, Callable, Dict, Any, Optional

from loguru import logger

from pinjected import Injected
from pinjected.di.injected import extract_dependency
from pinjected.di.proxiable import DelegatedVar
from pinjected.v2.binds import IBind, BindInjected
from pinjected.v2.keys import IBindKey, StrBindKey
from pinjected.v2.provide_context import ProvideContext

Providable = Union[str, IBindKey, Callable, IBind]


class IScope(ABC):
    @abstractmethod
    def provide(self, tgt: IBindKey, cxt: ProvideContext, provider: Callable[[IBindKey, ProvideContext], Any]):
        pass


class ScopeNode(IScope):
    objects: Dict[IBindKey, Any] = field(default_factory=dict)

    def provide(self, tgt: IBindKey, cxt: ProvideContext, provider: Callable[[IBindKey, ProvideContext], Any]):
        if tgt not in self.objects:
            self.objects[tgt] = provider(tgt, cxt)

        return self.objects[tgt]


@dataclass
class AsyncResolver:
    design: "Design"
    parent: Optional["AsyncResolver"] = None
    objects: Dict[IBindKey, Any] = field(default_factory=dict)

    def __post_init__(self):
        from pinjected import injected, instance, providers
        async def dummy():
            raise RuntimeError('This should never be instantiated')
        dummy = Injected.bind(dummy)

        self.design = self.design + providers(
            __resolver__=dummy,
            __design__=dummy
        )
        self.objects = {
            StrBindKey("__resolver__"): self,
            StrBindKey("__design__"): self.design
        }

    async def _provide(self, key: IBindKey, cxt: ProvideContext):
        # we need to think which one to ask provider
        # if we have the binding for the key, use our own scope
        if key in self.objects:
            data = self.objects[key]
            return data
        elif key in self.design:
            logger.info(f"{cxt.trace_str}")
            # we are responsible for providing this
            bind = self.design.bindings[key]
            dep_keys = list(bind.dependencies)
            tasks = []
            for dep_key in dep_keys:
                n_cxt = ProvideContext(key=dep_key, parent=cxt)
                tasks.append(self._provide(dep_key, n_cxt))
            res = await asyncio.gather(*tasks)
            deps = dict(zip(dep_keys, res))
            data = await bind.provide(cxt, deps)
            self.objects[key] = data
            show_data = str(data)[:100]
            logger.info(f"{cxt.trace_str} := {show_data}")
            return data
        else:
            if self.parent is not None:
                return await self.parent._provide(key, cxt)
            else:
                raise KeyError(f"Key {key} not found in design in {cxt.trace_str}")

    def child_session(self, overrides: "Design"):
        return AsyncResolver(overrides, parent=self)

    async def _provide_providable(self, tgt: Providable):
        async def resolve_deps(keys: set[IBindKey]):
            tasks = [self._provide(k, ProvideContext(key=k, parent=None)) for k in keys]
            return {k: v for k, v in zip(keys, await asyncio.gather(*tasks))}

        logger.info(f"providing {tgt}")
        match tgt:
            case str():
                return await self._provide(StrBindKey(tgt), ProvideContext(key=StrBindKey(tgt), parent=None))
            case IBindKey():
                return await self._provide(tgt, ProvideContext(key=tgt, parent=None))
            case DelegatedVar():
                return await self._provide_providable(tgt.eval())
            case Injected() as i_tgt:
                return await self._provide_providable(BindInjected(i_tgt))
            case IBind():
                deps = await resolve_deps(tgt.dependencies)
                return await tgt.provide(ProvideContext(key=tgt, parent=None), deps)
            case func if inspect.isfunction:
                deps = extract_dependency(func)
                logger.info(f"Resolving deps for {func} -> {deps}")
                keys = {StrBindKey(d) for d in deps}
                deps = await resolve_deps(keys)
                kwargs = {k.name: v for k, v in deps.items()}
                data = tgt(**kwargs)
                if inspect.iscoroutinefunction(tgt):
                    return await data
                else:
                    return data
            case _:
                raise TypeError(f"tgt must be str, IBindKey, Callable or IBind, got {tgt}")

    async def provide(self, tgt: Providable):
        return await self._provide_providable(tgt)

    def to_blocking(self):
        return Resolver(self)

    def __getitem__(self, item):
        return self.provide(item)


@dataclass
class Resolver:
    resolver: AsyncResolver

    def provide(self, tgt: Providable):
        return asyncio.run(self.resolver.provide(tgt))

    def child_session(self, overrides: "Design"):
        return Resolver(self.resolver.child_session(overrides))

    def to_async(self):
        return self.resolver

    def __getitem__(self, item):
        return self.provide(item)
