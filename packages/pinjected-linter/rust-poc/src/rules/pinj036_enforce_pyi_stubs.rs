//! PINJ036: Enforce .pyi stub files for all modules
//!
//! All Python modules should have corresponding .pyi stub files with complete
//! public API signatures for better IDE support and type checking.
//! Files starting with 'test' are excluded.

use crate::models::{Fix, RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_instance_decorator, has_instance_decorator_async, has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Arg, ArgWithDefault, Constant, Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
use rustpython_parser::{parse, Mode};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq)]
struct PublicSymbol {
    name: String,
    kind: SymbolKind,
    signature: Option<String>,
    has_instance_decorator: bool,
    has_injected_decorator: bool,
    return_type: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
enum SymbolKind {
    Function,
    AsyncFunction,
    Class,
    Variable,
}

pub struct EnforcePyiStubsRule {
    exclude_patterns: Vec<String>,
    check_completeness: bool,
}

impl EnforcePyiStubsRule {
    pub fn new() -> Self {
        Self {
            exclude_patterns: vec![
                "test_*.py".to_string(),
                "**/tests/**".to_string(),
                "**/test/**".to_string(),
                "**/migrations/**".to_string(),
            ],
            check_completeness: true,
        }
    }

    /// Check if the file should be excluded from checking
    fn should_exclude(&self, file_path: &str) -> bool {
        let path = Path::new(file_path);

        // Check if filename matches test_*.py pattern (pytest files)
        if let Some(file_name) = path.file_name() {
            let name = file_name.to_str().unwrap_or("");
            if name.starts_with("test_") && name.ends_with(".py") {
                return true;
            }
        }

        // Check exclude patterns
        for pattern in &self.exclude_patterns {
            if pattern.contains("**/tests/**") && file_path.contains("/tests/") {
                return true;
            }
            if pattern.contains("**/test/**") && file_path.contains("/test/") {
                return true;
            }
            if pattern.contains("**/migrations/**") && file_path.contains("/migrations/") {
                return true;
            }
        }

        // Exclude temporary files - but not /tmp/ root directory itself
        // if file_path.starts_with("/tmp/") || file_path.contains("/tmp/") {
        //     return true;
        // }

        false
    }

