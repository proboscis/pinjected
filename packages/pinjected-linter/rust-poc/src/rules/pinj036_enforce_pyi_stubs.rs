//! PINJ036: Enforce .pyi stub files for all modules
//!
//! All Python modules should have corresponding .pyi stub files with complete
//! public API signatures for better IDE support and type checking.
//! Files starting with 'test' are excluded.

use crate::models::{Fix, RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_instance_decorator, has_instance_decorator_async, has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Arg, ArgWithDefault, Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
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

        // Check if filename starts with 'test'
        if let Some(file_name) = path.file_name() {
            let name = file_name.to_str().unwrap_or("");
            if name.starts_with("test") {
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

    /// Extract public symbols from a statement
    fn extract_from_stmt(&self, stmt: &Stmt, symbols: &mut Vec<PublicSymbol>, prefix: &str) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if !func.name.as_str().starts_with('_') || func.name.as_str() == "__init__" {
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
                if !func.name.as_str().starts_with('_') {
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
                if !class.name.as_str().starts_with('_') {
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

                    // Extract public methods from the class
                    for stmt in &class.body {
                        self.extract_from_stmt(stmt, symbols, &full_name);
                    }
                }
            }
            Stmt::Assign(assign) => {
                // Extract module-level variable assignments
                for target in &assign.targets {
                    if let Expr::Name(name) = target {
                        if !name.id.as_str().starts_with('_') {
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
                    if !name.id.as_str().starts_with('_') {
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

        // Build the result
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
                    if !symbol.name.contains('.') {
                        classes.insert(symbol.name.clone(), Vec::new());
                    }
                }
                SymbolKind::Variable => {
                    if !symbol.name.contains('.') {
                        variables.push(symbol);
                    }
                }
            }
        }

        // Collect class methods
        for symbol in missing_symbols {
            if let Some(dot_pos) = symbol.name.find('.') {
                let class_name = &symbol.name[..dot_pos];
                if let Some(methods) = classes.get_mut(class_name) {
                    methods.push(symbol);
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

        // Generate classes
        for (class_name, methods) in &classes {
            content.push_str(&format!("class {}:\n", class_name));

            if methods.is_empty() {
                content.push_str("    ...\n");
            } else {
                for method in methods {
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
}
