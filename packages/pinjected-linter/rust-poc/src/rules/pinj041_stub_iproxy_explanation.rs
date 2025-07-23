//! PINJ041: Explain IProxy transformations in stub files
//!
//! This rule validates that .pyi stub files correctly show IProxy transformations
//! and provides educational explanations about WHY these transformations happen.
//!
//! - @instance functions: Should be typed as `name: IProxy[T]` in .pyi files
//! - @injected functions: Should use @overload with return type T (not IProxy[T])

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::{Expr, Mod, Stmt, StmtFunctionDef, StmtAsyncFunctionDef};
use rustpython_parser::{parse, Mode};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

pub struct StubIProxyExplanationRule {}

impl StubIProxyExplanationRule {
    pub fn new() -> Self {
        Self {}
    }

    /// Check if this is a stub file
    fn is_stub_file(&self, file_path: &str) -> bool {
        file_path.ends_with(".pyi")
    }

    /// Find corresponding .py file for a .pyi file
    fn find_python_file(&self, stub_path: &str) -> Option<PathBuf> {
        let path = Path::new(stub_path);
        let py_path = path.with_extension("py");
        if py_path.exists() {
            Some(py_path)
        } else {
            None
        }
    }

    /// Check if an expression represents IProxy type
    fn is_iproxy_type(&self, expr: &Expr) -> bool {
        match expr {
            Expr::Name(name) => name.id.as_str() == "IProxy",
            Expr::Attribute(attr) => {
                if let Expr::Name(name) = &*attr.value {
                    (name.id.as_str() == "pinjected" && attr.attr.as_str() == "IProxy") ||
                    (name.id.as_str() == "di" && attr.attr.as_str() == "IProxy")
                } else {
                    false
                }
            }
            // Handle generic types like IProxy[SomeType]
            Expr::Subscript(subscript) => self.is_iproxy_type(&subscript.value),
            _ => false,
        }
    }

    /// Extract the inner type from IProxy[T]
    fn extract_inner_type(&self, expr: &Expr) -> Option<String> {
        if let Expr::Subscript(subscript) = expr {
            if self.is_iproxy_type(&subscript.value) {
                return Some(self.format_type_annotation(&subscript.slice));
            }
        }
        None
    }

    /// Format type annotation as string
    fn format_type_annotation(&self, expr: &Expr) -> String {
        match expr {
            Expr::Name(name) => name.id.to_string(),
            Expr::Attribute(attr) => {
                let value = self.format_type_annotation(&attr.value);
                format!("{}.{}", value, attr.attr)
            }
            Expr::Subscript(subscript) => {
                let value = self.format_type_annotation(&subscript.value);
                let slice = self.format_type_annotation(&subscript.slice);
                format!("{}[{}]", value, slice)
            }
            Expr::Tuple(tuple) => {
                let elements: Vec<String> = tuple.elts.iter()
                    .map(|e| self.format_type_annotation(e))
                    .collect();
                elements.join(", ")
            }
            Expr::BinOp(binop) => {
                let left = self.format_type_annotation(&binop.left);
                let right = self.format_type_annotation(&binop.right);
                format!("{} | {}", left, right)
            }
            _ => "Any".to_string(),
        }
    }

