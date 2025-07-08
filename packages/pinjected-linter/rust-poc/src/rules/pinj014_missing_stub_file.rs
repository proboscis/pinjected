//! PINJ014: Missing .pyi stub file
//! 
//! Modules with @injected functions should have corresponding .pyi stub files
//! for better IDE support and type checking.

use rustpython_ast::{Mod, Stmt, StmtAsyncFunctionDef, Expr};
use std::path::{Path, PathBuf};
use crate::models::{Violation, RuleContext, Severity};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::has_injected_decorator;

pub struct MissingStubFileRule {
    min_injected_functions: usize,
    stub_search_paths: Vec<String>,
    ignore_patterns: Vec<String>,
}

impl MissingStubFileRule {
    pub fn new() -> Self {
        Self {
            min_injected_functions: 1,
            stub_search_paths: vec!["stubs".to_string(), "typings".to_string()],
            ignore_patterns: vec!["**/tests/**".to_string(), "**/migrations/**".to_string()],
        }
    }
    
    /// Count the number of @injected functions in the module
    fn count_injected_functions(&self, ast: &Mod) -> usize {
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
    
    /// Check if the file path matches any ignore patterns
    fn should_ignore(&self, file_path: &str) -> bool {
        // Check ignore patterns
        for pattern in &self.ignore_patterns {
            if pattern == "**/tests/**" && file_path.contains("/tests/") {
                return true;
            }
            if pattern == "**/migrations/**" && file_path.contains("/migrations/") {
                return true;
            }
        }
        
        // Always ignore temporary files
        if let Some(file_name) = Path::new(file_path).file_name() {
            let name = file_name.to_str().unwrap_or("");
            if name.starts_with("tmp") && name.len() > 10 {
                return true;
            }
        }
        
        if file_path.starts_with("/tmp/") {
            return true;
        }
        
        false
    }
    
    /// Look for stub file in various locations
    fn find_stub_file(&self, file_path: &str) -> Option<PathBuf> {
        let path = Path::new(file_path);
        
        // Check same directory first
        let stub_path = path.with_extension("pyi");
        if stub_path.exists() {
            return Some(stub_path);
        }
        
        // Check alternative directories
        if let Some(parent) = path.parent() {
            for stub_dir in &self.stub_search_paths {
                let alt_stub = parent.join(stub_dir).join(path.file_name().unwrap()).with_extension("pyi");
                if alt_stub.exists() {
                    return Some(alt_stub);
                }
            }
        }
        
        None
    }
}

// Helper for async functions
fn has_injected_decorator_async(func: &StmtAsyncFunctionDef) -> bool {
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

impl LintRule for MissingStubFileRule {
    fn rule_id(&self) -> &str {
        "PINJ014"
    }
    
    fn description(&self) -> &str {
        "Modules with @injected functions should have corresponding .pyi stub files"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        // This is a module-level rule, only check on the first statement
        // to avoid duplicate reports
        match context.ast {
            Mod::Module(module) => {
                if !module.body.is_empty() && !std::ptr::eq(context.stmt, &module.body[0]) {
                    // Not the first statement, skip to avoid duplicates
                    return violations;
                }
            }
            _ => return violations,
        }
        
        // Count @injected functions
        let injected_count = self.count_injected_functions(context.ast);
        
        // No @injected functions, no violation
        if injected_count == 0 {
            return violations;
        }
        
        // Check minimum threshold
        if injected_count < self.min_injected_functions {
            return violations;
        }
        
        // Check if file should be ignored
        if self.should_ignore(context.file_path) {
            return violations;
        }
        
        // Look for stub file
        if self.find_stub_file(context.file_path).is_some() {
            // Stub file exists, no violation
            return violations;
        }
        
        // No stub file found - create violation
        violations.push(Violation {
            rule_id: self.rule_id().to_string(),
            message: format!(
                "Module contains {} @injected function(s) but no .pyi stub file found",
                injected_count
            ),
            offset: 0, // Report at start of file
            file_path: context.file_path.to_string(),
            severity: Severity::Warning,
        });
        
        violations
    }
}