//! AST node formatting for stub files

use rustpython_ast::{Constant, Expr, Stmt, StmtAsyncFunctionDef, StmtClassDef, StmtFunctionDef};
use super::signature_formatter::SignatureFormatter;
use crate::utils::pinjected_patterns::has_injected_decorator;
use super::injected_function_analyzer::has_injected_decorator_async;

pub struct AstFormatter {
    sig_formatter: SignatureFormatter,
}

impl AstFormatter {
    pub fn new() -> Self {
        Self {
            sig_formatter: SignatureFormatter::new(),
        }
    }

    pub fn format_import_stmt(&self, stmt: &Stmt) -> String {
        if let Stmt::Import(import) = stmt {
            let names: Vec<String> = import.names.iter()
                .map(|alias| {
                    if let Some(asname) = &alias.asname {
                        format!("{} as {}", alias.name, asname)
                    } else {
                        alias.name.to_string()
                    }
                })
                .collect();
            format!("import {}", names.join(", "))
        } else {
            String::new()
        }
    }

    pub fn format_import_from_stmt(&self, stmt: &Stmt) -> String {
        if let Stmt::ImportFrom(import_from) = stmt {
            let module = import_from.module.as_ref().map(|m| m.as_str()).unwrap_or("");
            let names: Vec<String> = import_from.names.iter()
                .map(|alias| {
                    if let Some(asname) = &alias.asname {
                        format!("{} as {}", alias.name, asname)
                    } else {
                        alias.name.to_string()
                    }
                })
                .collect();
            format!("from {} import {}", module, names.join(", "))
        } else {
            String::new()
        }
    }

    pub fn format_function_def(&self, func: &StmtFunctionDef) -> String {
        // Format the function with its decorators
        let mut lines = Vec::new();
        for dec in &func.decorator_list {
            lines.push(format!("@{}", self.format_decorator(dec)));
        }
        
        // Use appropriate signature generation based on whether function is @injected
        if has_injected_decorator(func) {
            lines.push(self.sig_formatter.generate_function_signature(func));
        } else {
            lines.push(self.sig_formatter.generate_non_injected_function_signature(func));
        }
        
        lines.join("\n")
    }

    pub fn format_async_function_def(&self, func: &StmtAsyncFunctionDef) -> String {
        // Format the async function with its decorators
        let mut lines = Vec::new();
        for dec in &func.decorator_list {
            lines.push(format!("@{}", self.format_decorator(dec)));
        }
        
        // Use appropriate signature generation based on whether function is @injected
        if has_injected_decorator_async(func) {
            lines.push(self.sig_formatter.generate_async_function_signature(func));
        } else {
            lines.push(self.sig_formatter.generate_non_injected_async_function_signature(func));
        }
        
        lines.join("\n")
    }

    pub fn format_decorator(&self, expr: &Expr) -> String {
        match expr {
            Expr::Name(name) => name.id.to_string(),
            Expr::Attribute(attr) => {
                let value = self.sig_formatter.format_type_annotation(&attr.value);
                format!("{}.{}", value, attr.attr)
            }
            _ => "decorator".to_string(),
        }
    }