    /// Extract public symbols from a module
    fn extract_public_symbols(&self, ast: &Mod) -> Vec<PublicSymbol> {
        let mut symbols = Vec::new();

        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.extract_from_stmt(stmt, &mut symbols, "");
                }
            }
            _ => {}
        }

        symbols
    }

    /// Extract public symbols from a class body (handles class-level vs instance attributes)
    fn extract_from_class_body(&self, stmt: &Stmt, symbols: &mut Vec<PublicSymbol>, class_name: &str) {
        match stmt {
            // Methods are extracted normally
            Stmt::FunctionDef(_) | Stmt::AsyncFunctionDef(_) => {
                self.extract_from_stmt(stmt, symbols, class_name);
            }
            // Class-level assignments
            Stmt::Assign(assign) => {
                // In a class body, only consider simple Name targets (not attribute access)
                for target in &assign.targets {
                    if let Expr::Name(name) = target {
                        // Include all variables, both public and private
                        if true {
                            let full_name = format!("{}.{}", class_name, name.id);
                            symbols.push(PublicSymbol {
                                name: full_name,
                                kind: SymbolKind::Variable,
                                signature: None,
                                has_instance_decorator: false,
                                has_injected_decorator: false,
                                return_type: None,
                            });
                        }
                    }
                    // Ignore Expr::Attribute (e.g., self.x) - these are instance attributes
                }
            }
            // Class-level annotated assignments
            Stmt::AnnAssign(ann_assign) => {
                // Only consider simple Name targets (not self.x)
                if let Expr::Name(name) = ann_assign.target.as_ref() {
                    // Include all variables, both public and private
                    if true {
                        let full_name = format!("{}.{}", class_name, name.id);
                        let type_ann = self.format_type_annotation(&ann_assign.annotation);
                        symbols.push(PublicSymbol {
                            name: full_name,
                            kind: SymbolKind::Variable,
                            signature: Some(type_ann),
                            has_instance_decorator: false,
                            has_injected_decorator: false,
                            return_type: None,
                        });
                    }
                }
                // Ignore Expr::Attribute (e.g., self.x: int) - these are instance attributes
            }
            // Nested classes - process them as top-level classes within the parent class
            Stmt::ClassDef(nested_class) => {
                // Include all nested classes, both public and private
                if true {
                    let nested_full_name = format!("{}.{}", class_name, nested_class.name);
                    
                    symbols.push(PublicSymbol {
                        name: nested_full_name.clone(),
                        kind: SymbolKind::Class,
                        signature: None,
                        has_instance_decorator: false,
                        has_injected_decorator: false,
                        return_type: None,
                    });
                    
                    // Extract nested class members
                    for nested_stmt in &nested_class.body {
                        self.extract_from_class_body(nested_stmt, symbols, &nested_full_name);
                    }
                }
            }
            _ => {}
        }
    }

    /// Extract public symbols from a statement
    fn extract_from_stmt(&self, stmt: &Stmt, symbols: &mut Vec<PublicSymbol>, prefix: &str) {
        match stmt {
            Stmt::FunctionDef(func) => {
                // Include all methods, both public and private
                if true {
                    let full_name = if prefix.is_empty() {
                        func.name.to_string()
                    } else {
                        format!("{}.{}", prefix, func.name)
                    };

                    let has_instance = has_instance_decorator(func);
                    let has_injected = has_injected_decorator(func);
                    let return_type = func.returns.as_ref().map(|r| self.format_type_annotation(r));
                    
                    // Use special signature for @injected functions
                    let signature = if has_injected {
                        self.generate_injected_function_signature(func)
                    } else {
                        self.generate_function_signature(func)
                    };
                    
                    symbols.push(PublicSymbol {
                        name: full_name,
                        kind: SymbolKind::Function,
                        signature: Some(signature),
                        has_instance_decorator: has_instance,
                        has_injected_decorator: has_injected,
                        return_type,
                    });
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                // Include all methods, both public and private
                if true {
                    let full_name = if prefix.is_empty() {
                        func.name.to_string()
                    } else {
                        format!("{}.{}", prefix, func.name)
                    };

                    let has_instance = has_instance_decorator_async(func);
                    let has_injected = has_injected_decorator_async(func);
                    let return_type = func.returns.as_ref().map(|r| self.format_type_annotation(r));
                    
                    // Use special signature for @injected functions
                    let signature = if has_injected {
                        self.generate_injected_async_function_signature(func)
                    } else {
                        self.generate_async_function_signature(func)
                    };
                    
                    symbols.push(PublicSymbol {
                        name: full_name,
                        kind: SymbolKind::AsyncFunction,
                        signature: Some(signature),
                        has_instance_decorator: has_instance,
                        has_injected_decorator: has_injected,
                        return_type,
                    });
                }
            }
            Stmt::ClassDef(class) => {
                // Include all classes, both public and private
                if true {
                    let full_name = if prefix.is_empty() {
                        class.name.to_string()
                    } else {
                        format!("{}.{}", prefix, class.name)
                    };

                    symbols.push(PublicSymbol {
                        name: full_name.clone(),
                        kind: SymbolKind::Class,
                        signature: None,
                        has_instance_decorator: false,
                        has_injected_decorator: false,
                        return_type: None,
                    });

                    // Extract public methods and class-level attributes from the class
                    // When inside a class, we need to handle assignments differently
                    for stmt in &class.body {
                        self.extract_from_class_body(stmt, symbols, &full_name);
                    }
                }
            }
            Stmt::Assign(assign) => {
                // Extract module-level variable assignments
                for target in &assign.targets {
                    if let Expr::Name(name) = target {
                        // Include all variables, both public and private
                        if true {
                            let full_name = if prefix.is_empty() {
                                name.id.to_string()
                            } else {
                                format!("{}.{}", prefix, name.id)
                            };

                            symbols.push(PublicSymbol {
                                name: full_name,
                                kind: SymbolKind::Variable,
                                signature: None,
                                has_instance_decorator: false,
                                has_injected_decorator: false,
                                return_type: None,
                            });
                        }
                    }
                }
            }
            Stmt::AnnAssign(ann_assign) => {
                // Extract annotated module-level variables
                if let Expr::Name(name) = ann_assign.target.as_ref() {
                    // Include all variables, both public and private
                    if true {
                        let full_name = if prefix.is_empty() {
                            name.id.to_string()
                        } else {
                            format!("{}.{}", prefix, name.id)
                        };

                        let type_ann = self.format_type_annotation(&ann_assign.annotation);
                        symbols.push(PublicSymbol {
                            name: full_name,
                            kind: SymbolKind::Variable,
                            signature: Some(type_ann),
                            has_instance_decorator: false,
                            has_injected_decorator: false,
                            return_type: None,
                        });
                    }
                }
            }
            _ => {}
        }
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
            Expr::Tuple(tuple) => {
                // Handle tuple expressions like Dict[str, str]
                let elements: Vec<String> = tuple.elts.iter()
                    .map(|e| self.format_type_annotation(e))
                    .collect();
                elements.join(", ")
            }
            Expr::Attribute(attr) => {
                let value = self.format_type_annotation(&attr.value);
                format!("{}.{}", value, attr.attr)
            }
            Expr::BinOp(binop) => {
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

    /// Generate function signature
    fn generate_function_signature(&self, func: &StmtFunctionDef) -> String {
        let mut sig = String::new();
        sig.push_str(func.name.as_str());
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

        // Return type - always include one, defaulting to Any if not specified
        sig.push_str(" -> ");
        if let Some(returns) = &func.returns {
            sig.push_str(&self.format_type_annotation(returns));
        } else {
            sig.push_str("Any");
        }

        sig
    }

    /// Generate async function signature
    fn generate_async_function_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let mut sig = String::new();
        sig.push_str(func.name.as_str());
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

        // Return type - always include one, defaulting to Any if not specified
        sig.push_str(" -> ");
        if let Some(returns) = &func.returns {
            sig.push_str(&self.format_type_annotation(returns));
        } else {
            sig.push_str("Any");
        }

        sig
    }

    /// Generate function signature for @injected functions (removing positional-only args)
    fn generate_injected_function_signature(&self, func: &StmtFunctionDef) -> String {
        let mut sig = String::new();
        sig.push_str(func.name.as_str());
        sig.push('(');

        let args = &func.args;
        let mut runtime_args = Vec::new();

        // For @injected functions, skip position-only args (dependencies)
        // Only include runtime args (after /)
        
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

        sig.push_str(&runtime_args.join(", "));
        sig.push(')');

        // Return type - wrap in IProxy[T] for @injected functions
        sig.push_str(" -> ");
        if let Some(returns) = &func.returns {
            sig.push_str("IProxy[");
            sig.push_str(&self.format_type_annotation(returns));
            sig.push(']');
        } else {
            sig.push_str("IProxy[Any]");
        }

        sig
    }

    /// Generate async function signature for @injected functions (removing positional-only args)
    fn generate_injected_async_function_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let mut sig = String::new();
        sig.push_str(func.name.as_str());
        sig.push('(');

        let args = &func.args;
        let mut runtime_args = Vec::new();

        // For @injected functions, skip position-only args (dependencies)
        // Only include runtime args (after /)
        
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

        sig.push_str(&runtime_args.join(", "));
        sig.push(')');

        // Return type - wrap in IProxy[T] for @injected functions
        sig.push_str(" -> ");
        if let Some(returns) = &func.returns {
            sig.push_str("IProxy[");
            sig.push_str(&self.format_type_annotation(returns));
            sig.push(']');
        } else {
            sig.push_str("IProxy[Any]");
        }

        sig
    }

    /// Find the corresponding .pyi file
    fn find_stub_file(&self, file_path: &str) -> Option<PathBuf> {
        let path = Path::new(file_path);
        let stub_path = path.with_extension("pyi");

        if stub_path.exists() {
            Some(stub_path)
        } else {
            None
        }
    }

    /// Parse and extract symbols from .pyi file
    fn extract_stub_symbols(&self, stub_path: &Path) -> Result<Vec<PublicSymbol>, String> {
        let content = fs::read_to_string(stub_path)
            .map_err(|e| format!("Failed to read stub file: {}", e))?;

        let ast = parse(&content, rustpython_parser::Mode::Module, "<stub>")
            .map_err(|e| format!("Failed to parse stub file: {}", e))?;

        Ok(self.extract_public_symbols(&ast))
    }

    /// Compare module symbols with stub symbols
    fn find_missing_symbols(
        &self,
        module_symbols: &[PublicSymbol],
        stub_symbols: &[PublicSymbol],
    ) -> Vec<PublicSymbol> {
        module_symbols
            .iter()
            .filter(|module_sym| {
                // For @instance functions, they should be present as variables in stub
                if module_sym.has_instance_decorator {
                    // Check if it exists as a variable in stub
                    !stub_symbols.iter().any(|stub_sym| {
                        stub_sym.name == module_sym.name && matches!(stub_sym.kind, SymbolKind::Variable)
                    })
                } 
                // For @injected functions, check if they have correct signature with @overload
                else if module_sym.has_injected_decorator {
                    !stub_symbols.iter().any(|stub_sym| {
                        stub_sym.name == module_sym.name 
                            && matches!(stub_sym.kind, SymbolKind::Function | SymbolKind::AsyncFunction)
                            // For now, just check name exists. More sophisticated comparison could check signature
                    })
                } else {
                    // For other symbols, check if they exist with matching kind
                    !stub_symbols.iter().any(|stub_sym| {
                        stub_sym.name == module_sym.name && stub_sym.kind == module_sym.kind
                    })
                }
            })
            .cloned()
            .collect()
    }

    /// Merge existing stub content with missing symbols
    fn merge_stub_content(&self, existing_content: &str, missing_symbols: &[PublicSymbol]) -> String {
        if existing_content.is_empty() {
            return self.generate_stub_content(missing_symbols);
        }

        // Parse existing content to preserve it
        let existing_ast = match parse(existing_content, Mode::Module, "<stub>") {
            Ok(ast) => ast,
            Err(_) => {
                // If we can't parse, append to existing content
                let mut result = existing_content.to_string();
                if !result.ends_with('\n') {
                    result.push('\n');
                }
                result.push_str("\n# Additional symbols added by linter:\n");
                result.push_str(&self.generate_stub_content(missing_symbols));
                return result;
            }
        };

        // Collect existing imports and symbols
        let mut has_iproxy_import = false;
        let mut has_overload_import = false;
        let mut has_any_import = false;
        let mut existing_symbols = HashSet::new();
        let mut classes_with_ellipsis = HashMap::new();
        
        if let Mod::Module(module) = &existing_ast {
            for stmt in &module.body {
                match stmt {
                    Stmt::ImportFrom(import_from) => {
                        if let Some(module) = &import_from.module {
                            match module.as_str() {
                                "typing" => {
                                    for alias in &import_from.names {
                                        match alias.name.as_str() {
                                            "overload" => has_overload_import = true,
                                            "Any" => has_any_import = true,
                                            _ => {}
                                        }
                                    }
                                }
                                "pinjected" => {
                                    for alias in &import_from.names {
                                        if alias.name.as_str() == "IProxy" {
                                            has_iproxy_import = true;
                                        }
                                    }
                                }
                                _ => {}
                            }
                        }
                    }
                    Stmt::FunctionDef(func) => {
                        existing_symbols.insert(func.name.to_string());
                    }
                    Stmt::AsyncFunctionDef(func) => {
                        existing_symbols.insert(func.name.to_string());
                    }
                    Stmt::ClassDef(class) => {
                        existing_symbols.insert(class.name.to_string());
                        // Check if this class has only ... as its body
                        if class.body.len() == 1 {
                            if let Stmt::Expr(expr_stmt) = &class.body[0] {
                                if matches!(expr_stmt.value.as_ref(), Expr::Constant(c) if matches!(&c.value, Constant::Ellipsis)) {
                                    classes_with_ellipsis.insert(class.name.to_string(), true);
                                }
                            }
                        }
                    }
                    Stmt::AnnAssign(ann_assign) => {
                        if let Expr::Name(name) = ann_assign.target.as_ref() {
                            existing_symbols.insert(name.id.to_string());
                        }
                    }
                    Stmt::Assign(assign) => {
                        for target in &assign.targets {
                            if let Expr::Name(name) = target {
                                existing_symbols.insert(name.id.to_string());
                            }
                        }
                    }
                    _ => {}
                }
            }
        }

        // Don't filter any missing symbols - they were already identified as missing
        // by find_missing_symbols which checks for correct declarations
        let truly_missing = missing_symbols.to_vec();

        if truly_missing.is_empty() {
            return existing_content.to_string();
        }

        // Determine what imports we need
        let needs_iproxy = !has_iproxy_import && truly_missing.iter().any(|s| s.has_instance_decorator || s.has_injected_decorator);
        let needs_overload = !has_overload_import && truly_missing.iter().any(|s| s.has_injected_decorator);
        let needs_any = !has_any_import && (needs_iproxy || truly_missing.iter().any(|s| s.signature.is_none()));

        // Check if we need to expand any classes with ellipsis
        let mut classes_to_expand = HashMap::new();
        for symbol in &truly_missing {
            if let Some(dot_pos) = symbol.name.find('.') {
                let class_name = &symbol.name[..dot_pos];
                if classes_with_ellipsis.contains_key(class_name) {
                    classes_to_expand.entry(class_name.to_string())
                        .or_insert_with(Vec::new)
                        .push(symbol);
                }
            }
        }

        // If we have classes to expand, we need to reconstruct the entire file
        if !classes_to_expand.is_empty() {
            return self.reconstruct_with_expanded_classes(
                existing_content,
                &existing_ast,
                &classes_to_expand,
                &truly_missing,
                needs_any,
                needs_overload,
                needs_iproxy,
                has_any_import,
                has_overload_import,
                has_iproxy_import,
            );
        }

        // Otherwise, use the old append approach
        let mut result = existing_content.to_string();
        
        // Ensure file ends with newline
        if !result.ends_with('\n') {
            result.push('\n');
        }
        
        // Add missing imports at the beginning if needed
        if needs_any || needs_overload || needs_iproxy {
            let mut import_lines = Vec::new();
            
            // Find where to insert imports (after existing imports or at the beginning)
            let lines: Vec<&str> = result.lines().collect();
            let mut insert_pos = 0;
            for (i, line) in lines.iter().enumerate() {
                if line.starts_with("from ") || line.starts_with("import ") {
                    insert_pos = i + 1;
                } else if !line.trim().is_empty() && insert_pos > 0 {
                    break;
                }
            }
            
            if needs_any || needs_overload {
                let mut typing_imports = Vec::new();
                if needs_overload {
                    typing_imports.push("overload");
                }
                if needs_any {
                    typing_imports.push("Any");
                }
                import_lines.push(format!("from typing import {}", typing_imports.join(", ")));
            }
            
            if needs_iproxy {
                import_lines.push("from pinjected import IProxy".to_string());
            }
            
            // Reconstruct the file with new imports
            let mut new_lines = Vec::new();
            for (i, line) in lines.iter().enumerate() {
                if i == insert_pos && !import_lines.is_empty() {
                    for import in &import_lines {
                        new_lines.push(import.as_str());
                    }
                    if insert_pos == 0 {
                        new_lines.push(""); // blank line after imports
                    }
                }
                new_lines.push(line);
            }
            result = new_lines.join("\n");
            if !result.ends_with('\n') {
                result.push('\n');
            }
        }
        
        // Add missing symbols
        result.push_str("\n# Additional symbols:\n");
        result.push_str(&self.generate_stub_content(&truly_missing));
        
        result
    }

    /// Reconstruct the stub file with expanded class definitions
    fn reconstruct_with_expanded_classes(
        &self,
        _existing_content: &str,
        existing_ast: &Mod,
        classes_to_expand: &HashMap<String, Vec<&PublicSymbol>>,
        all_missing_symbols: &[PublicSymbol],
        needs_any: bool,
        needs_overload: bool,
        needs_iproxy: bool,
        has_any_import: bool,
        has_overload_import: bool,
        has_iproxy_import: bool,
    ) -> String {
        let mut result = String::new();
        let mut imports_added = false;

        // First, handle imports
        if let Mod::Module(module) = existing_ast {
            // Collect existing imports
            let mut import_stmts = Vec::new();
            let mut other_stmts = Vec::new();
            
            for stmt in &module.body {
                match stmt {
                    Stmt::Import(_) | Stmt::ImportFrom(_) => {
                        import_stmts.push(stmt);
                    }
                    _ => {
                        other_stmts.push(stmt);
                    }
                }
            }
            
            // Add existing imports
            for stmt in &import_stmts {
                result.push_str(&self.stmt_to_string(stmt));
                result.push('\n');
            }
            
            // Add new imports if needed
            if needs_any && !has_any_import || needs_overload && !has_overload_import {
                let mut typing_imports = Vec::new();
                if needs_overload && !has_overload_import {
                    typing_imports.push("overload");
                }
                if needs_any && !has_any_import {
                    typing_imports.push("Any");
                }
                result.push_str(&format!("from typing import {}\n", typing_imports.join(", ")));
                imports_added = true;
            }
            
            if needs_iproxy && !has_iproxy_import {
                result.push_str("from pinjected import IProxy\n");
                imports_added = true;
            }
            
            // Add blank line after imports
            if !import_stmts.is_empty() || imports_added {
                result.push('\n');
            }
            
            // Process other statements
            for stmt in &other_stmts {
                match stmt {
                    Stmt::ClassDef(class) if classes_to_expand.contains_key(&class.name.to_string()) => {
                        // This is a class we need to expand
                        let class_members = classes_to_expand.get(&class.name.to_string()).unwrap();
                        result.push_str(&self.generate_expanded_class(&class.name, class_members, &class.decorator_list));
                        result.push('\n');
                    }
                    _ => {
                        // Keep other statements as-is
                        result.push_str(&self.stmt_to_string(stmt));
                        result.push('\n');
                    }
                }
            }
            
            // Add any remaining symbols that weren't part of expanded classes
            let expanded_symbols: HashSet<String> = classes_to_expand.values()
                .flat_map(|members| members.iter().map(|s| s.name.clone()))
                .collect();
            
            let remaining_symbols: Vec<&PublicSymbol> = all_missing_symbols.iter()
                .filter(|s| !expanded_symbols.contains(&s.name))
                .collect();
            
            if !remaining_symbols.is_empty() {
                result.push_str("\n# Additional symbols:\n");
                result.push_str(&self.generate_stub_content(&remaining_symbols.into_iter().cloned().collect::<Vec<_>>()));
            }
        }
        
        result
    }

    /// Generate an expanded class definition with all its members
    fn generate_expanded_class(&self, class_name: &str, members: &[&PublicSymbol], decorators: &[Expr]) -> String {
        let mut result = String::new();
        
        // Add decorators
        for decorator in decorators {
            result.push_str(&self.decorator_to_string(decorator));
            result.push('\n');
        }
        
        result.push_str(&format!("class {}:\n", class_name));
        
        if members.is_empty() {
            result.push_str("    ...\n");
            return result;
        }
        
        // Separate members by type
        let mut fields = Vec::new();
        let mut methods = Vec::new();
        
        for member in members {
            let member_name = &member.name[class_name.len() + 1..]; // Remove "ClassName."
            match member.kind {
                SymbolKind::Variable => fields.push((member_name, member)),
                SymbolKind::Function | SymbolKind::AsyncFunction => methods.push((member_name, member)),
                _ => {}
            }
        }
        
        // Generate fields first
        for (field_name, field) in &fields {
            result.push_str("    ");
            if let Some(sig) = &field.signature {
                result.push_str(&format!("{}: {}\n", field_name, sig));
            } else {
                result.push_str(&format!("{}: Any\n", field_name));
            }
        }
        
        // Add blank line between fields and methods if both exist
        if !fields.is_empty() && !methods.is_empty() {
            result.push('\n');
        }
        
        // Generate methods
        for (method_name, method) in &methods {
            result.push_str("    ");
            if matches!(method.kind, SymbolKind::AsyncFunction) {
                result.push_str("async ");
            }
            result.push_str("def ");
            
            if let Some(sig) = &method.signature {
                // Replace the full name with just the method name
                let sig_with_method_name = sig.replace(&method.name, method_name);
                result.push_str(&sig_with_method_name);
            } else {
                result.push_str(method_name);
                result.push_str("(self, *args, **kwargs) -> Any");
            }
            result.push_str(": ...\n");
        }
        
        result
    }

    /// Convert a statement back to string representation
    fn stmt_to_string(&self, stmt: &Stmt) -> String {
        // This is a simplified version - in a real implementation, 
        // you'd want to use a proper AST-to-source converter
        match stmt {
            Stmt::Import(import) => {
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
            }
            Stmt::ImportFrom(import_from) => {
                let module = import_from.module.as_deref().unwrap_or("");
                let names: Vec<String> = import_from.names.iter()
                    .map(|alias| {
                        if let Some(asname) = &alias.asname {
                            format!("{} as {}", alias.name, asname)
                        } else {
                            alias.name.to_string()
                        }
                    })
                    .collect();
                let level_dots = ".".repeat(import_from.level.map(|l| l.to_u32() as usize).unwrap_or(0));
                format!("from {}{} import {}", level_dots, module, names.join(", "))
            }
            Stmt::ClassDef(class) => {
                let mut result = String::new();
                for decorator in &class.decorator_list {
                    result.push_str(&self.decorator_to_string(decorator));
                    result.push('\n');
                }
                result.push_str(&format!("class {}:\n", class.name));
                result.push_str("    ...");
                result
            }
            Stmt::FunctionDef(func) => {
                let mut result = String::new();
                for decorator in &func.decorator_list {
                    result.push_str(&self.decorator_to_string(decorator));
                    result.push('\n');
                }
                result.push_str(&format!("def {}(", func.name));
                // Add simplified args
                result.push_str("*args, **kwargs");
                result.push_str(") -> Any: ...");
                result
            }
            Stmt::AsyncFunctionDef(func) => {
                let mut result = String::new();
                for decorator in &func.decorator_list {
                    result.push_str(&self.decorator_to_string(decorator));
                    result.push('\n');
                }
                result.push_str(&format!("async def {}(", func.name));
                // Add simplified args
                result.push_str("*args, **kwargs");
                result.push_str(") -> Any: ...");
                result
            }
            Stmt::AnnAssign(ann_assign) => {
                if let Expr::Name(name) = ann_assign.target.as_ref() {
                    format!("{}: Any", name.id)
                } else {
                    "# Unknown annotation".to_string()
                }
            }
            _ => "# Preserved statement".to_string()
        }
    }

    /// Convert a decorator to string representation
    fn decorator_to_string(&self, decorator: &Expr) -> String {
        match decorator {
            Expr::Name(name) => format!("@{}", name.id),
            Expr::Attribute(attr) => {
                if let Expr::Name(obj) = attr.value.as_ref() {
                    format!("@{}.{}", obj.id, attr.attr)
                } else {
                    "@unknown".to_string()
                }
            }
            _ => "@unknown".to_string()
        }
    }

    /// Generate stub file content for missing symbols
    fn generate_stub_content(&self, missing_symbols: &[PublicSymbol]) -> String {
        let mut content = String::new();

        // Group symbols by type
        let mut functions = Vec::new();
        let mut injected_functions = Vec::new();
        let mut instance_functions = Vec::new();
        let mut classes = HashMap::new();
        let mut variables = Vec::new();

        for symbol in missing_symbols {
            match &symbol.kind {
                SymbolKind::Function | SymbolKind::AsyncFunction => {
                    if !symbol.name.contains('.') {
                        if symbol.has_instance_decorator {
                            instance_functions.push(symbol);
                        } else if symbol.has_injected_decorator {
                            injected_functions.push(symbol);
                        } else {
                            functions.push(symbol);
                        }
                    }
                }
                SymbolKind::Class => {
                    // Always create an entry for the class, even if it's nested
                    classes.insert(symbol.name.clone(), Vec::new());
                }
                SymbolKind::Variable => {
                    if !symbol.name.contains('.') {
                        variables.push(symbol);
                    }
                }
            }
        }

        // Collect class methods, attributes, and nested classes
        for symbol in missing_symbols {
            if let Some(_dot_pos) = symbol.name.find('.') {
                // For nested class members like ComplexClass.NestedConfig.timeout,
                // we need to find the correct class to add it to
                let parts: Vec<&str> = symbol.name.split('.').collect();
                
                // Try to find the deepest class that exists
                for i in (1..parts.len()).rev() {
                    let class_path = parts[..i].join(".");
                    if let Some(class_members) = classes.get_mut(&class_path) {
                        class_members.push(symbol);
                        break;
                    } else if i == parts.len() - 1 && symbol.kind == SymbolKind::Class {
                        // This is a class declaration itself
                        // Find its parent class
                        if i > 1 {
                            let parent_path = parts[..i-1].join(".");
                            if let Some(parent_members) = classes.get_mut(&parent_path) {
                                parent_members.push(symbol);
                                // Also create an entry for this nested class
                                classes.insert(symbol.name.clone(), Vec::new());
                            }
                        }
                    }
                }
            }
        }

        // Add imports if we have @instance or @injected functions
        let needs_iproxy = !instance_functions.is_empty() || !injected_functions.is_empty();
        let needs_overload = !injected_functions.is_empty();
        
        if needs_iproxy || needs_overload {
            if needs_overload {
                content.push_str("from typing import overload");
                if needs_iproxy {
                    content.push_str(", Any\n");
                } else {
                    content.push_str("\n");
                }
            } else if needs_iproxy {
                content.push_str("from typing import Any\n");
            }
            
            if needs_iproxy {
                content.push_str("from pinjected import IProxy\n");
            }
            content.push_str("\n");
        }

        // Generate variables
        if !variables.is_empty() {
            for var in &variables {
                if let Some(sig) = &var.signature {
                    content.push_str(&format!("{}: {}\n", var.name, sig));
                } else {
                    content.push_str(&format!("{}: Any\n", var.name));
                }
            }
            content.push('\n');
        }

        // Generate @instance functions as IProxy declarations
        if !instance_functions.is_empty() {
            for func in &instance_functions {
                let return_type = func.return_type.as_ref()
                    .map(|s| s.as_str())
                    .unwrap_or("Any");
                content.push_str(&format!("{}: IProxy[{}]\n", func.name, return_type));
            }
            content.push('\n');
        }

        // Generate @injected functions with @overload
        if !injected_functions.is_empty() {
            for func in &injected_functions {
                content.push_str("@overload\n");
                if matches!(func.kind, SymbolKind::AsyncFunction) {
                    content.push_str("async ");
                }
                content.push_str("def ");
                if let Some(sig) = &func.signature {
                    content.push_str(sig);
                } else {
                    content.push_str(&func.name);
                    content.push_str("(*args, **kwargs) -> IProxy[Any]");
                }
                content.push_str(": ...\n\n");
            }
        }

        // Generate regular functions
        for func in &functions {
            if matches!(func.kind, SymbolKind::AsyncFunction) {
                content.push_str("async ");
            }
            content.push_str("def ");
            if let Some(sig) = &func.signature {
                content.push_str(sig);
            } else {
                content.push_str(&func.name);
                content.push_str("(*args, **kwargs) -> Any");
            }
            content.push_str(": ...\n\n");
        }

        // Generate classes with proper nesting support
        let mut processed_nested = HashSet::new();
        
        
        for (class_name, class_members) in &classes {
            // Skip if this is a nested class that will be handled by its parent
            if class_name.contains('.') {
                continue;
            }
            
            content.push_str(&format!("class {}:\n", class_name));

            if class_members.is_empty() && !classes.keys().any(|k| k.starts_with(&format!("{}.", class_name))) {
                content.push_str("    ...\n");
            } else {
                // Separate class variables from methods and nested classes
                let mut class_vars = Vec::new();
                let mut methods = Vec::new();
                let mut nested_classes = HashMap::new();
                
                for member in class_members {
                    // Check if this member belongs to a nested class
                    let member_path = &member.name[class_name.len() + 1..];
                    if member_path.contains('.') {
                        // This is a member of a nested class, skip it here
                        continue;
                    }
                    
                    match member.kind {
                        SymbolKind::Variable => class_vars.push(member),
                        SymbolKind::Function | SymbolKind::AsyncFunction => methods.push(member),
                        SymbolKind::Class => {
                            // This is a nested class declaration
                            nested_classes.insert(member.name.clone(), member_path.to_string());
                        }
                    }
                }
                
                // Generate class variables first
                for var in &class_vars {
                    content.push_str("    ");
                    let var_name = &var.name[class_name.len() + 1..];
                    if let Some(sig) = &var.signature {
                        content.push_str(&format!("{}: {}\n", var_name, sig));
                    } else {
                        content.push_str(&format!("{}: Any\n", var_name));
                    }
                }
                
                // Then generate methods
                for method in &methods {
                    content.push_str("    ");
                    if matches!(method.kind, SymbolKind::AsyncFunction) {
                        content.push_str("async ");
                    }
                    content.push_str("def ");

                    // Extract method name (after class name and dot)
                    let method_name = &method.name[class_name.len() + 1..];

                    if let Some(sig) = &method.signature {
                        // Replace the full name with just the method name in signature
                        let sig_with_method_name = sig.replace(&method.name, method_name);
                        content.push_str(&sig_with_method_name);
                    } else {
                        content.push_str(method_name);
                        content.push_str("(self, *args, **kwargs) -> Any");
                    }
                    content.push_str(": ...\n");
                }
                
                // Generate nested classes
                for (nested_full_name, nested_short_name) in &nested_classes {
                    content.push_str("\n");
                    content.push_str("    class ");
                    content.push_str(&nested_short_name);
                    content.push_str(":\n");
                    
                    // Find members of this nested class
                    let nested_members = classes.get(nested_full_name);
                    if let Some(members) = nested_members {
                        if members.is_empty() {
                            content.push_str("        ...\n");
                        } else {
                            // Process nested class members
                            for member in members {
                                match member.kind {
                                    SymbolKind::Variable => {
                                        content.push_str("        ");
                                        let var_name = &member.name[nested_full_name.len() + 1..];
                                        if let Some(sig) = &member.signature {
                                            content.push_str(&format!("{}: {}\n", var_name, sig));
                                        } else {
                                            content.push_str(&format!("{}: Any\n", var_name));
                                        }
                                    }
                                    SymbolKind::Function | SymbolKind::AsyncFunction => {
                                        content.push_str("        ");
                                        if matches!(member.kind, SymbolKind::AsyncFunction) {
                                            content.push_str("async ");
                                        }
                                        content.push_str("def ");
                                        let method_name = &member.name[nested_full_name.len() + 1..];
                                        if let Some(sig) = &member.signature {
                                            let sig_with_method_name = sig.replace(&member.name, method_name);
                                            content.push_str(&sig_with_method_name);
                                        } else {
                                            content.push_str(method_name);
                                            content.push_str("(self, *args, **kwargs) -> Any");
                                        }
                                        content.push_str(": ...\n");
                                    }
                                    _ => {}
                                }
                            }
                        }
                    } else {
                        content.push_str("        ...\n");
                    }
                    processed_nested.insert(nested_full_name.clone());
                }
            }
            content.push('\n');
        }

        content
    }
}

