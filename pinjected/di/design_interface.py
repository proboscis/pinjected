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

import asyncio
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pprint import pformat
from typing import Dict, Callable, Any, List, Awaitable, Optional

from beartype import beartype

from pinjected.di.graph import DependencyResolver
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.validation import ValResult
from pinjected.module_var_path import ModuleVarPath
from pinjected.v2.binds import IBind
from pinjected.v2.keys import IBindKey, StrBindKey

ProvisionValidator = Callable[[IBindKey, Any], Awaitable[ValResult]]


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
        return resolver.purified_design(target).unbind(
            StrBindKey('__resolver__')).unbind(
            StrBindKey('session')).unbind(
            StrBindKey('__design__')).unbind(
            StrBindKey('__task_group__'))

    def __enter__(self):
        frame = inspect.currentframe().f_back
        DESIGN_OVERRIDES_STORE.add(frame, self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        frame = inspect.currentframe().f_back
        DESIGN_OVERRIDES_STORE.pop(frame)

    @property
    @abstractmethod
    def bindings(self) -> Dict[IBindKey, IBind]:
        pass

    @property
    @abstractmethod
    def validations(self) -> Dict[IBindKey, ProvisionValidator]:
        pass

    @staticmethod
    def from_bindings(bindings: Dict[IBindKey, IBind]):
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

    def provide(self,tgt:str|IBindKey):
        from loguru import logger
        from pinjected.v2.resolver import AsyncResolver
        logger.warning(f"Design.provide is deprecated. please use AsyncResolver instead.")
        return AsyncResolver(self).to_blocking().provide(tgt)

    def to_graph(self):
        from loguru import logger
        from pinjected.v2.resolver import AsyncResolver
        logger.warning(f"Design.to_graph is deprecated. please use AsyncResolver instead.")
        return AsyncResolver(self).to_blocking()

    def diff(self, other):
        from pinjected.di.util import get_dict_diff
        d = get_dict_diff(self.bindings, other.bindings)
        return d

    def inspect_picklability(self):
        from pinjected.di.util import check_picklable
        from loguru import logger
        logger.info(f"checking picklability of bindings")
        check_picklable(self.bindings)




@dataclass
class DesignOverridesStore:
    bindings: dict[ModuleVarPath, Design] = field(default_factory=dict)
    stack: List['DesignOverrideContext'] = field(default_factory=list)

    def clear(self):
        """Clear all bindings and stack to reset the store state."""
        self.bindings.clear()
        self.stack.clear()

    def add(self, frame: inspect.FrameInfo, design: "Design"):
        """Add a new design context.
        
        If this is the first context being added (i.e., a new test is starting),
        clear any existing bindings to prevent cross-test contamination.
        
        Args:
            frame: The frame where the context is being entered
            design: The design to add to the context
        """
        if not self.stack:
            self.clear()
        
        # Create new context with link to parent context if one exists
        parent = self.stack[-1] if self.stack else None
        cxt = DesignOverrideContext(design, frame, parent_context=parent)
        self.stack.append(cxt)

    def pop(self, frame: inspect.FrameInfo):
        """Pop the top context from the stack and update bindings.
        
        When a context is popped, any variables created within that context should:
        1. Get their immediate bindings from the current context
        2. Inherit any bindings from outer contexts that aren't overridden
        
        Args:
            frame: The frame where the context is being exited
        """
        cxt = self.stack.pop()
        target_vars = cxt.exit(frame)
        
        # Get the effective design for this context (includes inherited designs)
        context_design = cxt.get_effective_design()
        
        # Only add bindings for variables that were created in this context
        # and haven't been bound yet
        for mvp in target_vars:
            if mvp not in self.bindings and mvp in cxt.owned_vars:
                self.bindings[mvp] = context_design
                
        # Clean up any bindings that were owned by this context but are no
        # longer needed (helps prevent binding count issues)
        self.bindings = {
            k: v for k, v in self.bindings.items()
            if k not in cxt.owned_vars or k in target_vars
        }

    def get_overrides(self, tgt: ModuleVarPath):
        return self.bindings.get(tgt, Design.empty())


DESIGN_OVERRIDES_STORE = DesignOverridesStore()


@dataclass
class DesignOverrideContext:
    src: Design
    init_frame: inspect.FrameInfo
    parent_context: Optional['DesignOverrideContext'] = None
    owned_vars: set[ModuleVarPath] = field(default_factory=set)

    def __post_init__(self):
        # get parent global variables
        # Handle both FrameInfo and direct frame objects
        if isinstance(self.init_frame, inspect.FrameInfo):
            parent_globals = self.init_frame.frame.f_globals
        else:
            parent_globals = self.init_frame.f_globals
        self.last_global_ids = {k: id(v) for k, v in parent_globals.items()}

    def get_effective_design(self) -> Design:
        """Get the effective design for this context, including inherited designs.
        
        The effective design is built by combining:
        1. Designs from outer contexts (if any)
        2. This context's own design
        
        Returns:
            Design: The combined design that should apply to variables in this context
        """
        if self.parent_context:
            return self.parent_context.get_effective_design() + self.src
        return self.src

    def exit(self, frame: inspect.FrameInfo) -> list[ModuleVarPath]:
        """Track variables that were created or modified in this context.
        
        When exiting a context, we:
        1. Identify which variables changed during this context
        2. Track only DelegatedVar and Injected instances
        3. Record these as owned by this context
        
        Args:
            frame: The frame being exited
            
        Returns:
            list[ModuleVarPath]: List of module paths for variables owned by this context
        """
        # Handle both FrameInfo and direct frame objects
        if isinstance(frame, inspect.FrameInfo):
            parent_globals = frame.frame.f_globals
        else:
            parent_globals = frame.f_globals
        current_ids = {k: id(v) for k, v in parent_globals.items()}
        
        # Find changed or new variables
        changed_keys = [
            k for k in current_ids 
            if k not in self.last_global_ids or current_ids[k] != self.last_global_ids[k]
        ]
        
        # Filter for DelegatedVar and Injected instances
        from pinjected import Injected
        target_vars = {
            k: v for k, v in ((k, parent_globals[k]) for k in changed_keys)
            if isinstance(v, (DelegatedVar, Injected))
        }
        
        # Convert to ModuleVarPath and track ownership
        mod_name = parent_globals["__name__"]
        paths = [ModuleVarPath(f"{mod_name}.{k}") for k in target_vars]
        self.owned_vars.update(paths)
        
        return paths
