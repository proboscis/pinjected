"""PINJ012: Dependency cycles detection rule."""

import ast
from typing import Dict, List, Set

from ..models import RuleContext, Severity, Violation
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class DependencyGraph:
    """Graph structure to track and detect dependency cycles."""
    
    def __init__(self):
        self.nodes: Dict[str, Set[str]] = {}  # node -> set of dependencies
        self.node_locations: Dict[str, ast.AST] = {}  # node -> AST node for error reporting
    
    def add_node(self, name: str, dependencies: Set[str], location: ast.AST):
        """Add a node with its dependencies."""
        self.nodes[name] = dependencies
        self.node_locations[name] = location
    
    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the dependency graph using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> None:
            if node in rec_stack:
                # Found a cycle - extract it from the current path
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # Visit all dependencies
            if node in self.nodes:
                for dep in self.nodes[node]:
                    if dep in self.nodes:  # Only visit nodes that exist
                        dfs(dep)
            
            path.pop()
            rec_stack.remove(node)
        
        # Start DFS from all nodes
        for node in self.nodes:
            if node not in visited:
                dfs(node)
        
        # Remove duplicate cycles (same cycle found from different starting points)
        unique_cycles = []
        seen_cycles = set()
        
        for cycle in cycles:
            # Normalize cycle to start from lexicographically smallest node
            min_idx = cycle.index(min(cycle))
            normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
            
            if normalized not in seen_cycles:
                seen_cycles.add(normalized)
                unique_cycles.append(list(normalized))
        
        return unique_cycles


class PINJ012Visitor(BaseNodeVisitor):
    """Visitor for detecting dependency cycles in @injected functions."""
    
    def __init__(self, rule, context):
        super().__init__(rule, context)
        self.dependency_graph = DependencyGraph()
        self.current_function = None
    
    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def _check_function(self, node):
        """Extract dependencies from @injected functions."""
        if not has_decorator(node, "injected"):
            return
        
        # Get function name
        func_name = node.name
        
        # Extract dependencies (positional-only args before /)
        dependencies = set()
        
        if node.args.posonlyargs:
            # Has positional-only args (dependencies before /)
            for arg in node.args.posonlyargs:
                dep_name = arg.arg
                dependencies.add(dep_name)
        
        # Add to dependency graph
        self.dependency_graph.add_node(func_name, dependencies, node)
    
    def finalize(self):
        """Called after visiting all nodes to detect cycles."""
        cycles = self.dependency_graph.find_cycles()
        
        for cycle in cycles:
            # Format cycle for display
            cycle_str = " → ".join(cycle)
            
            # Find the first node in the cycle to attach the error to
            first_node = cycle[0]
            if first_node in self.dependency_graph.node_locations:
                node = self.dependency_graph.node_locations[first_node]
                
                self.add_violation(
                    node,
                    f"Circular dependency detected:\n  {cycle_str}",
                    suggestion="Refactor to eliminate the circular dependency. "
                              "Consider extracting shared functionality, using events/callbacks, "
                              "or restructuring the dependency hierarchy."
                )


class PINJ012DependencyCycles(ASTRuleBase):
    """Rule for detecting circular dependencies in @injected functions.
    
    Circular dependencies between @injected functions will cause runtime errors
    when Pinjected attempts to resolve the dependency graph. This rule detects
    these cycles at development time.
    
    Examples:
        Bad:
            @injected
            def service_a(service_b, /):
                return service_b()
            
            @injected
            def service_b(service_a, /):  # Creates cycle: A → B → A
                return service_a()
        
        Good:
            @injected
            def service_a(shared_service, /):
                return shared_service()
            
            @injected
            def service_b(shared_service, /):
                return shared_service()
    """
    
    rule_id = "PINJ012"
    name = "Dependency cycles detection"
    description = "Detects circular dependencies between @injected functions"
    severity = Severity.ERROR
    category = "dependency"
    auto_fixable = False  # Cycles require architectural changes
    
    def check(self, context: RuleContext) -> List[Violation]:
        """Check for violations by visiting AST nodes and detecting cycles."""
        visitor = self.get_visitor(context)
        visitor.visit(context.tree)
        visitor.finalize()  # Call finalize to detect cycles after building the graph
        return visitor.violations
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ012Visitor(self, context)