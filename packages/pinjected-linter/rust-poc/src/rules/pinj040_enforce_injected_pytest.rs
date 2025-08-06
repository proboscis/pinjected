//! PINJ040: Enforce @injected_pytest decorator in pytest files
//!
//! The @injected_pytest decorator should be used in pytest test files
//! instead of register_fixtures_from_design().

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, ExprCall, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct EnforceInjectedPytestRule;

impl EnforceInjectedPytestRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if an expression is an @injected_pytest decorator
    fn is_injected_pytest_decorator(&self, expr: &Expr) -> bool {
        match expr {
            Expr::Name(name) => name.id.as_str() == "injected_pytest",
            Expr::Call(call) => {
                // Check if the function being called is injected_pytest
                // This handles @injected_pytest() and @injected_pytest(__design__)
                self.is_injected_pytest_decorator(&call.func)
            }
            Expr::Attribute(attr) => {
                // Check for pinjected.test_helpers.injected_pytest
                if let Expr::Attribute(inner_attr) = &*attr.value {
                    if let Expr::Name(name) = &*inner_attr.value {
                        return name.id.as_str() == "pinjected"
                            && inner_attr.attr.as_str() == "test_helpers"
                            && attr.attr.as_str() == "injected_pytest";
                    }
                }
                // Check for test_helpers.injected_pytest
                if let Expr::Name(name) = &*attr.value {
                    return name.id.as_str() == "test_helpers"
                        && attr.attr.as_str() == "injected_pytest";
                }
                false
            }
            _ => false,
        }
    }

    /// Check if a function has @injected_pytest decorator
    fn has_injected_pytest_decorator(&self, func: &StmtFunctionDef) -> bool {
        func.decorator_list
            .iter()
            .any(|d| self.is_injected_pytest_decorator(d))
    }

    /// Check if an async function has @injected_pytest decorator
    fn has_injected_pytest_decorator_async(&self, func: &StmtAsyncFunctionDef) -> bool {
        func.decorator_list
            .iter()
            .any(|d| self.is_injected_pytest_decorator(d))
    }

    /// Check if the function is a pytest test function
    fn is_pytest_test_function(&self, func_name: &str) -> bool {
        func_name.starts_with("test_")
    }

    /// Create suggestion message
    fn create_suggestion_message(&self, func_name: &str) -> String {
        format!(
            "Test function '{}' should use @injected_pytest decorator to properly handle dependency injection in pytest. Add @injected_pytest decorator before the function definition. Example: from pinjected.test_helpers import injected_pytest; @injected_pytest def {}(...): ...",
            func_name, func_name
        )
    }
}

impl LintRule for EnforceInjectedPytestRule {
    fn rule_id(&self) -> &str {
        "PINJ040"
    }

    fn description(&self) -> &str {
        "Test functions in pytest files should use @injected_pytest decorator for proper dependency injection."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            // Check regular function definitions
            Stmt::FunctionDef(func) => {
                // Only check test functions in test files
                if self.is_pytest_test_function(&func.name) && 
                   (context.file_path.contains("test_") || context.file_path.contains("_test.py")) &&
                   !self.has_injected_pytest_decorator(func) {
                    violations.push(Violation {
                        rule_id: "PINJ040".to_string(),
                        message: self.create_suggestion_message(&func.name),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
            }
            // Check async function definitions
            Stmt::AsyncFunctionDef(func) => {
                // Only check test functions in test files
                if self.is_pytest_test_function(&func.name) && 
                   (context.file_path.contains("test_") || context.file_path.contains("_test.py")) &&
                   !self.has_injected_pytest_decorator_async(func) {
                    violations.push(Violation {
                        rule_id: "PINJ040".to_string(),
                        message: self.create_suggestion_message(&func.name),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
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
        let ast = parse(code, Mode::Module, "test_example.py").unwrap();
        let rule = EnforceInjectedPytestRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let context = RuleContext {
                        stmt,
                        file_path: "test_example.py",
                        source: code,
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
    fn test_missing_injected_pytest() {
        let code = r#"
from pinjected import injected

def test_user_creation(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ040");
        assert!(violations[0].message.contains("should use @injected_pytest"));
        assert!(violations[0].message.contains("test_user_creation"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_async_missing_injected_pytest() {
        let code = r#"
import pytest

@pytest.mark.asyncio
async def test_async_operation(user_service):
    result = await user_service.async_method()
    assert result is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ040");
        assert!(violations[0].message.contains("should use @injected_pytest"));
        assert!(violations[0].message.contains("test_async_operation"));
    }

    #[test]
    fn test_with_injected_pytest_no_violation() {
        // Test that having @injected_pytest doesn't trigger violation
        let code1 = r#"
from pinjected.test_helpers import injected_pytest

@injected_pytest
def test_something(service):
    assert service is not None
"#;
        let violations1 = check_code(code1);
        assert_eq!(violations1.len(), 0);

        let code2 = r#"
import pinjected.test_helpers

@pinjected.test_helpers.injected_pytest
def test_another(service):
    assert service is not None
"#;
        let violations2 = check_code(code2);
        assert_eq!(violations2.len(), 0);
    }

    #[test]
    fn test_no_violation_for_non_test_functions() {
        let code = r#"
from pinjected import injected

@injected
def some_service():
    # Not a test, should not trigger
    return Service()

def helper_function():
    # Not a test function
    return None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_multiple_decorators_with_injected_pytest() {
        let code = r#"
from pinjected.test_helpers import injected_pytest
import pytest

@pytest.mark.slow
@injected_pytest
def test_with_multiple_decorators(service):
    # Has @injected_pytest, should not trigger
    assert service.slow_operation() is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_functions_not_affected() {
        let code = r#"
def outer_function():
    # Inner function should not be checked
    def test_inner(service):
        assert service is not None
"#;
        // Only top-level functions are checked by the linter
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_multiple_test_functions_missing_decorator() {
        let code = r#"
import pytest

def test_first():
    pass

def test_second(service):
    assert service is not None

@pytest.mark.skip
def test_third(database):
    assert database is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ040"));
    }
}