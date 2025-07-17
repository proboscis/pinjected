//! PINJ036: Enforce .pyi stub files for all modules
//!
//! All Python modules should have corresponding .pyi stub files with complete
//! public API signatures for better IDE support and type checking.
//! Files starting with 'test' are excluded.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Arg, ArgWithDefault, Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
use rustpython_parser::parse;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq)]
struct PublicSymbol {
    name: String,
    kind: SymbolKind,
    signature: Option<String>,
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

                    let signature = self.generate_function_signature(func);
                    symbols.push(PublicSymbol {
                        name: full_name,
                        kind: SymbolKind::Function,
                        signature: Some(signature),
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

                    let signature = self.generate_async_function_signature(func);
                    symbols.push(PublicSymbol {
                        name: full_name,
                        kind: SymbolKind::AsyncFunction,
                        signature: Some(signature),
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

        // Return type
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str(&self.format_type_annotation(returns));
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

        // Return type
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str(&self.format_type_annotation(returns));
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
        let stub_names: HashSet<String> = stub_symbols.iter().map(|s| s.name.clone()).collect();

        module_symbols
            .iter()
            .filter(|s| !stub_names.contains(&s.name))
            .cloned()
            .collect()
    }

    /// Generate stub file content for missing symbols
    fn generate_stub_content(&self, missing_symbols: &[PublicSymbol]) -> String {
        let mut content = String::new();

        // Group symbols by type
        let mut functions = Vec::new();
        let mut classes = HashMap::new();
        let mut variables = Vec::new();

        for symbol in missing_symbols {
            match &symbol.kind {
                SymbolKind::Function | SymbolKind::AsyncFunction => {
                    if !symbol.name.contains('.') {
                        functions.push(symbol);
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

        // Generate functions
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

                            let stub_content = self.generate_stub_content(&missing);

                            let message = format!(
                                "Stub file exists but is missing the following public symbols:\n{}\n\nAdd these to {}:\n\n{}",
                                missing_names.join("\n"),
                                stub_path.display(),
                                stub_content
                            );

                            violations.push(Violation {
                                rule_id: self.rule_id().to_string(),
                                message,
                                offset: 0,
                                file_path: context.file_path.to_string(),
                                severity: Severity::Warning,
                            });
                        }
                    }
                    Err(e) => {
                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message: format!("Failed to parse stub file: {}", e),
                            offset: 0,
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                        });
                    }
                }
            }
        } else {
            // No stub file found
            let stub_path = Path::new(context.file_path).with_extension("pyi");
            let stub_content = self.generate_stub_content(&module_symbols);

            let message = format!(
                "Module has {} public symbol(s) but no .pyi stub file found.\n\nCreate {} with the following content:\n\n{}",
                module_symbols.len(),
                stub_path.display(),
                stub_content
            );

            violations.push(Violation {
                rule_id: self.rule_id().to_string(),
                message,
                offset: 0,
                file_path: context.file_path.to_string(),
                severity: Severity::Warning,
            });
        }

        violations
    }
}
