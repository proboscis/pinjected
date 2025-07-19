//! PINJ014: Missing .pyi stub file
//!
//! Modules with @injected functions should have corresponding .pyi stub files
//! for better IDE support and type checking.

use crate::config::{find_config_pyproject_toml, load_config};
use crate::models::{Fix, RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::has_injected_decorator;
use rustpython_ast::{Arg, ArgWithDefault, Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
use rustpython_parser::{parse, Mode};
use std::collections::HashMap;
use std::fs;
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
    
    pub fn with_config(config: Option<&crate::config::RuleConfig>) -> Self {
        match config {
            Some(cfg) => Self {
                min_injected_functions: cfg.min_injected_functions.unwrap_or(1),
                stub_search_paths: cfg.stub_search_paths.clone()
                    .unwrap_or_else(|| vec!["stubs".to_string(), "typings".to_string()]),
                ignore_patterns: cfg.ignore_patterns.clone()
                    .unwrap_or_else(|| vec!["**/tests/**".to_string(), "**/migrations/**".to_string()]),
            },
            None => Self::new(),
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
            Expr::Constant(constant) => match &constant.value {
                rustpython_ast::Constant::None => "None".to_string(),
                rustpython_ast::Constant::Str(s) => format!("'{}'", s),
                _ => "Any".to_string(),
            },
            _ => "Any".to_string(),
        }
    }

    /// Generate function signature for stub file (only runtime args after /)
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
        let mut runtime_args = Vec::new();

        // Find if there are position-only args (which end with /)
        let has_posonly = !args.posonlyargs.is_empty();
        
        // For @injected functions, we only want args after the /
        // Position-only args are the injected dependencies
        // Regular args after the / are runtime arguments
        
        if has_posonly {
            // Skip position-only args (they are injected dependencies)
            // But include regular args (they are runtime args after /)
            
            // Regular args (these come after the /)
            for arg in &args.args {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // *args
            if let Some(vararg) = &args.vararg {
                runtime_args.push(format!("*{}", self.format_arg(vararg)));
            } else if !args.kwonlyargs.is_empty() && args.args.is_empty() {
                // If no *args but we have keyword-only args, add *
                runtime_args.push("*".to_string());
            }

            // Keyword-only args
            for arg in &args.kwonlyargs {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // **kwargs
            if let Some(kwarg) = &args.kwarg {
                runtime_args.push(format!("**{}", self.format_arg(kwarg)));
            }
        } else {
            // No position-only separator, include all args
            // This is for functions without explicit / separator
            
            // Regular args
            for arg in &args.args {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // *args
            if let Some(vararg) = &args.vararg {
                runtime_args.push(format!("*{}", self.format_arg(vararg)));
            } else if !args.kwonlyargs.is_empty() && args.args.is_empty() {
                // If no *args but we have keyword-only args, add *
                runtime_args.push("*".to_string());
            }

            // Keyword-only args
            for arg in &args.kwonlyargs {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // **kwargs
            if let Some(kwarg) = &args.kwarg {
                runtime_args.push(format!("**{}", self.format_arg(kwarg)));
            }
        }

        sig.push_str(&runtime_args.join(", "));
        sig.push(')');

        // Return type - transform to IProxy[T]
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str("IProxy[");
            sig.push_str(&self.format_type_annotation(returns));
            sig.push(']');
        }

        sig.push_str(": ...");
        sig
    }

    /// Generate async function signature for stub file (only runtime args after /)
    fn generate_async_function_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let mut sig = String::new();

        sig.push_str("async def ");
        sig.push_str(&func.name);
        sig.push('(');

        let args = &func.args;
        let mut runtime_args = Vec::new();

        // Find if there are position-only args (which end with /)
        let has_posonly = !args.posonlyargs.is_empty();
        
        // For @injected functions, we only want args after the /
        // Position-only args are the injected dependencies
        // Regular args after the / are runtime arguments
        
        if has_posonly {
            // Skip position-only args (they are injected dependencies)
            // But include regular args (they are runtime args after /)
            
            // Regular args (these come after the /)
            for arg in &args.args {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // *args
            if let Some(vararg) = &args.vararg {
                runtime_args.push(format!("*{}", self.format_arg(vararg)));
            } else if !args.kwonlyargs.is_empty() && args.args.is_empty() {
                // If no *args but we have keyword-only args, add *
                runtime_args.push("*".to_string());
            }

            // Keyword-only args
            for arg in &args.kwonlyargs {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // **kwargs
            if let Some(kwarg) = &args.kwarg {
                runtime_args.push(format!("**{}", self.format_arg(kwarg)));
            }
        } else {
            // No position-only separator, include all args
            // This is for functions without explicit / separator
            
            // Regular args
            for arg in &args.args {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // *args
            if let Some(vararg) = &args.vararg {
                runtime_args.push(format!("*{}", self.format_arg(vararg)));
            } else if !args.kwonlyargs.is_empty() && args.args.is_empty() {
                // If no *args but we have keyword-only args, add *
                runtime_args.push("*".to_string());
            }

            // Keyword-only args
            for arg in &args.kwonlyargs {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // **kwargs
            if let Some(kwarg) = &args.kwarg {
                runtime_args.push(format!("**{}", self.format_arg(kwarg)));
            }
        }

        sig.push_str(&runtime_args.join(", "));
        sig.push(')');

        // Return type - transform to IProxy[T]
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str("IProxy[");
            sig.push_str(&self.format_type_annotation(returns));
            sig.push(']');
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
            // Handle directory patterns like "**/test/**" or "**/tests/**"
            if pattern.starts_with("**/") && pattern.ends_with("/**") {
                let dir_name = &pattern[3..pattern.len()-3];
                if file_path.contains(&format!("/{}/", dir_name)) {
                    return true;
                }
            }
            
            // Handle file patterns like "**/test_*.py"
            if pattern.starts_with("**/") && pattern.contains("*") {
                if let Some(file_name) = Path::new(file_path).file_name() {
                    let file_name_str = file_name.to_str().unwrap_or("");
                    
                    // Extract the pattern after "**/""
                    let file_pattern = &pattern[3..];
                    
                    // Simple glob matching for patterns like "test_*.py"
                    if file_pattern.starts_with("test_") && file_pattern.ends_with(".py") {
                        if file_name_str.starts_with("test_") && file_name_str.ends_with(".py") {
                            return true;
                        }
                    }
                    // Handle "*_test.py" pattern
                    else if file_pattern.starts_with("*_test.py") {
                        if file_name_str.ends_with("_test.py") {
                            return true;
                        }
                    }
                }
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
        content.push_str("from typing import overload\n");
        content.push_str("from pinjected import IProxy\n");
        
        // Note: Additional imports for return types would need to be added based on the actual types used
        // For now, we'll add a comment about this
        content.push_str("# Add imports for return types and parameter types as needed\n");
        content.push_str("\n");

        // Add function signatures with @overload
        for func in functions {
            content.push_str("@overload\n");
            content.push_str(&func.signature);
            content.push('\n');
            if !functions.iter().position(|f| f.name == func.name).unwrap() == functions.len() - 1 {
                content.push('\n');
            }
        }

        content
    }

    /// Extract function signatures from a stub file
    fn extract_stub_signatures(&self, stub_path: &Path) -> Result<HashMap<String, String>, String> {
        let content = fs::read_to_string(stub_path)
            .map_err(|e| format!("Failed to read stub file: {}", e))?;
        
        let ast = parse(&content, Mode::Module, stub_path.to_str().unwrap())
            .map_err(|e| format!("Failed to parse stub file: {}", e))?;
        
        let mut signatures = HashMap::new();
        
        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.extract_function_signatures(stmt, &mut signatures);
                }
            }
            _ => {}
        }
        
        Ok(signatures)
    }
    
    /// Extract function signatures from statements (handles nested functions)
    fn extract_function_signatures(&self, stmt: &Stmt, signatures: &mut HashMap<String, String>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                // Check if it has @overload decorator
                let has_overload = func.decorator_list.iter().any(|dec| {
                    if let Expr::Name(name) = dec {
                        name.id.as_str() == "overload"
                    } else {
                        false
                    }
                });
                
                if has_overload {
                    signatures.insert(func.name.to_string(), self.format_stub_signature(func));
                }
                
                // Check nested functions
                for stmt in &func.body {
                    self.extract_function_signatures(stmt, signatures);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                // Check if it has @overload decorator
                let has_overload = func.decorator_list.iter().any(|dec| {
                    if let Expr::Name(name) = dec {
                        name.id.as_str() == "overload"
                    } else {
                        false
                    }
                });
                
                if has_overload {
                    signatures.insert(func.name.to_string(), self.format_async_stub_signature(func));
                }
                
                // Check nested functions
                for stmt in &func.body {
                    self.extract_function_signatures(stmt, signatures);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.extract_function_signatures(stmt, signatures);
                }
            }
            _ => {}
        }
    }
    
    /// Format a function signature from stub file for comparison
    fn format_stub_signature(&self, func: &StmtFunctionDef) -> String {
        let sig = self.generate_function_signature(func);
        // Remove trailing ": ..." for comparison
        sig.trim_end_matches(": ...").to_string()
    }
    
    /// Format an async function signature from stub file for comparison
    fn format_async_stub_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let sig = self.generate_async_function_signature(func);
        // Remove trailing ": ..." for comparison
        sig.trim_end_matches(": ...").to_string()
    }
    
    /// Validate stub file signatures against expected signatures
    fn validate_stub_signatures(
        &self, 
        stub_path: &Path, 
        expected_functions: &[InjectedFunctionInfo]
    ) -> Vec<String> {
        let mut errors = Vec::new();
        
        // Try to parse the stub file
        let actual_signatures = match self.extract_stub_signatures(stub_path) {
            Ok(sigs) => sigs,
            Err(e) => {
                errors.push(format!("Failed to parse stub file: {}", e));
                return errors;
            }
        };
        
        // Check each expected function
        for expected in expected_functions {
            let expected_sig = expected.signature.trim_end_matches(": ...").to_string();
            
            match actual_signatures.get(&expected.name) {
                Some(actual_sig) => {
                    if actual_sig.trim() != expected_sig.trim() {
                        errors.push(format!(
                            "Function '{}' has incorrect signature in stub file.\nExpected: {}\nActual: {}",
                            expected.name,
                            expected_sig,
                            actual_sig
                        ));
                    }
                }
                None => {
                    errors.push(format!(
                        "Function '{}' is missing from stub file.\nExpected: {}",
                        expected.name,
                        expected_sig
                    ));
                }
            }
        }
        
        // Check for extra functions in stub file that shouldn't be there
        for (name, sig) in &actual_signatures {
            if !expected_functions.iter().any(|f| &f.name == name) {
                errors.push(format!(
                    "Unexpected function '{}' in stub file with signature: {}",
                    name,
                    sig
                ));
            }
        }
        
        errors
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

        // Load configuration for this file
        let config_path = Path::new(context.file_path);
        let config = if let Some(pyproject_path) = find_config_pyproject_toml(config_path.parent().unwrap_or(Path::new("."))) {
            load_config(Some(&pyproject_path))
        } else {
            None
        };
        
        let rule_config = config.as_ref()
            .and_then(|c| c.rules.get("PINJ014"));
        
        // Create a properly configured rule instance
        let configured_rule = Self::with_config(rule_config);

        // Count @injected functions
        let injected_count = configured_rule.count_injected_functions(context.ast);

        // No @injected functions, no violation
        if injected_count == 0 {
            return violations;
        }

        // Check minimum threshold
        if injected_count < configured_rule.min_injected_functions {
            return violations;
        }

        // Check if file should be ignored
        if configured_rule.should_ignore(context.file_path) {
            return violations;
        }

        // Collect expected functions first (we'll need them either way)
        let injected_functions = configured_rule.collect_injected_functions(context.ast);
        
        // Look for stub file
        if let Some(stub_path) = configured_rule.find_stub_file(context.file_path) {
            // Stub file exists - validate its contents
            let validation_errors = configured_rule.validate_stub_signatures(&stub_path, &injected_functions);
            
            if !validation_errors.is_empty() {
                let message = format!(
                    "Stub file {} has incorrect signatures:\n\n{}",
                    stub_path.display(),
                    validation_errors.join("\n\n")
                );
                
                // Generate fix content for validation errors
                let stub_content = configured_rule.generate_stub_content(&injected_functions);
                let fix = Fix {
                    description: "Update stub file with correct signatures".to_string(),
                    file_path: stub_path.clone(),
                    content: stub_content,
                };
                
                violations.push(Violation::with_fix(
                    self.rule_id().to_string(),
                    message,
                    0, // Report at start of file
                    context.file_path.to_string(),
                    Severity::Warning,
                    fix,
                ));
            }
            
            return violations;
        }

        // No stub file found - create violation with expected content
        let stub_file_path = Path::new(context.file_path).with_extension("pyi");
        let stub_content = configured_rule.generate_stub_content(&injected_functions);

        let message = format!(
            "Module contains {} @injected function(s) but no .pyi stub file found.\n\nExpected stub file: {}\n\nExpected content:\n{}",
            injected_count,
            stub_file_path.display(),
            stub_content
        );

        // Create fix for missing stub file
        let fix = Fix {
            description: "Create missing stub file".to_string(),
            file_path: stub_file_path.clone(),
            content: stub_content.clone(),
        };
        
        violations.push(Violation::with_fix(
            self.rule_id().to_string(),
            message,
            0, // Report at start of file
            context.file_path.to_string(),
            Severity::Warning,
            fix,
        ));

        violations
    }
}