    // CRITICAL FIX: Properly format class definitions instead of replacing with ellipsis
    pub fn format_class_def(&self, class: &StmtClassDef) -> String {
        let mut result = String::new();
        
        // Add decorators
        for decorator in &class.decorator_list {
            result.push_str(&format!("@{}\n", self.format_decorator(decorator)));
        }
        
        // Add class definition with base classes
        result.push_str(&format!("class {}", class.name));
        
        // Add base classes if any
        if !class.bases.is_empty() {
            result.push('(');
            let bases: Vec<String> = class.bases.iter()
                .map(|base| self.sig_formatter.format_type_annotation(base))
                .collect();
            result.push_str(&bases.join(", "));
            result.push(')');
        }
        
        result.push_str(":\n");
        
        // Format class body
        if class.body.is_empty() {
            result.push_str("    ...");
        } else {
            let mut has_content = false;
            for stmt in &class.body {
                match stmt {
                    // Handle ellipsis
                    Stmt::Expr(expr_stmt) => {
                        if let Expr::Constant(c) = expr_stmt.value.as_ref() {
                            if matches!(&c.value, Constant::Ellipsis) {
                                // Skip processing further if this is the only statement
                                if class.body.len() == 1 {
                                    result.push_str("    ...");
                                    has_content = true;
                                    break;
                                }
                                // Otherwise continue to process it normally
                            }
                        }
                    }
                    _ => {}
                }
                
                // Format each statement in the class body
                let stmt_str_opt = match stmt {
                    Stmt::FunctionDef(func) => {
                        let mut func_str = self.format_function_def(func);
                        // Indent method definitions
                        func_str = func_str.lines()
                            .map(|line| if line.is_empty() { line.to_string() } else { format!("    {}", line) })
                            .collect::<Vec<_>>()
                            .join("\n");
                        Some(func_str)
                    }
                    Stmt::AsyncFunctionDef(func) => {
                        let mut func_str = self.format_async_function_def(func);
                        // Indent method definitions
                        func_str = func_str.lines()
                            .map(|line| if line.is_empty() { line.to_string() } else { format!("    {}", line) })
                            .collect::<Vec<_>>()
                            .join("\n");
                        Some(func_str)
                    }
                    Stmt::AnnAssign(ann_assign) => {
                        if let Expr::Name(name) = ann_assign.target.as_ref() {
                            if let Some(value) = &ann_assign.value {
                                if let Expr::Constant(c) = value.as_ref() {
                                    if matches!(&c.value, Constant::Ellipsis) {
                                        Some(format!("    {}: {}", name.id, self.sig_formatter.format_type_annotation(&ann_assign.annotation)))
                                    } else {
                                        Some(format!("    {}: {} = ...", name.id, self.sig_formatter.format_type_annotation(&ann_assign.annotation)))
                                    }
                                } else {
                                    Some(format!("    {}: {} = ...", name.id, self.sig_formatter.format_type_annotation(&ann_assign.annotation)))
                                }
                            } else {
                                Some(format!("    {}: {}", name.id, self.sig_formatter.format_type_annotation(&ann_assign.annotation)))
                            }
                        } else {
                            None  // Skip non-name annotations
                        }
                    }
                    Stmt::Assign(assign) => {
                        if let Some(target) = assign.targets.first() {
                            if let Expr::Name(name) = target {
                                Some(format!("    {} = ...", name.id))
                            } else {
                                None  // Skip non-name assignments
                            }
                        } else {
                            None
                        }
                    }
                    Stmt::Expr(expr_stmt) => {
                        if let Expr::Constant(c) = expr_stmt.value.as_ref() {
                            if matches!(&c.value, Constant::Ellipsis) {
                                Some("    ...".to_string())
                            } else {
                                None  // Skip other constant expressions
                            }
                        } else {
                            None  // Skip other expressions
                        }
                    }
                    _ => None,  // Skip other statements
                };
                
                if let Some(stmt_str) = stmt_str_opt {
                    has_content = true;
                    result.push_str(&stmt_str);
                    result.push('\n');
                }
            }
            
            if !has_content {
                result.push_str("    ...");
            } else {
                // Remove trailing newline if present
                if result.ends_with('\n') {
                    result.pop();
                }
            }
        }
        
        result
    }

    pub fn format_other_stmt(&self, stmt: &Stmt) -> String {
        // This is a simplified version - ideally we'd preserve exact formatting
        match stmt {
            Stmt::ClassDef(class) => {
                // CRITICAL: Use the proper format_class_def method
                self.format_class_def(class)
            }
            Stmt::Assign(assign) => {
                if let Some(target) = assign.targets.first() {
                    if let Expr::Name(name) = target {
                        format!("{} = ...", name.id)
                    } else {
                        "# assignment".to_string()
                    }
                } else {
                    "# assignment".to_string()
                }
            }
            Stmt::AnnAssign(annassign) => {
                if let Expr::Name(name) = &*annassign.target {
                    let type_ann = self.sig_formatter.format_type_annotation(&annassign.annotation);
                    if annassign.value.is_some() {
                        format!("{}: {} = ...", name.id, type_ann)
                    } else {
                        format!("{}: {}", name.id, type_ann)
                    }
                } else {
                    "# annotated assignment".to_string()
                }
            }
            Stmt::FunctionDef(func) => {
                // Non-overload functions should be preserved
                self.format_function_def(func)
            }
            Stmt::AsyncFunctionDef(func) => {
                // Non-overload async functions should be preserved
                self.format_async_function_def(func)
            }
            _ => "# preserved content".to_string(),
        }
    }
}