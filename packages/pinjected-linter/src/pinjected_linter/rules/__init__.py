"""Linter rules for Pinjected."""

from .base import ASTRuleBase, BaseNodeVisitor, BaseRule

# Import specific rules as they are implemented
from .pinj001_instance_naming import PINJ001InstanceNaming
from .pinj002_instance_defaults import PINJ002InstanceDefaults
from .pinj003_async_instance_naming import PINJ003AsyncInstanceNaming
from .pinj004_direct_instance_call import PINJ004DirectInstanceCall
from .pinj005_injected_function_naming import PINJ005InjectedFunctionNaming
from .pinj006_async_injected_naming import PINJ006AsyncInjectedNaming
from .pinj007_slash_separator_position import PINJ007SlashSeparatorPosition
from .pinj008_injected_dependency_declaration import (
    PINJ008InjectedDependencyDeclaration,
)
from .pinj009_no_await_in_injected import PINJ009NoAwaitInInjected
from .pinj010_design_usage import PINJ010DesignUsage
from .pinj011_iproxy_annotations import PINJ011IProxyAnnotations
from .pinj012_dependency_cycles import PINJ012DependencyCycles
from .pinj013_builtin_shadowing import PINJ013BuiltinShadowing
from .pinj014_missing_stub_file import PINJ014MissingStubFile
from .pinj015_missing_slash import PINJ015MissingSlash

# Rule registry
RULE_CLASSES = [
    PINJ001InstanceNaming,
    PINJ002InstanceDefaults,
    PINJ003AsyncInstanceNaming,
    PINJ004DirectInstanceCall,
    PINJ005InjectedFunctionNaming,
    PINJ006AsyncInjectedNaming,
    PINJ007SlashSeparatorPosition,
    PINJ008InjectedDependencyDeclaration,
    PINJ009NoAwaitInInjected,
    PINJ010DesignUsage,
    PINJ011IProxyAnnotations,
    PINJ012DependencyCycles,
    PINJ013BuiltinShadowing,
    PINJ014MissingStubFile,
    PINJ015MissingSlash,
]

RULES_BY_ID = {rule.rule_id: rule for rule in RULE_CLASSES}

__all__ = [
    "RULES_BY_ID",
    "RULE_CLASSES",
    "ASTRuleBase",
    "BaseNodeVisitor",
    "BaseRule",
]
