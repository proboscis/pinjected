"""
This module defines the Design interface for the pinjected dependency injection system.
The interface was extracted (as per issue #26) to provide a clear contract for dependency
configuration and management. This separation enables multiple implementations with different
strategies for handling dependencies, validations, and metadata.

Key implementations of this interface can be found in design.py:
- MergedDesign: Combines multiple designs with precedence rules
- AddValidation: Adds validation capabilities to existing designs
- MetaDataDesign: Handles metadata-only designs
- DesignImpl: Standard implementation with direct bindings management
"""

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beartype import beartype
from returns.maybe import Maybe, Nothing

from pinjected.di.graph import DependencyResolver
from pinjected.di.proxiable import DelegatedVar
from pinjected.module_var_path import ModuleVarPath
from pinjected.v2.binds import IBind
from pinjected.v2.keys import IBindKey, StrBindKey

if TYPE_CHECKING:
    from pinjected.providable import Providable


class Design(ABC):
    def __add__(self, other: "Design") -> "Design":
        from pinjected.di.design import MergedDesign

        return MergedDesign(srcs=[self, other])

    @abstractmethod
    def __contains__(self, item: IBindKey):
        pass

    @abstractmethod
    @beartype
    def __getitem__(self, item: IBindKey | str) -> IBind:
        pass

    def purify(self, target: "Providable"):
        resolver = DependencyResolver(self)
        return (
            resolver.purified_design(target)
            .unbind(StrBindKey("__resolver__"))
            .unbind(StrBindKey("session"))
            .unbind(StrBindKey("__design__"))
            .unbind(StrBindKey("__task_group__"))
        )

    def __enter__(self):
        frame = inspect.currentframe().f_back
        DESIGN_OVERRIDES_STORE.add(frame, self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        frame = inspect.currentframe().f_back
        DESIGN_OVERRIDES_STORE.pop(frame)

    @property
    @abstractmethod
    def bindings(self) -> dict[IBindKey, IBind]:
        pass

    @staticmethod
    def from_bindings(bindings: dict[IBindKey, IBind]):
        from pinjected.di.design import DesignImpl

        return DesignImpl(_bindings=bindings)

    @staticmethod
    def empty():
        from pinjected.di.design import DesignImpl

        return DesignImpl()

    @property
    @abstractmethod
    def children(self):
        pass

    def dfs_design(self):
        yield self
        for c in self.children:
            yield from c.dfs_design()

    def keys(self):
        return self.bindings.keys()

    def provide(self, tgt: str | IBindKey, default: Maybe = Nothing):
        tgt = StrBindKey(tgt) if isinstance(tgt, str) else tgt
        if tgt not in self and default is not Nothing:
            return default.unwrap()
        from pinjected.pinjected_logging import logger
        from pinjected.v2.async_resolver import AsyncResolver

        logger.warning(
            "Design.provide is deprecated. please use AsyncResolver instead."
        )
        return AsyncResolver(self).to_blocking().provide(tgt)

    def to_graph(self):
        from pinjected.pinjected_logging import logger
        from pinjected.v2.async_resolver import AsyncResolver

        logger.warning(
            "Design.to_graph is deprecated. please use AsyncResolver instead."
        )
        return AsyncResolver(self).to_blocking()

    def diff(self, other):
        from pinjected.di.util import get_dict_diff

        d = get_dict_diff(self.bindings, other.bindings)
        return d

    def inspect_picklability(self):
        from pinjected.di.util import check_picklable
        from pinjected.pinjected_logging import logger

        logger.info("checking picklability of bindings")
        check_picklable(self.bindings)


@dataclass
class DesignOverridesStore:
    bindings: dict[ModuleVarPath, Design] = field(default_factory=dict)
    stack: list["DesignOverrideContext"] = field(default_factory=list)

    def add(self, frame: inspect.FrameInfo, design: "Design"):
        cxt = DesignOverrideContext(design, frame)
        self.stack.append(cxt)

    def pop(self, frame: inspect.FrameInfo):
        cxt = self.stack.pop()
        acc_d = sum([cxt.src for cxt in self.stack], start=Design.empty()) + cxt.src
        target_vars = cxt.exit(frame)
        for mvp in target_vars:
            if mvp not in self.bindings:
                self.bindings[mvp] = acc_d

    def get_overrides(self, tgt: ModuleVarPath):
        return self.bindings.get(tgt, Design.empty())


DESIGN_OVERRIDES_STORE = DesignOverridesStore()


@dataclass
class DesignOverrideContext:
    src: Design
    init_frame: inspect.FrameInfo

    def __post_init__(self):
        # get parent global variables
        parent_globals = self.init_frame.f_globals
        global_ids = {k: id(v) for k, v in parent_globals.items()}
        # logger.debug(f"enter->\n"+pformat(global_ids))
        # print("enter->\n"+pformat(global_ids))
        self.last_global_ids = global_ids

    def exit(self, frame: inspect.FrameInfo) -> list[ModuleVarPath]:
        # get parent global variables
        parent_globals = frame.f_globals
        global_ids = {k: id(v) for k, v in parent_globals.items()}
        # print("exit->\n"+pformat(global_ids))
        changed_keys = []
        for k in global_ids:
            if k in self.last_global_ids:
                if global_ids[k] != self.last_global_ids[k]:
                    changed_keys.append(k)
            else:
                changed_keys.append(k)
        # logger.debug(f"global_ids:{global_ids}")
        # find instance of DelegatedVar and Injected in the changed globals
        target_vars = dict()
        from pinjected import Injected

        for k in changed_keys:
            v = parent_globals[k]
            if isinstance(v, DelegatedVar):
                target_vars[k] = v
            if isinstance(v, Injected):
                target_vars[k] = v

        mod_name = frame.f_globals["__name__"]
        # mod_name = inspect.getmodule(frame).__name__
        # logger.info(f"found targets:\n{pformat(target_vars)}")
        return [ModuleVarPath(mod_name + "." + v) for v in target_vars]
