"""PINJ001: Instance function naming convention rule."""

import ast
from typing import Optional

from ..models import Fix, Position, RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ001Visitor(BaseNodeVisitor):
    """Visitor for checking instance function naming."""
    
    # Common verb prefixes that indicate actions
    VERB_PREFIXES = {
        "get_", "set_", "create_", "build_", "setup_", "initialize_",
        "make_", "fetch_", "load_", "save_", "delete_", "update_",
        "process_", "handle_", "execute_", "run_", "start_", "stop_",
        "open_", "close_", "connect_", "disconnect_", "prepare_",
        "generate_", "compute_", "calculate_", "validate_", "check_",
    }
    
    # Common verbs that might appear alone
    STANDALONE_VERBS = {
        "init", "initialize", "setup", "build", "create", "make",
        "get", "fetch", "load", "process", "execute", "run",
    }
    
    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def _check_function(self, node):
        """Check if an @instance function uses verb naming."""
        if not has_decorator(node, "instance"):
            return
        
        function_name = node.name
        
        # Check for verb prefixes
        for prefix in self.VERB_PREFIXES:
            if function_name.startswith(prefix):
                suggestion = self._suggest_noun_form(function_name, prefix)
                fix = self._create_fix(node, function_name, suggestion)
                self.add_violation(
                    node,
                    f"@instance function '{function_name}' uses verb form. "
                    f"Use noun form instead.",
                    suggestion=f"Consider renaming to '{suggestion}'",
                    fix=fix,
                )
                return
        
        # Check for standalone verbs
        if function_name in self.STANDALONE_VERBS:
            # For standalone verbs, suggest a generic noun form
            suggestion = self._suggest_noun_for_verb(function_name)
            fix = self._create_fix(node, function_name, suggestion) if suggestion else None
            default_suggestion = (
                "@instance functions should represent what is provided, not actions"
            )
            self.add_violation(
                node,
                f"@instance function '{function_name}' uses verb form. "
                f"Use noun form instead.",
                suggestion=f"Consider renaming to '{suggestion}'" if suggestion else default_suggestion,
                fix=fix,
            )
    
    def _suggest_noun_form(self, name: str, verb_prefix: str) -> str:
        """Suggest a noun form for a verb-based name."""
        # Remove the verb prefix
        remainder = name[len(verb_prefix):]
        
        # Special cases
        if verb_prefix == "get_" and remainder.endswith("_connection"):
            return remainder  # "connection" is already a noun
        elif verb_prefix == "create_" and remainder.endswith("_factory"):
            return remainder  # "factory" is already a noun
        elif verb_prefix in ("get_", "fetch_", "load_") or verb_prefix in ("create_", "build_", "make_"):
            return remainder  # Just remove the verb
        elif verb_prefix == "setup_":
            return remainder  # Just remove "setup_"
        
        # Default: just remove the verb prefix
        return remainder if remainder else name
    
    def _suggest_noun_for_verb(self, verb: str) -> Optional[str]:
        """Suggest a noun form for a standalone verb."""
        verb_to_noun = {
            "init": "initializer",
            "initialize": "initializer",
            "setup": "configuration",
            "build": "builder",
            "create": "creator",
            "make": "maker",
            "get": "getter",
            "fetch": "fetcher",
            "load": "loader",
            "process": "processor",
            "execute": "executor",
            "run": "runner",
        }
        return verb_to_noun.get(verb)
    
    def _create_fix(self, node: ast.FunctionDef, old_name: str, new_name: str) -> Fix:
        """Create a fix to rename the function."""
        # The function name appears after 'def '
        # We need to find where the name starts in the line
        start_pos = Position(
            line=node.lineno,
            column=node.col_offset + 4,  # 'def ' is 4 characters
        )
        end_pos = Position(
            line=node.lineno,
            column=node.col_offset + 4 + len(old_name),
        )
        
        return Fix(
            start_pos=start_pos,
            end_pos=end_pos,
            replacement=new_name,
            description=f"Rename '{old_name}' to '{new_name}'",
        )


class PINJ001InstanceNaming(ASTRuleBase):
    """Rule for checking instance function naming convention."""
    
    rule_id = "PINJ001"
    name = "Instance function naming convention"
    description = "@instance functions should use noun forms, not verbs"
    severity = Severity.ERROR
    category = "naming"
    auto_fixable = True
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ001Visitor(self, context)