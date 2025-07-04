"""Linter rules for Pinjected."""

from .base import ASTRuleBase, BaseNodeVisitor, BaseRule

# Import specific rules as they are implemented
from .pinj001_instance_naming import PINJ001InstanceNaming
from .pinj002_instance_defaults import PINJ002InstanceDefaults
from .pinj003_async_instance_naming import PINJ003AsyncInstanceNaming
from .pinj004_direct_instance_call import PINJ004DirectInstanceCall
from .pinj008_injected_dependency_declaration import PINJ008InjectedDependencyDeclaration
from .pinj015_missing_slash import PINJ015MissingSlash

# Rule registry
RULE_CLASSES = [
    PINJ001InstanceNaming,
    PINJ002InstanceDefaults,
    PINJ003AsyncInstanceNaming,
    PINJ004DirectInstanceCall,
    PINJ008InjectedDependencyDeclaration,
    PINJ015MissingSlash,
]

RULES_BY_ID = {rule.rule_id: rule for rule in RULE_CLASSES}

__all__ = [
    "BaseRule",
    "ASTRuleBase", 
    "BaseNodeVisitor",
    "RULE_CLASSES",
    "RULES_BY_ID",
]