"""PINJ002: Instance function default arguments rule."""

import ast
from typing import List, Optional

from ..models import Fix, RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ002Visitor(BaseNodeVisitor):
    """Visitor for checking instance function default arguments."""
    
    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def _check_function(self, node):
        """Check if an @instance function has default arguments."""
        if not has_decorator(node, "instance"):
            return
        
        # Check for default arguments
        defaults = node.args.defaults
        if defaults:
            # Calculate which arguments have defaults
            # defaults list corresponds to the last len(defaults) arguments
            args_with_defaults = []
            num_args = len(node.args.args)
            num_defaults = len(defaults)
            
            for i in range(num_defaults):
                arg_index = num_args - num_defaults + i
                arg = node.args.args[arg_index]
                default = defaults[i]
                args_with_defaults.append((arg.arg, self._default_to_str(default)))
            
            # Report violation
            default_strs = [f"{name}={value}" for name, value in args_with_defaults]
            self.add_violation(
                node,
                f"@instance function '{node.name}' has default arguments: {', '.join(default_strs)}. "
                f"Use design() for configuration instead.",
                suggestion=self._generate_suggestion(node.name, args_with_defaults),
                fix=self._create_fix(node),
            )
    
    def _default_to_str(self, node) -> str:
        """Convert default value AST node to string representation."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Str):  # Python < 3.8
            return repr(node.s)
        elif isinstance(node, ast.Num):  # Python < 3.8
            return str(node.n)
        else:
            # For complex expressions, use a generic representation
            return "..."
    
    def _generate_suggestion(self, func_name: str, args_with_defaults: List[tuple]) -> str:
        """Generate suggestion for using design() instead."""
        design_args = [f"    {name}={value}" for name, value in args_with_defaults]
        args_str = ',\n'.join(design_args)
        return (
            f"Consider using:\n"
            f"base_design = design(\n"
            f"{args_str}\n"
            f")\n"
            f"Then use base_design in your composition."
        )
    
    def _create_fix(self, node: ast.FunctionDef) -> Optional[Fix]:
        """Create a fix to remove default arguments."""
        # This is a complex fix that would require updating the function signature
        # For now, we'll just provide the violation without auto-fix
        # A full implementation would need to:
        # 1. Remove defaults from function signature
        # 2. Create a design() call with the defaults
        # 3. Update all callers to use the design
        return None


class PINJ002InstanceDefaults(ASTRuleBase):
    """Rule for checking instance function default arguments."""
    
    rule_id = "PINJ002"
    name = "Instance function default arguments"
    description = "@instance functions should not have default arguments"
    severity = Severity.ERROR
    category = "design"
    auto_fixable = False  # Complex fix requires refactoring
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ002Visitor(self, context)