impl LintRule for EnforcePyiStubsRule {
    fn rule_id(&self) -> &str {
        "PINJ036"
    }

    fn description(&self) -> &str {
        "All modules should have corresponding .pyi stub files with complete public API signatures"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        // This is a module-level rule - check if we're in the module-level context
        match context.stmt {
            Stmt::Pass(_) => {
                // This is the module-level check, proceed
            }
            _ => {
                // This is a statement-level check, skip
                return violations;
            }
        }

        // Check if file should be excluded
        if self.should_exclude(context.file_path) {
            return violations;
        }

        // Extract public symbols from the module
        let module_symbols = self.extract_public_symbols(context.ast);

        // If no public symbols, no need for stub file
        if module_symbols.is_empty() {
            return violations;
        }

        // Check for stub file
        if let Some(stub_path) = self.find_stub_file(context.file_path) {
            // Stub file exists, check completeness if enabled
            if self.check_completeness {
                match self.extract_stub_symbols(&stub_path) {
                    Ok(stub_symbols) => {
                        let missing = self.find_missing_symbols(&module_symbols, &stub_symbols);

                        if !missing.is_empty() {
                            let missing_names: Vec<String> = missing
                                .iter()
                                .map(|s| {
                                    format!(
                                        "  - {} ({})",
                                        s.name,
                                        match s.kind {
                                            SymbolKind::Function => "function",
                                            SymbolKind::AsyncFunction => "async function",
                                            SymbolKind::Class => "class",
                                            SymbolKind::Variable => "variable",
                                        }
                                    )
                                })
                                .collect();

                            // Read existing stub content
                            let existing_content = fs::read_to_string(&stub_path).unwrap_or_default();
                            
                            // Generate merged content that preserves existing content
                            let merged_content = self.merge_stub_content(&existing_content, &missing);

                            let message = format!(
                                "Stub file exists but is missing the following public symbols:\n{}",
                                missing_names.join("\n")
                            );

                            let fix = Fix {
                                description: "Update stub file with missing symbols while preserving existing content".to_string(),
                                file_path: stub_path.clone(),
                                content: merged_content,
                            };

                            violations.push(Violation::with_fix(
                                self.rule_id().to_string(),
                                message,
                                0,
                                context.file_path.to_string(),
                                Severity::Warning,
                                fix,
                            ));
                        }
                    }
                    Err(e) => {
                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message: format!("Failed to parse stub file: {}", e),
                            offset: 0,
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }
                }
            }
        } else {
            // No stub file found
            let stub_path = Path::new(context.file_path).with_extension("pyi");
            let stub_content = self.generate_stub_content(&module_symbols);

            let message = format!(
                "Module has {} public symbol(s) but no .pyi stub file found",
                module_symbols.len()
            );

            let fix = Fix {
                description: "Create missing stub file".to_string(),
                file_path: stub_path.clone(),
                content: stub_content,
            };

            violations.push(Violation::with_fix(
                self.rule_id().to_string(),
                message,
                0,
                context.file_path.to_string(),
                Severity::Warning,
                fix,
            ));
        }

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_parser::{parse, Mode};
    use std::fs;
    use tempfile::tempdir;

    fn check_rule(source: &str, file_path: &str) -> Vec<Violation> {
        let rule = EnforcePyiStubsRule::new();
        let ast = parse(source, Mode::Module, file_path).unwrap();
        let context = RuleContext {
            stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass {
                range: rustpython_ast::text_size::TextRange::default(),
            }),
            file_path,
            source,
            ast: &ast,
        };
        rule.check(&context)
    }

