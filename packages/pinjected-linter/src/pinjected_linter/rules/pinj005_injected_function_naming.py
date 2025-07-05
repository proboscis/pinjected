"""PINJ005: Injected function naming convention rule."""

import ast
from typing import Optional

from ..models import Fix, Position, RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ005Visitor(BaseNodeVisitor):
    """Visitor for checking injected function naming."""
    
    # Common verb prefixes that indicate actions
    VERB_PREFIXES = {
        "get_", "set_", "create_", "build_", "setup_", "initialize_",
        "make_", "fetch_", "load_", "save_", "delete_", "update_",
        "process_", "handle_", "execute_", "run_", "start_", "stop_",
        "open_", "close_", "connect_", "disconnect_", "prepare_",
        "generate_", "compute_", "calculate_", "validate_", "check_",
        "send_", "receive_", "parse_", "format_", "convert_", "transform_",
        "register_", "unregister_", "enable_", "disable_", "configure_",
        "mount_", "unmount_", "bind_", "unbind_", "attach_", "detach_",
        "compile_", "render_", "draw_", "write_", "read_", "scan_",
        "authenticate_", "authorize_", "verify_", "sign_", "encrypt_", "decrypt_",
    }
    
    # Common verbs that might appear alone or at the start
    STANDALONE_VERBS = {
        "init", "initialize", "setup", "build", "create", "make",
        "get", "fetch", "load", "process", "execute", "run",
        "validate", "check", "verify", "authenticate", "authorize",
        "parse", "format", "render", "compile", "transform",
        "start", "stop", "pause", "resume", "reset", "refresh",
        "handle", "manage", "control", "operate", "perform",
        "workflow", "pipeline", "orchestrate", "coordinate",
        "filter", "sort", "group", "aggregate", "reduce",
        "publish", "subscribe", "broadcast", "notify", "alert",
    }
    
    # Common noun patterns that indicate non-verb naming
    NOUN_SUFFIXES = {
        "_data", "_info", "_config", "_configuration", "_result",
        "_response", "_request", "_state", "_status", "_context",
        "_manager", "_handler", "_service", "_client", "_provider",
        "_factory", "_builder", "_validator", "_processor", "_controller",
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
        """Check if an @injected function uses verb naming."""
        if not has_decorator(node, "injected"):
            return
        
        function_name = node.name
        
        # Handle async prefix for async functions
        if isinstance(node, ast.AsyncFunctionDef) and function_name.startswith("a_"):
            # Check the part after 'a_' prefix
            name_without_prefix = function_name[2:]
            if not self._is_verb_form(name_without_prefix):
                self._report_violation(node, function_name, name_without_prefix)
        elif not self._is_verb_form(function_name):
            self._report_violation(node, function_name, function_name)
    
    def _is_verb_form(self, name: str) -> bool:
        """Check if a name follows verb naming convention."""
        # Empty or single char names are invalid
        if len(name) <= 1:
            return False
        
        # Check if it starts with a verb prefix
        for prefix in self.VERB_PREFIXES:
            if name.startswith(prefix):
                return True
        
        # Check if it's a standalone verb
        if name in self.STANDALONE_VERBS:
            return True
        
        # Check if first word (before underscore) is a verb
        first_word = name.split('_')[0]
        if first_word in self.STANDALONE_VERBS:
            return True
        
        # Check if it has noun suffixes (indicates non-verb form)
        for suffix in self.NOUN_SUFFIXES:
            if name.endswith(suffix):
                return False
        
        # Additional heuristic: if it's a single word that's not in our verb list,
        # it's likely a noun
        if '_' not in name and name not in self.STANDALONE_VERBS:
            return False
        
        return False
    
    def _report_violation(self, node, full_name: str, checked_name: str):
        """Report a naming violation."""
        suggestion = self._suggest_verb_form(checked_name)
        
        # For async functions with a_ prefix, adjust the suggestion
        if full_name.startswith("a_") and isinstance(node, ast.AsyncFunctionDef):
            suggestion = f"a_{suggestion}"
        
        fix = self._create_fix(node, full_name, suggestion) if suggestion else None
        
        self.add_violation(
            node,
            f"@injected function '{full_name}' uses noun form. Use verb form instead.",
            suggestion=(
                f"Consider renaming to '{suggestion}'" if suggestion 
                else "Use a verb form like 'get_', 'create_', 'process_', etc."
            ),
            fix=fix,
        )
    
    def _suggest_verb_form(self, name: str) -> Optional[str]:
        """Suggest a verb form for a noun-named function."""
        # Common noun to verb transformations
        if name.endswith("_data"):
            return f"get_{name}"
        elif name.endswith("_info") or name.endswith("_information"):
            return f"fetch_{name}"
        elif name.endswith("_config") or name.endswith("_configuration"):
            return f"load_{name}"
        elif name.endswith("_result"):
            return f"calculate_{name}"
        elif name.endswith("_response"):
            return f"get_{name}"
        elif name.endswith("_manager") or name.endswith("_handler"):
            # These are already action-oriented, might just need prefix
            return f"get_{name}"
        elif name == "data":
            return "get_data"
        elif name == "info":
            return "get_info"
        elif name == "config":
            return "load_config"
        elif name == "configuration":
            return "load_configuration"
        elif name == "result":
            return "get_result"
        elif name == "response":
            return "get_response"
        elif "_" not in name:
            # Single word, probably a noun
            return f"get_{name}"
        
        # For other cases, suggest adding a get_ prefix
        return f"get_{name}"
    
    def _create_fix(self, node, old_name: str, new_name: str) -> Optional[Fix]:
        """Create a fix to rename the function."""
        if not new_name:
            return None
        
        # Find the exact position of the function name after 'def' or 'async def'
        if isinstance(node, ast.AsyncFunctionDef):
            # For async functions, we need to account for 'async def '
            name_start_offset = node.col_offset + len("async def ")
        else:
            # For regular functions, account for 'def '
            name_start_offset = node.col_offset + len("def ")
        
        return Fix(
            start_pos=Position(line=node.lineno, column=name_start_offset),
            end_pos=Position(line=node.lineno, column=name_start_offset + len(old_name)),
            replacement=new_name,
            description=f"Rename '{old_name}' to '{new_name}' to follow verb naming convention",
        )


class PINJ005InjectedFunctionNaming(ASTRuleBase):
    """Rule for checking @injected function naming convention.
    
    @injected functions represent actions or operations that can be performed
    with injected dependencies. Using verb forms makes it clear that these
    are functions to be called, not values to be provided.
    """
    
    rule_id = "PINJ005"
    name = "Injected function naming convention"
    description = "@injected functions should use verb forms"
    severity = Severity.WARNING
    category = "naming"
    auto_fixable = True
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ005Visitor(self, context)