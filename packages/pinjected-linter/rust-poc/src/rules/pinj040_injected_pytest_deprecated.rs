//! PINJ040: Deprecated @injected_pytest decorator
//!
//! The @injected_pytest decorator is deprecated in favor of the modern
//! pytest fixture integration using register_fixtures_from_design().

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct InjectedPytestDeprecatedRule;

impl InjectedPytestDeprecatedRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if an expression is an @injected_pytest decorator
    fn is_injected_pytest_decorator(&self, expr: &Expr) -> bool {
        match expr {
            Expr::Name(name) => name.id.as_str() == "injected_pytest",
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

    /// Create migration suggestion
    fn create_migration_message(&self, func_name: &str) -> String {
        format!(
            "The @injected_pytest decorator is deprecated and will be removed in a future version.\n\n\
            Quick migration:\n\
            1. Import: from pinjected.test import register_fixtures_from_design\n\
            2. Create design: test_design = design(service=service_func, database=database_func)\n\
            3. Register: register_fixtures_from_design(test_design)\n\
            4. Remove @injected_pytest from '{}' and use fixtures directly\n\n\
            Example:\n\
            # Before: @injected_pytest\\ndef test_something(service): ...\n\
            # After: def test_something(service): ...  # service available as pytest fixture\n\n\
            For detailed migration guide run: pinjected-linter --show-rule-doc PINJ040",
            func_name
        )
    }
}

impl LintRule for InjectedPytestDeprecatedRule {
    fn rule_id(&self) -> &str {
        "PINJ040"
    }

    fn description(&self) -> &str {
        "The @injected_pytest decorator is deprecated. Use register_fixtures_from_design() instead."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            // Check regular function definitions
            Stmt::FunctionDef(func) => {
                if self.has_injected_pytest_decorator(func) {
                    violations.push(Violation {
                        rule_id: "PINJ040".to_string(),
                        message: self.create_migration_message(&func.name),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Warning,
                        fix: None, // No auto-fix as requested
                    });
                }
            }
            // Check async function definitions
            Stmt::AsyncFunctionDef(func) => {
                if self.has_injected_pytest_decorator_async(func) {
                    violations.push(Violation {
                        rule_id: "PINJ040".to_string(),
                        message: self.create_migration_message(&func.name),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Warning,
                        fix: None, // No auto-fix as requested
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
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = InjectedPytestDeprecatedRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let context = RuleContext {
                        stmt,
                        file_path: "test.py",
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
    fn test_injected_pytest_deprecated() {
        let code = r#"
from pinjected.test_helpers import injected_pytest

@injected_pytest
def test_user_creation(user_service, database):
    user = user_service.create_user("test@example.com")
    assert user.id in database
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ040");
        assert!(violations[0].message.contains("deprecated"));
        assert!(violations[0].message.contains("register_fixtures_from_design"));
        assert!(violations[0].message.contains("test_user_creation"));
        assert!(violations[0].message.contains("Quick migration:"));
        assert!(violations[0].message.contains("Example:"));
        assert_eq!(violations[0].severity, Severity::Warning);
    }

    #[test]
    fn test_async_injected_pytest_deprecated() {
        let code = r#"
from pinjected.test_helpers import injected_pytest

@injected_pytest
async def test_async_operation(user_service):
    result = await user_service.async_method()
    assert result is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ040");
        assert!(violations[0].message.contains("deprecated"));
        assert!(violations[0].message.contains("Remove @injected_pytest"));
        assert!(violations[0].message.contains("test_async_operation"));
    }

    #[test]
    fn test_different_import_styles() {
        // Test different ways of importing injected_pytest
        let code1 = r#"
from pinjected import test_helpers

@test_helpers.injected_pytest
def test_something(service):
    assert service is not None
"#;
        let violations1 = check_code(code1);
        assert_eq!(violations1.len(), 1);

        let code2 = r#"
import pinjected.test_helpers

@pinjected.test_helpers.injected_pytest
def test_another(service):
    assert service is not None
"#;
        let violations2 = check_code(code2);
        assert_eq!(violations2.len(), 1);
    }

    #[test]
    fn test_no_violation_for_regular_pytest() {
        let code = r#"
import pytest
from pinjected import injected

@pytest.mark.asyncio
async def test_regular(user_service):
    # This should not trigger PINJ040
    result = await user_service.async_method()
    assert result is not None

@injected
def some_service():
    # Not a test, should not trigger
    return Service()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_multiple_decorators() {
        let code = r#"
from pinjected.test_helpers import injected_pytest
import pytest

@pytest.mark.slow
@injected_pytest
def test_with_multiple_decorators(service):
    # Should still detect @injected_pytest
    assert service.slow_operation() is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ040");
    }

    #[test]
    fn test_nested_functions_not_affected() {
        let code = r#"
def outer_function():
    from pinjected.test_helpers import injected_pytest
    
    # Inner function should not be checked
    @injected_pytest
    def inner_test(service):
        assert service is not None
"#;
        // Only top-level functions are checked by the linter
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}