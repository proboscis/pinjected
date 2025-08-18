//! PINJ058: Missing return type annotation
//!
//! Functions and methods should have return type annotations for better type safety.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{StmtAsyncFunctionDef, StmtFunctionDef};

pub struct MissingReturnTypeAnnotationRule;

impl MissingReturnTypeAnnotationRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a function should be skipped (special methods with implicit returns)
    fn should_skip_function(name: &str, is_method: bool) -> bool {
        if !is_method {
            return false;
        }

        // Special methods that have implicit return types
        matches!(
            name,
            "__init__" | "__new__" | "__del__" | "__enter__" | "__exit__" | 
            "__aenter__" | "__aexit__" | "__setattr__" | "__delattr__" |
            "__setitem__" | "__delitem__" | "__set__" | "__delete__" |
            "__set_name__"
        )
    }

    /// Check if this is a method (has self/cls as first parameter)
    fn is_method(func: &StmtFunctionDef) -> bool {
        if let Some(first_arg) = func.args.args.first() {
            let arg_name = first_arg.def.arg.as_str();
            return arg_name == "self" || arg_name == "cls";
        }
        if let Some(first_arg) = func.args.posonlyargs.first() {
            let arg_name = first_arg.def.arg.as_str();
            return arg_name == "self" || arg_name == "cls";
        }
        false
    }

    /// Check if this is an async method
    fn is_async_method(func: &StmtAsyncFunctionDef) -> bool {
        if let Some(first_arg) = func.args.args.first() {
            let arg_name = first_arg.def.arg.as_str();
            return arg_name == "self" || arg_name == "cls";
        }
        if let Some(first_arg) = func.args.posonlyargs.first() {
            let arg_name = first_arg.def.arg.as_str();
            return arg_name == "self" || arg_name == "cls";
        }
        false
    }

    /// Check a function definition
    fn check_function(&self, func: &StmtFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        let is_method = Self::is_method(func);
        if Self::should_skip_function(func.name.as_str(), is_method) {
            return violations;
        }

        if func.returns.is_none() {
            let func_type = if is_method { "Method" } else { "Function" };
            let message = format!(
                "{} '{}' is missing a return type annotation. Add -> ReturnType for better type safety.",
                func_type,
                func.name.as_str()
            );

            violations.push(Violation {
                rule_id: "PINJ058".to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
                fix: None,
            });
        }

        violations
    }

    /// Check an async function definition
    fn check_async_function(&self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        let is_method = Self::is_async_method(func);
        if Self::should_skip_function(func.name.as_str(), is_method) {
            return violations;
        }

        if func.returns.is_none() {
            let func_type = if is_method { "Async method" } else { "Async function" };
            let message = format!(
                "{} '{}' is missing a return type annotation. Add -> ReturnType for better type safety.",
                func_type,
                func.name.as_str()
            );

            violations.push(Violation {
                rule_id: "PINJ058".to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
                fix: None,
            });
        }

        violations
    }
}

impl LintRule for MissingReturnTypeAnnotationRule {
    fn rule_id(&self) -> &str {
        "PINJ058"
    }

