"""PINJ014: Missing .pyi stub file rule."""

import ast
from pathlib import Path
from typing import List

from ..models import RuleContext, Severity, Violation
from ..utils.ast_utils import has_decorator
from .base import BaseRule


class PINJ014MissingStubFile(BaseRule):
    """Rule for checking missing .pyi stub files for modules with @injected functions."""
    
    rule_id = "PINJ014"
    name = "Missing .pyi stub file"
    description = "Modules with @injected functions should have corresponding .pyi stub files"
    severity = Severity.WARNING
    category = "documentation"
    auto_fixable = False
    
    def check(self, context: RuleContext) -> List[Violation]:
        """Check if module with @injected functions has a .pyi stub file."""
        violations = []
        
        # Check if module has any @injected functions
        has_injected_functions = self._has_injected_functions(context.tree)
        
        if not has_injected_functions:
            return violations
        
        # Check configuration options
        min_injected_functions = self.config.get("min_injected_functions", 1)
        stub_search_paths = self.config.get("stub_search_paths", ["stubs", "typings"])
        ignore_patterns = self.config.get("ignore_patterns", ["**/tests/**", "**/migrations/**"])
        
        # Check if file matches ignore patterns
        path_str = str(context.file_path)
        
        # Always ignore temporary files (but not regular Python files in temp directories)
        file_name = context.file_path.name
        if (file_name.startswith("tmp") and len(file_name) > 10 and not file_name.endswith("_test.py")
            or path_str.startswith("/tmp/") and file_name.startswith("tmp")):
            return violations
            
        for pattern in ignore_patterns:
            # Check if any part of the path contains the pattern keywords
            if pattern == "**/tests/**" and "/tests/" in path_str:
                return violations
            elif pattern == "**/migrations/**" and "/migrations/" in path_str:
                return violations
            elif context.file_path.match(pattern):
                return violations
        
        # Count injected functions
        injected_count = self._count_injected_functions(context.tree)
        if injected_count < min_injected_functions:
            return violations
        
        # Check for stub file
        stub_path = context.file_path.with_suffix('.pyi')
        
        # Check in same directory first
        if stub_path.exists():
            return violations
        
        # Check in additional stub directories
        for stub_dir in stub_search_paths:
            alternative_stub = context.file_path.parent / stub_dir / context.file_path.with_suffix('.pyi').name
            if alternative_stub.exists():
                return violations
        
        # No stub file found, create violation
        violation = Violation(
            rule_id=self.rule_id,
            message=f"Module contains {injected_count} @injected function(s) but no .pyi stub file found",
            file_path=context.file_path,
            position=self._get_first_injected_position(context.tree),
            severity=self.get_severity(),
            suggestion=self._generate_suggestion(context, stub_path),
        )
        violations.append(violation)
        
        return violations
    
    def _has_injected_functions(self, tree: ast.AST) -> bool:
        """Check if module has any @injected functions."""
        
        class InjectedChecker(ast.NodeVisitor):
            def __init__(self):
                self.has_injected = False
            
            def visit_FunctionDef(self, node):
                if has_decorator(node, "injected"):
                    self.has_injected = True
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                if has_decorator(node, "injected"):
                    self.has_injected = True
                self.generic_visit(node)
        
        checker = InjectedChecker()
        checker.visit(tree)
        return checker.has_injected
    
    def _count_injected_functions(self, tree: ast.AST) -> int:
        """Count number of @injected functions in module."""
        
        class InjectedCounter(ast.NodeVisitor):
            def __init__(self):
                self.count = 0
            
            def visit_FunctionDef(self, node):
                if has_decorator(node, "injected"):
                    self.count += 1
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                if has_decorator(node, "injected"):
                    self.count += 1
                self.generic_visit(node)
        
        counter = InjectedCounter()
        counter.visit(tree)
        return counter.count
    
    def _get_first_injected_position(self, tree: ast.AST):
        """Get position of first @injected function in module."""
        from ..models import Position
        
        class FirstInjectedFinder(ast.NodeVisitor):
            def __init__(self):
                self.first_position = None
            
            def visit_FunctionDef(self, node):
                if self.first_position is None and has_decorator(node, "injected"):
                    self.first_position = Position(
                        line=node.lineno,
                        column=node.col_offset,
                        end_line=node.end_lineno,
                        end_column=node.end_col_offset,
                    )
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                if self.first_position is None and has_decorator(node, "injected"):
                    self.first_position = Position(
                        line=node.lineno,
                        column=node.col_offset,
                        end_line=node.end_lineno,
                        end_column=node.end_col_offset,
                    )
                self.generic_visit(node)
        
        finder = FirstInjectedFinder()
        finder.visit(tree)
        return finder.first_position or Position(line=1, column=0)
    
    def _generate_suggestion(self, context: RuleContext, stub_path: Path) -> str:
        """Generate suggestion for creating stub file."""
        # Collect @injected function signatures
        signatures = self._collect_injected_signatures(context.tree)
        
        suggestion_lines = [
            f"Create a stub file at: {stub_path}",
            "",
            "Example stub content:",
            "```python",
            "from typing import Any",
            "from pinjected import injected",
            "",
        ]
        
        for sig in signatures[:3]:  # Show first 3 as examples
            suggestion_lines.append(sig)
        
        if len(signatures) > 3:
            suggestion_lines.append(f"# ... and {len(signatures) - 3} more @injected functions")
        
        suggestion_lines.extend([
            "```",
            "",
            "Stub files improve IDE support and type checking for @injected functions.",
        ])
        
        return "\n".join(suggestion_lines)
    
    def _collect_injected_signatures(self, tree: ast.AST) -> List[str]:
        """Collect signatures of @injected functions for stub suggestion."""
        
        class SignatureCollector(ast.NodeVisitor):
            def __init__(self):
                self.signatures = []
            
            def visit_FunctionDef(self, node):
                if has_decorator(node, "injected"):
                    sig = self._build_signature(node, is_async=False)
                    self.signatures.append(sig)
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                if has_decorator(node, "injected"):
                    sig = self._build_signature(node, is_async=True)
                    self.signatures.append(sig)
                self.generic_visit(node)
            
            def _build_signature(self, node, is_async: bool) -> str:
                """Build a stub signature for a function."""
                parts = ["@injected"]
                
                # Function definition
                func_def = "async def" if is_async else "def"
                sig_line = f"{func_def} {node.name}("
                
                # Add parameters with type hints
                params = []
                for arg in node.args.posonlyargs:
                    params.append(f"{arg.arg}: Any")
                
                if node.args.posonlyargs:
                    params.append("/")
                
                for arg in node.args.args:
                    # Add type annotation if available, otherwise Any
                    if arg.annotation:
                        # For simplicity, we'll use Any in the suggestion
                        params.append(f"{arg.arg}: Any")
                    else:
                        params.append(f"{arg.arg}: Any")
                
                sig_line += ", ".join(params)
                sig_line += ") -> Any: ..."
                
                return "\n".join(parts) + "\n" + sig_line
        
        collector = SignatureCollector()
        collector.visit(tree)
        return collector.signatures