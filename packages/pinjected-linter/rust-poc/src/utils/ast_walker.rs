//! AST walking utilities for collecting information across modules

use rustpython_ast::{Mod, Stmt};
use std::collections::HashSet;
use crate::utils::pinjected_patterns::{has_instance_decorator, has_instance_decorator_async, has_instance_callable_decorator, has_instance_callable_decorator_async};

/// Collect all @instance function names in a module
pub fn collect_instance_functions(ast: &Mod) -> HashSet<String> {
    let mut instance_functions = HashSet::new();
    
    match ast {
        Mod::Module(module) => {
            for stmt in &module.body {
                collect_instance_functions_from_stmt(stmt, &mut instance_functions);
            }
        }
        _ => {}
    }
    
    instance_functions
}

fn collect_instance_functions_from_stmt(stmt: &Stmt, instance_functions: &mut HashSet<String>) {
    match stmt {
        Stmt::FunctionDef(func) => {
            if has_instance_decorator(func) {
                instance_functions.insert(func.name.to_string());
            }
            // Don't recurse into function bodies - we only want module-level functions
        }
        Stmt::AsyncFunctionDef(func) => {
            if has_instance_decorator_async(func) {
                instance_functions.insert(func.name.to_string());
            }
            // Don't recurse into function bodies - we only want module-level functions
        }
        Stmt::ClassDef(_class) => {
            // Could check for instance methods in classes if needed
            // For now, skip class methods
        }
        _ => {}
    }
}

/// Collect all @instance(callable=True) function names in a module
pub fn collect_instance_callable_functions(ast: &Mod) -> HashSet<String> {
    let mut instance_callable_functions = HashSet::new();
    
    match ast {
        Mod::Module(module) => {
            for stmt in &module.body {
                collect_instance_callable_functions_from_stmt(stmt, &mut instance_callable_functions);
            }
        }
        _ => {}
    }
    
    instance_callable_functions
}

fn collect_instance_callable_functions_from_stmt(stmt: &Stmt, instance_callable_functions: &mut HashSet<String>) {
    match stmt {
        Stmt::FunctionDef(func) => {
            if has_instance_callable_decorator(func) {
                instance_callable_functions.insert(func.name.to_string());
            }
            // Don't recurse into function bodies - we only want module-level functions
        }
        Stmt::AsyncFunctionDef(func) => {
            if has_instance_callable_decorator_async(func) {
                instance_callable_functions.insert(func.name.to_string());
            }
            // Don't recurse into function bodies - we only want module-level functions
        }
        Stmt::ClassDef(_class) => {
            // Could check for instance(callable=True) methods in classes if needed
            // For now, skip class methods
        }
        _ => {}
    }
}