    fn description(&self) -> &str {
        "Functions and methods should have return type annotations"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            rustpython_ast::Stmt::FunctionDef(func) => {
                for mut violation in self.check_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            rustpython_ast::Stmt::AsyncFunctionDef(func) => {
                for mut violation in self.check_async_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            _ => {}
        }

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_ast::Mod;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = MissingReturnTypeAnnotationRule::new();
        let mut violations = Vec::new();

        fn check_stmts(
            stmts: &[rustpython_ast::Stmt],
            rule: &MissingReturnTypeAnnotationRule,
            violations: &mut Vec<Violation>,
            code: &str,
            ast: &Mod,
        ) {
            for stmt in stmts {
                let context = RuleContext {
                    stmt,
                    file_path: "test.py",
                    source: code,
                    ast,
                };
                violations.extend(rule.check(&context));

                // Check nested statements (e.g., methods in classes)
                match stmt {
                    rustpython_ast::Stmt::ClassDef(class) => {
                        check_stmts(&class.body, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::FunctionDef(func) => {
                        check_stmts(&func.body, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::AsyncFunctionDef(func) => {
                        check_stmts(&func.body, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::If(if_stmt) => {
                        check_stmts(&if_stmt.body, rule, violations, code, ast);
                        check_stmts(&if_stmt.orelse, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::With(with_stmt) => {
                        check_stmts(&with_stmt.body, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::AsyncWith(with_stmt) => {
                        check_stmts(&with_stmt.body, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::For(for_stmt) => {
                        check_stmts(&for_stmt.body, rule, violations, code, ast);
                        check_stmts(&for_stmt.orelse, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::AsyncFor(for_stmt) => {
                        check_stmts(&for_stmt.body, rule, violations, code, ast);
                        check_stmts(&for_stmt.orelse, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::While(while_stmt) => {
                        check_stmts(&while_stmt.body, rule, violations, code, ast);
                        check_stmts(&while_stmt.orelse, rule, violations, code, ast);
                    }
                    rustpython_ast::Stmt::Try(try_stmt) => {
                        check_stmts(&try_stmt.body, rule, violations, code, ast);
                        for handler in &try_stmt.handlers {
                            let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler;
                            check_stmts(&h.body, rule, violations, code, ast);
                        }
                        check_stmts(&try_stmt.orelse, rule, violations, code, ast);
                        check_stmts(&try_stmt.finalbody, rule, violations, code, ast);
                    }
                    _ => {}
                }
            }
        }

        match &ast {
            Mod::Module(module) => {
                check_stmts(&module.body, &rule, &mut violations, code, &ast);
            }
            _ => {}
        }

        violations
    }

    #[test]
    fn test_function_without_return_type() {
        let code = r#"
def add(a: int, b: int):
    return a + b
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ058");
        assert!(violations[0].message.contains("Function 'add'"));
    }

    #[test]
    fn test_function_with_return_type() {
        let code = r#"
def add(a: int, b: int) -> int:
    return a + b
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_method_without_return_type() {
        let code = r#"
class Calculator:
    def add(self, a: int, b: int):
        return a + b
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ058");
        assert!(violations[0].message.contains("Method 'add'"));
    }

    #[test]
    fn test_method_with_return_type() {
        let code = r#"
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_init_method_skipped() {
        let code = r#"
class MyClass:
    def __init__(self, value: int):
        self.value = value
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_special_methods_skipped() {
        let code = r#"
class MyClass:
    def __init__(self):
        pass
    
    def __del__(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_async_function_without_return_type() {
        let code = r#"
async def fetch_data(url: str):
    return await client.get(url)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ058");
        assert!(violations[0].message.contains("Async function 'fetch_data'"));
    }

    #[test]
    fn test_async_function_with_return_type() {
        let code = r#"
async def fetch_data(url: str) -> dict:
    return await client.get(url)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_async_method_without_return_type() {
        let code = r#"
class DataFetcher:
    async def fetch(self, url: str):
        return await self.client.get(url)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ058");
        assert!(violations[0].message.contains("Async method 'fetch'"));
    }

    #[test]
    fn test_classmethod_without_return_type() {
        let code = r#"
class Factory:
    @classmethod
    def create(cls, name: str):
        return cls(name)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ058");
        assert!(violations[0].message.contains("Method 'create'"));
    }

    #[test]
    fn test_staticmethod_without_return_type() {
        let code = r#"
class Utils:
    @staticmethod
    def process(data: str):
        return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ058");
        assert!(violations[0].message.contains("Function 'process'"));
    }

    #[test]
    fn test_lambda_ignored() {
        let code = r#"
compute = lambda x: x * 2
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_function_without_return_type() {
        let code = r#"
def outer() -> int:
    def inner(x: int):
        return x * 2
    return inner(5)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ058");
        assert!(violations[0].message.contains("Function 'inner'"));
    }
}