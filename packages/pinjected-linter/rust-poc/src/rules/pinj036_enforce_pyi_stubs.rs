//! PINJ036: Enforce .pyi stub files for all modules
//!
//! All Python modules should have corresponding .pyi stub files with complete
//! public API signatures for better IDE support and type checking.
//! Files starting with 'test' are excluded.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_instance_decorator, has_instance_decorator_async};
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
    has_instance_decorator: bool,
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
                    let return_type = func.returns.as_ref().map(|r| self.format_type_annotation(r));
                    let signature = self.generate_function_signature(func);
                    
                    symbols.push(PublicSymbol {
                        name: full_name,
                        kind: SymbolKind::Function,
                        signature: Some(signature),
                        has_instance_decorator: has_instance,
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
                    let return_type = func.returns.as_ref().map(|r| self.format_type_annotation(r));
                    let signature = self.generate_async_function_signature(func);
                    
                    symbols.push(PublicSymbol {
                        name: full_name,
                        kind: SymbolKind::AsyncFunction,
                        signature: Some(signature),
                        has_instance_decorator: has_instance,
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
            .filter(|module_sym| {
                // For @instance functions, they should be present as variables in stub
                if module_sym.has_instance_decorator {
                    // Check if it exists as a variable in stub
                    !stub_symbols.iter().any(|stub_sym| {
                        stub_sym.name == module_sym.name && matches!(stub_sym.kind, SymbolKind::Variable)
                    })
                } else {
                    // For other symbols, just check if name exists
                    !stub_names.contains(&module_sym.name)
                }
            })
            .cloned()
            .collect()
    }

    /// Generate stub file content for missing symbols
    fn generate_stub_content(&self, missing_symbols: &[PublicSymbol]) -> String {
        let mut content = String::new();

        // Group symbols by type
        let mut functions = Vec::new();
        let mut instance_functions = Vec::new();
        let mut classes = HashMap::new();
        let mut variables = Vec::new();

        for symbol in missing_symbols {
            match &symbol.kind {
                SymbolKind::Function | SymbolKind::AsyncFunction => {
                    if !symbol.name.contains('.') {
                        if symbol.has_instance_decorator {
                            instance_functions.push(symbol);
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

        // Add imports if we have @instance functions
        if !instance_functions.is_empty() {
            content.push_str("from pinjected import IProxy\n");
            content.push_str("from typing import Any\n\n");
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
                                fix: None,
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
                fix: None,
            });
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
        
        // Check that the generated stub content includes IProxy declarations
        println!("Violation message: {}", violation.message);
        assert!(violation.message.contains("from pinjected import IProxy"));
        assert!(violation.message.contains("database: IProxy[DatabaseConnection]"));
        assert!(violation.message.contains("cache_service: IProxy[CacheService]"));
        assert!(violation.message.contains("config: IProxy[Dict[str, str]]"));
        
        // Regular function should still be a function
        assert!(violation.message.contains("def regular_function() -> str: ..."));
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
        assert!(violations[0].message.contains("resource: IProxy[MyResource]"));
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
        let msg = &violations[0].message;
        
        // Check correct handling of different symbol types
        assert!(msg.contains("db: IProxy[Database]"));
        assert!(msg.contains("def service(db, /) -> Any: ..."));
        assert!(msg.contains("class MyClass:"));
        assert!(msg.contains("API_KEY: Any"));
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
        // Should default to Any when no return type
        assert!(violations[0].message.contains("resource: IProxy[Any]"));
    }
}
