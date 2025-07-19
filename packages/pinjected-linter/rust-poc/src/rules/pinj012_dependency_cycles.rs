//! PINJ012: Dependency cycles detection
//!
//! Circular dependencies between @injected functions will cause runtime errors
//! when Pinjected attempts to resolve the dependency graph. This rule detects
//! these cycles at development time.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Mod, Stmt};
use std::collections::{HashMap, HashSet};

pub struct DependencyCyclesRule;

impl DependencyCyclesRule {
    pub fn new() -> Self {
        Self
    }

    /// Build dependency graph from all @injected functions
    fn build_dependency_graph(ast: &Mod) -> HashMap<String, HashSet<String>> {
        let mut graph = HashMap::new();

        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    Self::collect_from_stmt(stmt, &mut graph);
                }
            }
            _ => {}
        }

        graph
    }

    fn collect_from_stmt(stmt: &Stmt, graph: &mut HashMap<String, HashSet<String>>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    let func_name = func.name.to_string();
                    let mut dependencies = HashSet::new();

                    // Extract dependencies (positional-only args before /)
                    for arg in &func.args.posonlyargs {
                        dependencies.insert(arg.def.arg.to_string());
                    }

                    graph.insert(func_name, dependencies);
                }
                // Check nested functions
                for stmt in &func.body {
                    Self::collect_from_stmt(stmt, graph);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    let func_name = func.name.to_string();
                    let mut dependencies = HashSet::new();

                    // Extract dependencies (positional-only args before /)
                    for arg in &func.args.posonlyargs {
                        dependencies.insert(arg.def.arg.to_string());
                    }

                    graph.insert(func_name, dependencies);
                }
                // Check nested functions
                for stmt in &func.body {
                    Self::collect_from_stmt(stmt, graph);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    Self::collect_from_stmt(stmt, graph);
                }
            }
            _ => {}
        }
    }

    /// Find all cycles in the dependency graph using DFS
    fn find_cycles(graph: &HashMap<String, HashSet<String>>) -> Vec<Vec<String>> {
        let mut cycles = Vec::new();
        let mut visited = HashSet::new();
        let mut rec_stack = HashSet::new();
        let mut path = Vec::new();

        // DFS helper function
        fn dfs(
            node: &str,
            graph: &HashMap<String, HashSet<String>>,
            visited: &mut HashSet<String>,
            rec_stack: &mut HashSet<String>,
            path: &mut Vec<String>,
            cycles: &mut Vec<Vec<String>>,
        ) {
            if rec_stack.contains(node) {
                // Found a cycle - extract it from the current path
                if let Some(cycle_start) = path.iter().position(|n| n == node) {
                    let mut cycle: Vec<String> = path[cycle_start..].to_vec();
                    cycle.push(node.to_string());
                    cycles.push(cycle);
                }
                return;
            }

            if visited.contains(node) {
                return;
            }

            visited.insert(node.to_string());
            rec_stack.insert(node.to_string());
            path.push(node.to_string());

            // Visit all dependencies
            if let Some(deps) = graph.get(node) {
                for dep in deps {
                    if graph.contains_key(dep) {
                        // Only visit nodes that exist
                        dfs(dep, graph, visited, rec_stack, path, cycles);
                    }
                }
            }

            path.pop();
            rec_stack.remove(node);
        }

        // Start DFS from all nodes
        for node in graph.keys() {
            if !visited.contains(node) {
                dfs(
                    node,
                    graph,
                    &mut visited,
                    &mut rec_stack,
                    &mut path,
                    &mut cycles,
                );
            }
        }

        // Remove duplicate cycles (same cycle found from different starting points)
        let mut unique_cycles = Vec::new();
        let mut seen_cycles = HashSet::new();

        for cycle in cycles {
            if cycle.is_empty() {
                continue;
            }

            // Normalize cycle to start from lexicographically smallest node
            let min_node = cycle.iter().min().unwrap();
            let min_idx = cycle.iter().position(|n| n == min_node).unwrap();

            let mut normalized = Vec::new();
            for i in 0..cycle.len() - 1 {
                // Exclude the duplicate last element
                normalized.push(cycle[(min_idx + i) % (cycle.len() - 1)].clone());
            }

            let normalized_key = normalized.join("->");
            if !seen_cycles.contains(&normalized_key) {
                seen_cycles.insert(normalized_key);
                unique_cycles.push(normalized);
            }
        }

        unique_cycles
    }
}

impl LintRule for DependencyCyclesRule {
    fn rule_id(&self) -> &str {
        "PINJ012"
    }

    fn description(&self) -> &str {
        "Detects circular dependencies between @injected functions"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Build the complete dependency graph
        let graph = Self::build_dependency_graph(context.ast);

        // Find all cycles
        let cycles = Self::find_cycles(&graph);

        // Report cycles
        for cycle in cycles {
            if cycle.is_empty() {
                continue;
            }

            // Format cycle for display
            let cycle_str = cycle.join(" → ");

            // Find the AST node for the first function in the cycle to attach the error
            let first_node = &cycle[0];

            // Search for the function node in the current statement
            match context.stmt {
                Stmt::FunctionDef(func) => {
                    if func.name.as_str() == first_node {
                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message: format!(
                                "Circular dependency detected:\n  {} → {}",
                                cycle_str,
                                cycle[0] // Complete the cycle
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }
                }
                Stmt::AsyncFunctionDef(func) => {
                    if func.name.as_str() == first_node {
                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message: format!(
                                "Circular dependency detected:\n  {} → {}",
                                cycle_str,
                                cycle[0] // Complete the cycle
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }
                }
                _ => {}
            }
        }

        violations
    }
}
