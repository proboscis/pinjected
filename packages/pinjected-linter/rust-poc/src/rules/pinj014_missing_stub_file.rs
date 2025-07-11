//! PINJ014: Missing .pyi stub file
//!
//! Modules with @injected functions should have corresponding .pyi stub files
//! for better IDE support and type checking.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::has_injected_decorator;
use rustpython_ast::{Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef, Arg, ArgWithDefault};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
struct InjectedFunctionInfo {
    name: String,
    is_async: bool,
    signature: String,
}

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

    /// Collect all @injected functions in the module
    fn collect_injected_functions(&self, ast: &Mod) -> Vec<InjectedFunctionInfo> {
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

    /// Format a single argument
    fn format_arg(&self, arg: &Arg) -> String {
        let mut result = arg.arg.to_string();
        if let Some(ann) = &arg.annotation {
            result.push_str(": ");
            result.push_str(&self.format_type_annotation(ann));
        }
        result
    }

    /// Format an argument with default value
    fn format_arg_with_default(&self, arg: &ArgWithDefault) -> String {
        let mut result = self.format_arg(&arg.def);
        if arg.default.is_some() {
            // For stub files, we don't show default values, just indicate it has one
            result.push_str(" = ...");
        }
        result
    }

    /// Format type annotation
    fn format_type_annotation(&self, expr: &Expr) -> String {
        match expr {
            Expr::Name(name) => name.id.to_string(),
            Expr::Subscript(sub) => {
                let base = self.format_type_annotation(&sub.value);
                let index = self.format_type_annotation(&sub.slice);
                format!("{}[{}]", base, index)
            }
            Expr::Attribute(attr) => {
                let value = self.format_type_annotation(&attr.value);
                format!("{}.{}", value, attr.attr)
            }
            Expr::BinOp(binop) => {
                // Handle union types (e.g., str | None)
                let left = self.format_type_annotation(&binop.left);
                let right = self.format_type_annotation(&binop.right);
                format!("{} | {}", left, right)
            }
            Expr::Constant(constant) => {
                match &constant.value {
                    rustpython_ast::Constant::None => "None".to_string(),
                    rustpython_ast::Constant::Str(s) => format!("'{}'", s),
                    _ => "Any".to_string(),
                }
            }
            _ => "Any".to_string(),
        }
    }

    /// Generate function signature for stub file
    fn generate_function_signature(&self, func: &StmtFunctionDef) -> String {
        let mut sig = String::new();
        
        // Add async if needed
        if func.name.starts_with("a_") {
            sig.push_str("async ");
        }
        
        sig.push_str("def ");
        sig.push_str(&func.name);
        sig.push('(');

        let args = &func.args;
        let mut all_args = Vec::new();

        // Position-only args
        for arg in &args.posonlyargs {
            all_args.push(self.format_arg_with_default(arg));
        }
        
        if !args.posonlyargs.is_empty() {
            all_args.push("/".to_string());
        }

        // Regular args
        for arg in &args.args {
            all_args.push(self.format_arg_with_default(arg));
        }

        // *args
        if let Some(vararg) = &args.vararg {
            all_args.push(format!("*{}", self.format_arg(vararg)));
        }

        // Keyword-only args
        for arg in &args.kwonlyargs {
            all_args.push(self.format_arg_with_default(arg));
        }

        // **kwargs
        if let Some(kwarg) = &args.kwarg {
            all_args.push(format!("**{}", self.format_arg(kwarg)));
        }

        sig.push_str(&all_args.join(", "));
        sig.push(')');

        // Return type
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str(&self.format_type_annotation(returns));
        }

        sig.push_str(": ...");
        sig
    }

    /// Generate async function signature for stub file
    fn generate_async_function_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let mut sig = String::new();
        
        sig.push_str("async def ");
        sig.push_str(&func.name);
        sig.push('(');

        let args = &func.args;
        let mut all_args = Vec::new();

        // Position-only args
        for arg in &args.posonlyargs {
            all_args.push(self.format_arg_with_default(arg));
        }
        
        if !args.posonlyargs.is_empty() {
            all_args.push("/".to_string());
        }

        // Regular args
        for arg in &args.args {
            all_args.push(self.format_arg_with_default(arg));
        }

        // *args
        if let Some(vararg) = &args.vararg {
            all_args.push(format!("*{}", self.format_arg(vararg)));
        }

        // Keyword-only args
        for arg in &args.kwonlyargs {
            all_args.push(self.format_arg_with_default(arg));
        }

        // **kwargs
        if let Some(kwarg) = &args.kwarg {
            all_args.push(format!("**{}", self.format_arg(kwarg)));
        }

        sig.push_str(&all_args.join(", "));
        sig.push(')');

        // Return type
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str(&self.format_type_annotation(returns));
        }

        sig.push_str(": ...");
        sig
    }

    fn collect_in_stmt(&self, stmt: &Stmt, functions: &mut Vec<InjectedFunctionInfo>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    let signature = self.generate_function_signature(func);
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
                    let signature = self.generate_async_function_signature(func);
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
                let alt_stub = parent
                    .join(stub_dir)
                    .join(path.file_name().unwrap())
                    .with_extension("pyi");
                if alt_stub.exists() {
                    return Some(alt_stub);
                }
            }
        }

        None
    }

    /// Generate the expected stub file content
    fn generate_stub_content(&self, functions: &[InjectedFunctionInfo]) -> String {
        let mut content = String::new();
        
        // Add imports
        content.push_str("from typing import Any\n");
        content.push_str("from pinjected import injected, IProxy\n");
        content.push_str("\n");
        
        // Add function signatures
        for func in functions {
            content.push_str("@injected\n");
            content.push_str(&func.signature);
            content.push('\n');
            content.push('\n');
        }
        
        content
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

        // This is a module-level rule - check if we're in the module-level context
        // (identified by a Pass statement used as a placeholder)
        match context.stmt {
            Stmt::Pass(_) => {
                // This is the module-level check, proceed
            }
            _ => {
                // This is a statement-level check, skip since we handle this at module level
                return violations;
            }
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

        // No stub file found - collect functions and create violation with expected content
        let injected_functions = self.collect_injected_functions(context.ast);
        let stub_file_path = Path::new(context.file_path).with_extension("pyi");
        let stub_content = self.generate_stub_content(&injected_functions);
        
        let message = format!(
            "Module contains {} @injected function(s) but no .pyi stub file found.\n\nExpected stub file: {}\n\nExpected content:\n{}",
            injected_count,
            stub_file_path.display(),
            stub_content
        );
        
        violations.push(Violation {
            rule_id: self.rule_id().to_string(),
            message,
            offset: 0, // Report at start of file
            file_path: context.file_path.to_string(),
            severity: Severity::Warning,
        });

        violations
    }
}
