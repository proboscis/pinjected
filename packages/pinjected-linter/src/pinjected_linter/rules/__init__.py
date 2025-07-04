"""Linter rules for Pinjected."""

from .base import ASTRuleBase, BaseNodeVisitor, BaseRule

# Import specific rules as they are implemented
from .pinj001_instance_naming import PINJ001InstanceNaming
from .pinj002_instance_defaults import PINJ002InstanceDefaults
from .pinj003_async_instance_naming import PINJ003AsyncInstanceNaming
from .pinj004_direct_instance_call import PINJ004DirectInstanceCall
from .pinj005_instance_imports import PINJ005InstanceImports
from .pinj006_instance_side_effects import PINJ006InstanceSideEffects
from .pinj007_instance_runtime_dependencies import PINJ007InstanceRuntimeDependencies
from .pinj008_injected_dependency_declaration import (
    PINJ008InjectedDependencyDeclaration,
)
from .pinj009_injected_async_prefix import PINJ009InjectedAsyncPrefix
from .pinj010_design_usage import PINJ010DesignUsage
from .pinj011_iproxy_annotations import PINJ011IProxyAnnotations
from .pinj015_missing_slash import PINJ015MissingSlash

# Rule registry
RULE_CLASSES = [
    PINJ001InstanceNaming,
    PINJ002InstanceDefaults,
    PINJ003AsyncInstanceNaming,
    PINJ004DirectInstanceCall,
    PINJ005InstanceImports,
    PINJ006InstanceSideEffects,
    PINJ007InstanceRuntimeDependencies,
    PINJ008InjectedDependencyDeclaration,
    PINJ009InjectedAsyncPrefix,
    PINJ010DesignUsage,
    PINJ011IProxyAnnotations,
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