    #[test]
    fn test_instance_function_stub_generation() {
        let code = r#"
from pinjected import instance
from typing import Dict

@instance
def database() -> DatabaseConnection:
    return DatabaseConnection()

@instance
async def cache_service() -> CacheService:
    return await CacheService.create()

@instance
def config() -> Dict[str, str]:
    return {"api_key": "secret"}

def regular_function() -> str:
    return "hello"
"#;

        let violations = check_rule(code, "mymodule.py");

        assert_eq!(violations.len(), 1);
        let violation = &violations[0];
        
        // Check that the fix is present
        assert!(violation.fix.is_some());
        let fix = violation.fix.as_ref().unwrap();
        
        // Check that the generated stub content includes IProxy declarations
        println!("Fix content: {}", fix.content);
        assert!(fix.content.contains("from pinjected import IProxy"));
        assert!(fix.content.contains("database: IProxy[DatabaseConnection]"));
        assert!(fix.content.contains("cache_service: IProxy[CacheService]"));
        assert!(fix.content.contains("config: IProxy[Dict[str, str]]"));
        
        // Regular function should still be a function
        assert!(fix.content.contains("def regular_function() -> str: ..."));
    }

    #[test]
    fn test_instance_function_with_existing_correct_stub() {
        let dir = tempdir().unwrap();
        let py_path = dir.path().join("mymodule.py");
        let pyi_path = dir.path().join("mymodule.pyi");

        let py_content = r#"
from pinjected import instance

@instance
def resource() -> MyResource:
    return MyResource()
"#;

        let pyi_content = r#"
from pinjected import IProxy

resource: IProxy[MyResource]
"#;

        fs::write(&py_path, py_content).unwrap();
        fs::write(&pyi_path, pyi_content).unwrap();

        let rule = EnforcePyiStubsRule::new();
        let ast = parse(py_content, Mode::Module, py_path.to_str().unwrap()).unwrap();
        let context = RuleContext {
            stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass {
                range: rustpython_ast::text_size::TextRange::default(),
            }),
            file_path: py_path.to_str().unwrap(),
            source: py_content,
            ast: &ast,
        };

