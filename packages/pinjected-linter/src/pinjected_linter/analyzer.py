"""Main analyzer for Pinjected linter."""

import ast
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import RuleContext, Violation
from .rules import RULES_BY_ID
from .utils.symbol_table import SymbolTable


class SymbolTableBuilder(ast.NodeVisitor):
    """Build symbol table by visiting AST nodes."""
    
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self.scope_stack = []
    
    def visit_FunctionDef(self, node):
        """Visit function definition."""
        if not self.scope_stack:  # Top-level function
            self.symbol_table.add_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition."""
        if not self.scope_stack:  # Top-level function
            self.symbol_table.add_function(node)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Visit class definition."""
        if not self.scope_stack:  # Top-level class
            self.symbol_table.add_class(node)
        self.scope_stack.append(node)
        self.generic_visit(node)
        self.scope_stack.pop()
    
    def visit_Import(self, node):
        """Visit import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.symbol_table.add_import(name, alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Visit from-import statement."""
        if node.module:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                self.symbol_table.add_import(name, f"{node.module}.{alias.name}")
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Visit assignment statement."""
        if not self.scope_stack:  # Global assignment
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.symbol_table.add_global_var(target.id, node.value)
        self.generic_visit(node)


class PinjectedAnalyzer:
    """Main analyzer for Pinjected code."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parallel: bool = True,
    ):
        """Initialize analyzer.
        
        Args:
            config: Configuration dictionary
            parallel: Whether to use parallel processing
        """
        self.config = config or {}
        self.parallel = parallel and multiprocessing.cpu_count() > 1
        self.enabled_rules = self._get_enabled_rules()
    
    def analyze_file(self, file_path: Path) -> List[Violation]:
        """Analyze a single Python file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of violations found
        """
        try:
            source = file_path.read_text()
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            # Skip files with syntax errors or encoding issues
            return []
        
        # Build symbol table
        symbol_table = SymbolTable()
        builder = SymbolTableBuilder(symbol_table)
        builder.visit(tree)
        
        # Create rule context
        context = RuleContext(
            file_path=file_path,
            source=source,
            tree=tree,
            symbol_table=symbol_table,
            config=self.config,
        )
        
        # Run enabled rules
        violations = []
        for rule_class in self.enabled_rules:
            rule_config = self._get_rule_config(rule_class.rule_id)
            rule = rule_class(config=rule_config)
            
            if rule.is_enabled():
                try:
                    rule_violations = rule.check(context)
                    violations.extend(rule_violations)
                except Exception as e:
                    # Log error but continue with other rules
                    print(f"Error in rule {rule.rule_id}: {e}")
        
        return violations
    
    def analyze_files(self, file_paths: List[Path]) -> List[Violation]:
        """Analyze multiple Python files.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            List of all violations found
        """
        if self.parallel and len(file_paths) > 1:
            return self._analyze_files_parallel(file_paths)
        else:
            violations = []
            for file_path in file_paths:
                violations.extend(self.analyze_file(file_path))
            return violations
    
    def _analyze_files_parallel(self, file_paths: List[Path]) -> List[Violation]:
        """Analyze files in parallel."""
        violations = []
        
        with ProcessPoolExecutor() as executor:
            future_to_file = {
                executor.submit(self.analyze_file, file_path): file_path
                for file_path in file_paths
            }
            
            for future in as_completed(future_to_file):
                try:
                    file_violations = future.result()
                    violations.extend(file_violations)
                except Exception as e:
                    file_path = future_to_file[future]
                    print(f"Error analyzing {file_path}: {e}")
        
        return violations
    
    def _get_enabled_rules(self) -> List[type]:
        """Get list of enabled rule classes."""
        # Start with all rules
        enabled_rules = list(RULES_BY_ID.values())
        
        # Apply enable/disable from config
        if "disable" in self.config:
            disabled_ids = set(self.config["disable"])
            enabled_rules = [r for r in enabled_rules if r.rule_id not in disabled_ids]
        
        if "enable" in self.config:
            enabled_ids = set(self.config["enable"])
            enabled_rules = [r for r in enabled_rules if r.rule_id in enabled_ids]
        
        return enabled_rules
    
    def _get_rule_config(self, rule_id: str) -> Dict[str, Any]:
        """Get configuration for a specific rule."""
        rule_config = {}
        
        # Global rule config
        if "rules" in self.config and rule_id in self.config["rules"]:
            rule_config.update(self.config["rules"][rule_id])
        
        # Severity override
        if "severity" in self.config and rule_id in self.config["severity"]:
            rule_config["severity"] = self.config["severity"][rule_id]
        
        return rule_config