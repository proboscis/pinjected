"""PINJ013: Builtin shadowing detection rule."""

import ast
import builtins

from ..models import RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ013Visitor(BaseNodeVisitor):
    """Visitor for detecting built-in name shadowing."""
    
    def __init__(self, rule, context):
        super().__init__(rule, context)
        # Get all built-in names
        self.builtin_names = set(dir(builtins))
        
        # Common suggestions for built-in names
        self.suggestions = {
            "dict": ["config_dict", "settings_dict", "data_dict", "params_dict"],
            "list": ["item_list", "value_list", "result_list", "data_list"],
            "set": ["item_set", "unique_set", "data_set", "value_set"],
            "tuple": ["data_tuple", "result_tuple", "item_tuple", "value_tuple"],
            "str": ["text_str", "value_str", "data_str", "result_str"],
            "int": ["count_int", "value_int", "number_int", "id_int"],
            "float": ["value_float", "number_float", "score_float", "rate_float"],
            "bool": ["flag_bool", "is_enabled", "status_bool", "check_bool"],
            "type": ["object_type", "data_type", "value_type", "class_type"],
            "open": ["open_file", "file_opener", "open_resource", "open_connection"],
            "print": ["print_message", "log_message", "output_message", "display_message"],
            "input": ["user_input", "get_input", "read_input", "prompt_input"],
            "filter": ["filter_items", "apply_filter", "filter_data", "filter_values"],
            "map": ["map_values", "apply_map", "transform_items", "map_data"],
            "range": ["number_range", "value_range", "index_range", "item_range"],
            "len": ["get_length", "count_items", "calculate_length", "item_count"],
            "zip": ["zip_items", "combine_lists", "zip_values", "merge_lists"],
            "hash": ["compute_hash", "get_hash", "hash_value", "generate_hash"],
            "id": ["get_id", "object_id", "item_id", "unique_id"],
            "compile": ["compile_source", "compile_code", "compile_expression", "build_code"],
            "eval": ["evaluate_expression", "eval_code", "evaluate_string", "execute_expression"],
            "exec": ["execute_code", "exec_string", "run_code", "execute_script"],
            "format": ["format_string", "format_text", "apply_format", "format_value"],
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
        """Check if function shadows a built-in name."""
        # Only check functions with @instance or @injected decorators
        if not (has_decorator(node, "instance") or has_decorator(node, "injected")):
            return
        
        func_name = node.name
        
        # Check if the function name shadows a built-in
        if func_name in self.builtin_names:
            # Get suggestions for this built-in
            suggestions = self.suggestions.get(func_name, [])
            if not suggestions:
                # Generate generic suggestions
                if has_decorator(node, "instance"):
                    suggestions = [
                        f"{func_name}_provider",
                        f"{func_name}_instance",
                        f"get_{func_name}",
                        f"create_{func_name}"
                    ]
                else:
                    suggestions = [
                        f"{func_name}_func",
                        f"do_{func_name}",
                        f"handle_{func_name}",
                        f"process_{func_name}"
                    ]
            
            suggestion_text = f"Consider using a more descriptive name like '{suggestions[0]}' or '{suggestions[1]}'."
            
            self.add_violation(
                node,
                f"Function '{func_name}' shadows Python built-in name. {suggestion_text}",
                suggestion=suggestion_text
            )


class PINJ013BuiltinShadowing(ASTRuleBase):
    """Rule for detecting functions that shadow Python built-in names.
    
    Functions decorated with @instance or @injected should not use names
    that shadow Python built-ins like dict, list, open, etc. This can
    cause confusion and unexpected behavior.
    
    Examples:
        Bad:
            @instance
            def dict():  # Shadows built-in 'dict'
                return {}
            
            @injected
            def open(file_handler, /, path):  # Shadows built-in 'open'
                return file_handler.open(path)
        
        Good:
            @instance
            def config_dict():
                return {}
            
            @injected
            def open_file(file_handler, /, path):
                return file_handler.open(path)
    """
    
    rule_id = "PINJ013"
    name = "Builtin shadowing"
    description = "Functions should not shadow Python built-in names"
    severity = Severity.WARNING
    category = "naming"
    auto_fixable = False  # Renaming requires careful consideration
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ013Visitor(self, context)