        let violations = rule.check(&context);
        
        // Should not have violations since stub is correct
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_instance_function_with_wrong_stub() {
        let dir = tempdir().unwrap();
        let py_path = dir.path().join("mymodule.py");
        let pyi_path = dir.path().join("mymodule.pyi");

        let py_content = r#"
from pinjected import instance

@instance
def resource() -> MyResource:
    return MyResource()
"#;

        let pyi_content = r#"
def resource() -> MyResource: ...
"#;

        fs::write(&py_path, py_content).unwrap();
        fs::write(&pyi_path, pyi_content).unwrap();

        let rule = EnforcePyiStubsRule::new();
        let ast = parse(py_content, Mode::Module, py_path.to_str().unwrap()).unwrap();
        let context = RuleContext {
            stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass {
                range: rustpython_ast::text_size::TextRange::default(),
            }),
            file_path: py_path.to_str().unwrap(),
            source: py_content,
            ast: &ast,
        };

        let violations = rule.check(&context);
        
        // Should have violation since @instance function is declared as regular function
        assert_eq!(violations.len(), 1);
        assert!(violations[0].fix.is_some());
        let fix = violations[0].fix.as_ref().unwrap();
        println!("Fix content:\n{}", fix.content);
        assert!(fix.content.contains("resource: IProxy[MyResource]"));
    }

    #[test]
    fn test_mixed_functions_and_instance() {
        let code = r#"
from pinjected import instance, injected

@instance
def db() -> Database:
    return Database()

@injected
def service(db, /):
    return Service(db)

class MyClass:
    pass

API_KEY = "secret"
"#;

        let violations = check_rule(code, "mymodule.py");

        assert_eq!(violations.len(), 1);
        assert!(violations[0].fix.is_some());
        let fix = violations[0].fix.as_ref().unwrap();
        
        // Check correct handling of different symbol types
        assert!(fix.content.contains("db: IProxy[Database]"));
        // Note: service is @injected, so it should have @overload and IProxy return type
        assert!(fix.content.contains("@overload"));
        assert!(fix.content.contains("def service() -> IProxy[Any]: ..."));
        assert!(fix.content.contains("class MyClass:"));
        assert!(fix.content.contains("API_KEY: Any"));
    }

    #[test]
    fn test_instance_without_return_type() {
        let code = r#"
from pinjected import instance

@instance
def resource():
    return MyResource()
"#;

        let violations = check_rule(code, "mymodule.py");

        assert_eq!(violations.len(), 1);
        assert!(violations[0].fix.is_some());
        let fix = violations[0].fix.as_ref().unwrap();
        // Should default to Any when no return type
        assert!(fix.content.contains("resource: IProxy[Any]"));
    }

    #[test]
    fn test_injected_function_stub_generation() {
        let code = r#"
from pinjected import injected
from typing import List

@injected
def get_users(db: Database, cache: Cache, /, page: int = 1) -> List[User]:
    return db.get_users(page)

@injected
async def process_data(logger, processor, /, data: str) -> str:
    await logger.log(f"Processing {data}")
    return await processor.process(data)

def regular_function(x: int) -> str:
    return str(x)
"#;

        let violations = check_rule(code, "mymodule.py");

        assert_eq!(violations.len(), 1);
        assert!(violations[0].fix.is_some());
        let fix = violations[0].fix.as_ref().unwrap();
        
        // Check that @injected functions have @overload and IProxy return types
        assert!(fix.content.contains("from typing import overload"));
        assert!(fix.content.contains("from pinjected import IProxy"));
        assert!(fix.content.contains("@overload\ndef get_users(page: int = ...) -> IProxy[List[User]]: ..."));
        assert!(fix.content.contains("@overload\nasync def process_data(data: str) -> IProxy[str]: ..."));
        
        // Regular function should still be normal
        assert!(fix.content.contains("def regular_function(x: int) -> str: ..."));
    }

    #[test]
    fn test_injected_with_existing_correct_stub() {
        let dir = tempdir().unwrap();
        let py_path = dir.path().join("mymodule.py");
        let pyi_path = dir.path().join("mymodule.pyi");

        let py_content = r#"
from pinjected import injected

@injected
def service(db, cache, /, user_id: str) -> str:
    return cache.get(user_id) or db.fetch(user_id)
"#;

        let pyi_content = r#"
from typing import overload
from pinjected import IProxy

@overload
def service(user_id: str) -> IProxy[str]: ...
"#;

        fs::write(&py_path, py_content).unwrap();
        fs::write(&pyi_path, pyi_content).unwrap();

        let rule = EnforcePyiStubsRule::new();
        let ast = parse(py_content, Mode::Module, py_path.to_str().unwrap()).unwrap();
        let context = RuleContext {
            stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass {
                range: rustpython_ast::text_size::TextRange::default(),
            }),
            file_path: py_path.to_str().unwrap(),
            source: py_content,
            ast: &ast,
        };

        let violations = rule.check(&context);
        
        // Should not have violations since stub is correct
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_mixed_instance_injected_functions() {
        let code = r#"
from pinjected import instance, injected

@instance
def database() -> Database:
    return Database()

@injected
def get_user(db: Database, /, user_id: str) -> User:
    return db.get_user(user_id)

@injected
async def save_user(db: Database, cache: Cache, /, user: User) -> None:
    await db.save(user)
    await cache.invalidate(user.id)

class UserService:
    pass
"#;

        let violations = check_rule(code, "mymodule.py");

        assert_eq!(violations.len(), 1);
        assert!(violations[0].fix.is_some());
        let fix = violations[0].fix.as_ref().unwrap();
        
        // Check imports include both overload and IProxy
        assert!(fix.content.contains("from typing import overload"));
        assert!(fix.content.contains("from pinjected import IProxy"));
        
        // @instance function as IProxy variable
        assert!(fix.content.contains("database: IProxy[Database]"));
        
        // @injected functions with @overload
        assert!(fix.content.contains("@overload\ndef get_user(user_id: str) -> IProxy[User]: ..."));
        assert!(fix.content.contains("@overload\nasync def save_user(user: User) -> IProxy[None]: ..."));
        
        // Class
        assert!(fix.content.contains("class UserService:"));
    }

    #[test]
    fn test_class_vs_instance_attributes_edge_cases() {
        let code = r#"
class ComplexClass:
    # Class attributes with complex types
    config: Dict[str, Any] = {"key": "value"}
    _private_class_var = 10  # Should be ignored (starts with _)
    
    def __init__(self, name: str):
        # Instance attributes in __init__
        self.name = name
        self._id = 123  # Private instance attribute
        self.data: List[str] = []
        
    @classmethod
    def from_dict(cls, data: dict):
        # Instance attributes in classmethod
        instance = cls("")
        instance.extra = data
        return instance
    
    def process(self):
        # Dynamic instance attributes
        self.processed = True
        self.result = self._compute()
        
    # Nested class
    class NestedConfig:
        timeout = 30
        retry_count = 3

# Edge case: assignment that looks like attribute access but isn't
some_obj.attribute = 10  # This should NOT be extracted as a symbol
"#;

        let violations = check_rule(code, "mymodule.py");

        assert_eq!(violations.len(), 1);
        assert!(violations[0].fix.is_some());
        let fix = violations[0].fix.as_ref().unwrap();
        
        
        // Should include class-level attributes
        assert!(fix.content.contains("class ComplexClass:"));
        assert!(fix.content.contains("config: Dict[str, Any]"));
        
        // Should now include private class attributes (changed behavior)
        assert!(fix.content.contains("_private_class_var"));
        
        // Should NOT include any instance attributes as class-level attributes
        // Note: "name" will appear as a parameter in __init__, but not as a class attribute
        assert!(!fix.content.contains("\n    name:"));  // Check for class-level attribute
        assert!(!fix.content.contains("_id"));
        assert!(!fix.content.contains("\n    data:"));  // data might appear in type hints
        assert!(!fix.content.contains("extra"));
        assert!(!fix.content.contains("processed"));
        assert!(!fix.content.contains("result"));
        
        // Should include nested class and its attributes
        assert!(fix.content.contains("class NestedConfig:"));
        assert!(fix.content.contains("timeout: Any"));
        assert!(fix.content.contains("retry_count: Any"));
        
        // Should NOT include the module-level attribute assignment
        assert!(!fix.content.contains("some_obj"));
        assert!(!fix.content.contains("attribute"));
    }

    #[test]
    fn test_exclude_pytest_files() {
        // Test that test_*.py files are excluded
        let rule = EnforcePyiStubsRule::new();
        
        // Test various pytest file patterns
        assert!(rule.should_exclude("test_example.py"));
        assert!(rule.should_exclude("test_module_functionality.py"));
        assert!(rule.should_exclude("/path/to/test_something.py"));
        assert!(rule.should_exclude("./test_utils.py"));
        
        // Test that non-test files are not excluded
        assert!(!rule.should_exclude("example.py"));
        assert!(!rule.should_exclude("my_test.py")); // doesn't start with test_
        assert!(!rule.should_exclude("testing.py")); // starts with test but not test_
        
        // Verify with actual rule check
        let code = r#"
def some_function():
    return "This is a test file"
"#;
        
        let violations = check_rule(code, "test_example.py");
        assert_eq!(violations.len(), 0, "test_*.py files should be excluded from stub checks");
        
        let violations = check_rule(code, "regular_module.py");
        assert_eq!(violations.len(), 1, "non-test files should require stubs");
    }

    #[test]
    fn test_class_vs_instance_attributes() {
        let code = r#"
class MLPlatformJobFromSchematics:
    # Class-level attributes (should be in stub)
    class_var: str = "hello"
    CLASS_CONSTANT = 42
    
    def __init__(self):
        # Instance attributes (should NOT be in stub)
        self.project = "my_project"
        self.schematics = {}
        self.data = []
    
    def setup(self):
        # Instance attributes set outside __init__ (should NOT be in stub)
        self.runtime_config = {}
        self.status = "ready"
    
    # Class-level without annotation (should be in stub)
    default_timeout = 300

# Module-level variable (should be in stub)
MODULE_CONFIG = {"debug": True}
"#;

        let violations = check_rule(code, "mymodule.py");

        assert_eq!(violations.len(), 1);
        assert!(violations[0].fix.is_some());
        let fix = violations[0].fix.as_ref().unwrap();
        
        println!("Generated stub content:
{}", fix.content);
        
        // Should include class-level attributes
        assert!(fix.content.contains("class MLPlatformJobFromSchematics:"));
        assert!(fix.content.contains("class_var: str"));
        assert!(fix.content.contains("CLASS_CONSTANT: Any"));
        assert!(fix.content.contains("default_timeout: Any"));
        
        // Should include module-level variable
        assert!(fix.content.contains("MODULE_CONFIG: Any"));
        
        // Should NOT include instance attributes
        assert!(!fix.content.contains("project"));
        assert!(!fix.content.contains("schematics"));
        assert!(!fix.content.contains("data"));
        assert!(!fix.content.contains("runtime_config"));
        assert!(!fix.content.contains("status"));
    }

    #[test]
    fn test_private_methods_required_in_stub() {
        let code = r#"
class MyClass:
    def public_method(self) -> str:
        return "public"
    
    def _private_method(self) -> int:
        return 42
    
    def __init__(self):
        pass

def public_function() -> None:
    pass

def _private_function() -> str:
    return "private"

_PRIVATE_VAR = 10
PUBLIC_VAR = 20
"#;

        let violations = check_rule(code, "test.py");
        
        // Should report missing stub file
        assert_eq!(violations.len(), 1, "Should detect missing stub file");
        
        let violation = &violations[0];
        assert!(violation.fix.is_some(), "Should provide a fix");
        
        let fix = violation.fix.as_ref().unwrap();
        println!("Generated stub content:
{}", fix.content);
        
        // Check that private methods are included with proper signatures
        assert!(fix.content.contains("def _private_method(self) -> int: ..."), 
                "Should include private method _private_method with signature");
        
        // Check that private functions are included
        assert!(fix.content.contains("def _private_function() -> str: ..."), 
                "Should include private function _private_function");
        
        // Check that private variables are included
        assert!(fix.content.contains("_PRIVATE_VAR: Any"), 
                "Should include private variable _PRIVATE_VAR");
        
        // Check that public symbols are still included
        assert!(fix.content.contains("def public_method(self) -> str: ..."));
        assert!(fix.content.contains("def public_function() -> None: ..."));
        assert!(fix.content.contains("PUBLIC_VAR: Any"));
    }
}