    /// Analyze the Python source file to find @instance and @injected functions
    fn analyze_python_file(&self, py_path: &Path) -> Result<PythonAnalysis, String> {
        let content = fs::read_to_string(py_path)
            .map_err(|e| format!("Failed to read Python file: {}", e))?;
        
        let ast = parse(&content, Mode::Module, py_path.to_str().unwrap())
            .map_err(|e| format!("Failed to parse Python file: {}", e))?;
        
        let mut analysis = PythonAnalysis::new();
        
        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.analyze_stmt(stmt, &mut analysis);
                }
            }
            _ => {}
        }
        
        Ok(analysis)
    }

    /// Analyze a statement in the Python file
    fn analyze_stmt(&self, stmt: &Stmt, analysis: &mut PythonAnalysis) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if has_instance_decorator(func) {
                    let return_type = func.returns.as_ref()
                        .map(|r| self.format_type_annotation(r))
                        .unwrap_or_else(|| "Any".to_string());
                    analysis.instance_functions.insert(
                        func.name.to_string(),
                        InstanceInfo { return_type, is_async: false }
                    );
                } else if has_injected_decorator(func) {
                    let return_type = func.returns.as_ref()
                        .map(|r| self.format_type_annotation(r))
                        .unwrap_or_else(|| "Any".to_string());
                    analysis.injected_functions.insert(
                        func.name.to_string(),
                        InjectedInfo { return_type, is_async: false, has_slash: self.has_slash_separator(func) }
                    );
                }
                // Check nested functions
                for stmt in &func.body {
                    self.analyze_stmt(stmt, analysis);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_instance_decorator_async(func) {
                    let return_type = func.returns.as_ref()
                        .map(|r| self.format_type_annotation(r))
                        .unwrap_or_else(|| "Any".to_string());
                    analysis.instance_functions.insert(
                        func.name.to_string(),
                        InstanceInfo { return_type, is_async: true }
                    );
                } else if has_injected_decorator_async(func) {
                    let return_type = func.returns.as_ref()
                        .map(|r| self.format_type_annotation(r))
                        .unwrap_or_else(|| "Any".to_string());
                    analysis.injected_functions.insert(
                        func.name.to_string(),
                        InjectedInfo { return_type, is_async: true, has_slash: self.has_slash_separator_async(func) }
                    );
                }
                // Check nested functions
                for stmt in &func.body {
                    self.analyze_stmt(stmt, analysis);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.analyze_stmt(stmt, analysis);
                }
            }
            _ => {}
        }
    }

    /// Check if function has slash separator
    fn has_slash_separator(&self, func: &StmtFunctionDef) -> bool {
        !func.args.posonlyargs.is_empty()
    }

    /// Check if async function has slash separator
    fn has_slash_separator_async(&self, func: &StmtAsyncFunctionDef) -> bool {
        !func.args.posonlyargs.is_empty()
    }

    /// Check @instance declarations in stub file
    fn check_instance_stub(&self, name: &str, info: &InstanceInfo, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
            // Check for correct format: name: IProxy[T]
            Stmt::AnnAssign(ann_assign) => {
                if let Expr::Name(var_name) = &*ann_assign.target {
                    if var_name.id.as_str() == name {
                        if !self.is_iproxy_type(&ann_assign.annotation) {
                            violations.push(Violation {
                                rule_id: "PINJ041".to_string(),
                                message: format!(
                                    "@instance function '{}' should be typed as '{}: IProxy[{}]' in the .pyi file.\n\n\
                                    Why? The @instance decorator transforms your function into a dependency provider. \
                                    Instead of eagerly executing the function, pinjected wraps it as IProxy[{}] to enable \
                                    lazy evaluation and dependency injection at runtime. When you access this attribute, \
                                    pinjected will resolve all dependencies and return the actual {} instance.",
                                    name, name, info.return_type, info.return_type, info.return_type
                                ),
                                offset: ann_assign.range.start().to_usize(),
                                file_path: file_path.to_string(),
                                severity: Severity::Error,
                                fix: None,
                            });
                        } else {
                            // Check if the inner type matches
                            if let Some(inner_type) = self.extract_inner_type(&ann_assign.annotation) {
                                if inner_type != info.return_type {
                                    violations.push(Violation {
                                        rule_id: "PINJ041".to_string(),
                                        message: format!(
                                            "@instance function '{}' has incorrect type parameter. \
                                            Expected 'IProxy[{}]' but found 'IProxy[{}]'.\n\n\
                                            The type parameter should match the return type in your .py file.",
                                            name, info.return_type, inner_type
                                        ),
                                        offset: ann_assign.range.start().to_usize(),
                                        file_path: file_path.to_string(),
                                        severity: Severity::Error,
                                        fix: None,
                                    });
                                }
                            }
                        }
                        return;
                    }
                }
            }
            // Check for incorrect format: def name() -> T
            Stmt::FunctionDef(func) => {
                if func.name.as_str() == name {
                    violations.push(Violation {
                        rule_id: "PINJ041".to_string(),
                        message: format!(
                            "@instance function '{}' should not be declared as a function in the .pyi file. \
                            It should be a variable annotation: '{}: IProxy[{}]'.\n\n\
                            Why? @instance decorators transform functions into dependency providers that return \
                            IProxy objects. From the user's perspective, they access it as an attribute that \
                            provides an IProxy[{}], not as a callable function.",
                            name, name, info.return_type, info.return_type
                        ),
                        offset: func.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
            }
            _ => {}
        }
    }

    /// Check @injected declarations in stub file
    fn check_injected_stub(&self, name: &str, info: &InjectedInfo, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if func.name.as_str() == name {
                    // Check for @overload decorator
                    let has_overload = func.decorator_list.iter().any(|dec| {
                        if let Expr::Name(dec_name) = dec {
                            dec_name.id.as_str() == "overload"
                        } else {
                            false
                        }
                    });

                    if !has_overload {
                        violations.push(Violation {
                            rule_id: "PINJ041".to_string(),
                            message: format!(
                                "@injected function '{}' should have @overload decorator in the .pyi file.\n\n\
                                Why? @injected functions are transformed into IProxy[Callable] objects. \
                                The @overload decorator tells type checkers about the runtime signature \
                                that users will call.",
                                name
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }

                    // Check return type - should NOT be wrapped in IProxy
                    if let Some(returns) = &func.returns {
                        if self.is_iproxy_type(returns) {
                            violations.push(Violation {
                                rule_id: "PINJ041".to_string(),
                                message: format!(
                                    "@injected function '{}' should NOT have IProxy in its return type in the .pyi file. \
                                    It should return '{}' directly.\n\n\
                                    Why? While the @injected decorator makes the function itself an IProxy[Callable[[args], {}]], \
                                    the stub file shows the signature from the user's perspective. When they call the function \
                                    with runtime arguments, they get back {}, not IProxy[{}]. The IProxy wrapping happens \
                                    at the function level, not the return value level.",
                                    name, info.return_type, info.return_type, info.return_type, info.return_type
                                ),
                                offset: func.range.start().to_usize(),
                                file_path: file_path.to_string(),
                                severity: Severity::Error,
                                fix: None,
                            });
                        }
                    }
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if func.name.as_str() == name {
                    // Similar checks for async functions
                    let has_overload = func.decorator_list.iter().any(|dec| {
                        if let Expr::Name(dec_name) = dec {
                            dec_name.id.as_str() == "overload"
                        } else {
                            false
                        }
                    });

                    if !has_overload {
                        violations.push(Violation {
                            rule_id: "PINJ041".to_string(),
                            message: format!(
                                "@injected async function '{}' should have @overload decorator in the .pyi file.\n\n\
                                Why? @injected functions are transformed into IProxy[Callable] objects. \
                                The @overload decorator tells type checkers about the runtime signature \
                                that users will call.",
                                name
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }

                    // Check return type
                    if let Some(returns) = &func.returns {
                        if self.is_iproxy_type(returns) {
                            violations.push(Violation {
                                rule_id: "PINJ041".to_string(),
                                message: format!(
                                    "@injected async function '{}' should NOT have IProxy in its return type in the .pyi file. \
                                    It should return '{}' directly.\n\n\
                                    Why? The stub file represents the callable's signature after dependency injection. \
                                    Users call it with runtime args and await the result of type {}, not IProxy[{}].",
                                    name, info.return_type, info.return_type, info.return_type
                                ),
                                offset: func.range.start().to_usize(),
                                file_path: file_path.to_string(),
                                severity: Severity::Error,
                                fix: None,
                            });
                        }
                    }
                }
            }
            _ => {}
        }
    }

    /// Check a single statement in stub file
    fn check_stub_stmt(&self, stmt: &Stmt, analysis: &PythonAnalysis, file_path: &str, violations: &mut Vec<Violation>) {
        // First check @instance functions
        for (name, info) in &analysis.instance_functions {
            self.check_instance_stub(name, info, stmt, file_path, violations);
        }

        // Then check @injected functions
        for (name, info) in &analysis.injected_functions {
            self.check_injected_stub(name, info, stmt, file_path, violations);
        }

        // Recursively check nested statements
        match stmt {
            Stmt::FunctionDef(func) => {
                for stmt in &func.body {
                    self.check_stub_stmt(stmt, analysis, file_path, violations);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                for stmt in &func.body {
                    self.check_stub_stmt(stmt, analysis, file_path, violations);
                }
            }
            Stmt::ClassDef(class) => {
                for stmt in &class.body {
                    self.check_stub_stmt(stmt, analysis, file_path, violations);
                }
            }
            _ => {}
        }
    }
}

impl LintRule for StubIProxyExplanationRule {
    fn rule_id(&self) -> &str {
        "PINJ041"
    }

    fn description(&self) -> &str {
        "Explain IProxy transformations in .pyi stub files"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check .pyi files
        if !self.is_stub_file(context.file_path) {
            return violations;
        }

        // Find corresponding .py file
        let py_path = match self.find_python_file(context.file_path) {
            Some(path) => path,
            None => return violations, // No corresponding .py file
        };

        // Analyze the Python file
        let analysis = match self.analyze_python_file(&py_path) {
            Ok(analysis) => analysis,
            Err(_) => return violations, // Could not analyze Python file
        };

        // If no @instance or @injected functions, nothing to check
        if analysis.instance_functions.is_empty() && analysis.injected_functions.is_empty() {
            return violations;
        }

        // Check the stub file
        self.check_stub_stmt(context.stmt, &analysis, context.file_path, &mut violations);

        violations
    }
}

// Helper structures
#[derive(Debug)]
struct PythonAnalysis {
    instance_functions: HashMap<String, InstanceInfo>,
    injected_functions: HashMap<String, InjectedInfo>,
}

impl PythonAnalysis {
    fn new() -> Self {
        Self {
            instance_functions: HashMap::new(),
            injected_functions: HashMap::new(),
        }
    }
}

#[derive(Debug)]
struct InstanceInfo {
    return_type: String,
    is_async: bool,
}

#[derive(Debug)]
struct InjectedInfo {
    return_type: String,
    is_async: bool,
    has_slash: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_parser::{parse, Mode};
    use std::fs;
    use tempfile::TempDir;

    fn create_test_files(py_content: &str, pyi_content: &str) -> (TempDir, String, String) {
        let temp_dir = TempDir::new().unwrap();
        let py_path = temp_dir.path().join("test.py");
        let pyi_path = temp_dir.path().join("test.pyi");
        
        fs::write(&py_path, py_content).unwrap();
        fs::write(&pyi_path, pyi_content).unwrap();
        
        (temp_dir, py_path.to_str().unwrap().to_string(), pyi_path.to_str().unwrap().to_string())
    }

    fn check_stub_file(pyi_content: &str, pyi_path: &str) -> Vec<Violation> {
        let ast = parse(pyi_content, Mode::Module, pyi_path).unwrap();
        let rule = StubIProxyExplanationRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let context = RuleContext {
                        stmt,
                        file_path: pyi_path,
                        source: pyi_content,
                        ast: &ast,
                    };
                    violations.extend(rule.check(&context));
                }
            }
            _ => {}
        }

        violations
    }

    #[test]
    fn test_instance_correct_stub() {
        let py_content = r#"
from pinjected import instance

@instance
def database() -> Database:
    return PostgresDatabase()
"#;
        let pyi_content = r#"
from pinjected.di.iproxy import IProxy

database: IProxy[Database]
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_instance_missing_iproxy() {
        let py_content = r#"
from pinjected import instance

@instance
def database() -> Database:
    return PostgresDatabase()
"#;
        let pyi_content = r#"
database: Database  # Missing IProxy wrapper
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ041");
        assert!(violations[0].message.contains("should be typed as 'database: IProxy[Database]'"));
        assert!(violations[0].message.contains("lazy evaluation"));
    }

    #[test]
    fn test_instance_wrong_declaration() {
        let py_content = r#"
from pinjected import instance

@instance
def service() -> Service:
    return ServiceImpl()
"#;
        let pyi_content = r#"
def service() -> Service: ...  # Should be variable, not function
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ041");
        assert!(violations[0].message.contains("should not be declared as a function"));
        assert!(violations[0].message.contains("service: IProxy[Service]"));
    }

    #[test]
    fn test_injected_correct_stub() {
        let py_content = r#"
from pinjected import injected

@injected
def process(service, /, data: str) -> dict:
    return service.process(data)
"#;
        let pyi_content = r#"
from typing import overload

@overload
def process(data: str) -> dict: ...
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_with_iproxy_return() {
        let py_content = r#"
from pinjected import injected

@injected
def process(service, /, data: str) -> dict:
    return service.process(data)
"#;
        let pyi_content = r#"
from typing import overload
from pinjected.di.iproxy import IProxy

@overload
def process(data: str) -> IProxy[dict]: ...  # Wrong! Should be dict
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ041");
        assert!(violations[0].message.contains("should NOT have IProxy in its return type"));
        assert!(violations[0].message.contains("they get back dict, not IProxy[dict]"));
    }

    #[test]
    fn test_injected_missing_overload() {
        let py_content = r#"
from pinjected import injected

@injected
def fetch(api, /, user_id: str) -> User:
    return api.get_user(user_id)
"#;
        let pyi_content = r#"
def fetch(user_id: str) -> User: ...  # Missing @overload
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ041");
        assert!(violations[0].message.contains("should have @overload decorator"));
    }

    #[test]
    fn test_async_functions() {
        let py_content = r#"
from pinjected import instance, injected

@instance
async def async_db() -> AsyncDatabase:
    return await create_db()

@injected
async def a_fetch_data(db, /, query: str) -> list[dict]:
    return await db.query(query)
"#;
        let pyi_content = r#"
from typing import overload
from pinjected.di.iproxy import IProxy

async_db: IProxy[AsyncDatabase]

@overload
async def a_fetch_data(query: str) -> list[dict]: ...
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_complex_types() {
        let py_content = r#"
from pinjected import instance, injected

@instance
def config() -> dict[str, Any]:
    return {"key": "value"}

@injected
def process(service, /, items: list[str]) -> dict[str, list[int]]:
    return service.process_items(items)
"#;
        let pyi_content = r#"
from typing import overload, Any
from pinjected.di.iproxy import IProxy

config: IProxy[dict[str, Any]]

@overload
def process(items: list[str]) -> dict[str, list[int]]: ...
"#;
        let (_temp, _py_path, pyi_path) = create_test_files(py_content, pyi_content);
        let violations = check_stub_file(pyi_content, &pyi_path);
        assert_eq!(violations.len(), 0);
    }
}