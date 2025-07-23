//! Analysis of @injected functions in Python modules

use crate::utils::pinjected_patterns::has_injected_decorator;
use rustpython_ast::{Expr, Mod, Stmt, StmtAsyncFunctionDef};
use super::signature_formatter::SignatureFormatter;

#[derive(Debug, Clone)]
pub struct InjectedFunctionInfo {
    pub name: String,
    pub is_async: bool,
    pub signature: String,
}

pub struct InjectedFunctionAnalyzer {
    formatter: SignatureFormatter,
}

impl InjectedFunctionAnalyzer {
    pub fn new() -> Self {
        Self {
            formatter: SignatureFormatter::new(),
        }
    }

    /// Count the number of @injected functions in the module
    pub fn count_injected_functions(&self, ast: &Mod) -> usize {
        let mut count = 0;

        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    count += self.count_in_stmt(stmt);
                }
            }
            _ => {}
        }

        count
    }

    /// Collect all @injected functions in the module
    pub fn collect_injected_functions(&self, ast: &Mod) -> Vec<InjectedFunctionInfo> {
        let mut functions = Vec::new();

        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.collect_in_stmt(stmt, &mut functions);
                }
            }
            _ => {}
        }

        functions
    }

    fn collect_in_stmt(&self, stmt: &Stmt, functions: &mut Vec<InjectedFunctionInfo>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    let signature = self.formatter.generate_function_signature(func);
                    functions.push(InjectedFunctionInfo {
                        name: func.name.to_string(),
                        is_async: false,
                        signature,
                    });
                }
                // Check nested functions
                for stmt in &func.body {
                    self.collect_in_stmt(stmt, functions);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    let signature = self.formatter.generate_async_function_signature(func);
                    functions.push(InjectedFunctionInfo {
                        name: func.name.to_string(),
                        is_async: true,
                        signature,
                    });
                }
                // Check nested functions
                for stmt in &func.body {
                    self.collect_in_stmt(stmt, functions);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.collect_in_stmt(stmt, functions);
                }
            }
            _ => {}
        }
    }

    fn count_in_stmt(&self, stmt: &Stmt) -> usize {
        let mut count = 0;

        match stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    count += 1;
                }
                // Check nested functions
                for stmt in &func.body {
                    count += self.count_in_stmt(stmt);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    count += 1;
                }
                // Check nested functions
                for stmt in &func.body {
                    count += self.count_in_stmt(stmt);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    count += self.count_in_stmt(stmt);
                }
            }
            _ => {}
        }

        count
    }
}

// Helper for async functions
pub fn has_injected_decorator_async(func: &StmtAsyncFunctionDef) -> bool {
    for dec in &func.decorator_list {
        if let Expr::Name(name) = dec {
            if name.id.as_str() == "injected" {
                return true;
            }
        } else if let Expr::Attribute(attr) = dec {
            if attr.attr.as_str() == "injected" {
                return true;
            }
        }
    }
    false
}