//! PINJ043: No design() usage inside test functions
//!
//! The design() context manager should not be used inside test functions.
//! design() should be created at module level and converted to fixtures using register_fixtures_from_design().

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Stmt, StmtAsyncFunctionDef, StmtAsyncWith, StmtFunctionDef, StmtWith};

pub struct NoDesignInTestFunctionsRule {
    in_test_function: Vec<String>,
}

impl NoDesignInTestFunctionsRule {
    pub fn new() -> Self {
        Self {
            in_test_function: Vec::new(),
        }
    }

    /// Check if a function is a test function (starts with "test_" or has pytest decorators)
    fn is_test_function(func_name: &str, decorator_list: &[Expr]) -> bool {
        // Check if function name starts with "test_"
        if func_name.starts_with("test_") {
            return true;
        }

        // Check for pytest decorators
        for decorator in decorator_list {
            if Self::is_pytest_decorator(decorator) {
                return true;
            }
        }

        false
    }

    /// Check if an expression is a pytest decorator that makes a function a test
    fn is_pytest_decorator(expr: &Expr) -> bool {
        match expr {
            Expr::Attribute(attr) => {
                // Check for pytest.mark.* decorators
                if let Expr::Attribute(inner_attr) = &*attr.value {
                    if let Expr::Name(name) = &*inner_attr.value {
                        return name.id.as_str() == "pytest" && inner_attr.attr.as_str() == "mark";
                    }
                }
                // Check for direct pytest.* decorators
                if let Expr::Name(name) = &*attr.value {
                    return name.id.as_str() == "pytest";
                }
                false
            }
            _ => false,
        }
    }

    /// Check if an expression is a call to design()
    fn is_design_call(expr: &Expr) -> bool {
        match expr {
            Expr::Call(call) => match &*call.func {
                Expr::Name(name) => name.id.as_str() == "design",
                Expr::Attribute(attr) => {
                    if attr.attr.as_str() == "design" {
                        if let Expr::Name(module) = &*attr.value {
                            return module.id.as_str() == "pinjected";
                        }
                    }
                    false
                }
                _ => false,
            },
            _ => false,
        }
    }

    /// Check a with statement for design() usage
    fn check_with_statement(&self, with_stmt: &StmtWith, parent_name: &str) -> Option<Violation> {
        if self.in_test_function.is_empty() {
            return None;
        }

        for item in &with_stmt.items {
            if Self::is_design_call(&item.context_expr) {
                return Some(Violation {
                    rule_id: "PINJ043".to_string(),
                    message: format!(
                        "design() cannot be used inside test function '{}'. \
                        The 'with design()' context manager only works for IProxy entrypoint declarations, not for test dependency resolution.\n\n\
                        Use register_fixtures_from_design() instead (recommended):\n\
                        # At module level:\n\
                        test_design = design(\n\
                        ⠀⠀⠀⠀my_service=MyService(),\n\
                        ⠀⠀⠀⠀database=MockDatabase()\n\
                        )\n\
                        register_fixtures_from_design(test_design)\n\n\
                        # In test function:\n\
                        def test_something(my_service, database):  # Injected as fixtures\n\
                        ⠀⠀⠀⠀result = my_service.method()\n\
                        ⠀⠀⠀⠀assert result == expected",
                        parent_name
                    ),
                    offset: with_stmt.range.start().to_usize(),
                    file_path: String::new(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
        None
    }

    /// Check an async with statement for design() usage
    fn check_async_with_statement(
        &self,
        with_stmt: &StmtAsyncWith,
        parent_name: &str,
    ) -> Option<Violation> {
        if self.in_test_function.is_empty() {
            return None;
        }

        for item in &with_stmt.items {
            if Self::is_design_call(&item.context_expr) {
                return Some(Violation {
                    rule_id: "PINJ043".to_string(),
                    message: format!(
                        "design() cannot be used inside test function '{}'. \
                        The 'async with design()' pattern is not supported for test dependency resolution.\n\n\
                        Use register_fixtures_from_design() instead (recommended):\n\
                        # At module level:\n\
                        test_design = design(\n\
                        ⠀⠀⠀⠀async_service=AsyncService(),\n\
                        ⠀⠀⠀⠀database=MockDatabase()\n\
                        )\n\
                        register_fixtures_from_design(test_design)\n\n\
                        # In test function:\n\
                        @pytest.mark.asyncio\n\
                        async def test_something(async_service, database):  # Injected as fixtures\n\
                        ⠀⠀⠀⠀result = await async_service.async_method()\n\
                        ⠀⠀⠀⠀assert result == expected",
                        parent_name
                    ),
                    offset: with_stmt.range.start().to_usize(),
                    file_path: String::new(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
        None
    }

    /// Check a function body for design() usage
    fn check_function_body(&mut self, body: &[Stmt], func_name: &str) -> Vec<Violation> {
        let mut violations = Vec::new();

        // We're now inside a test function
        self.in_test_function.push(func_name.to_string());

        for stmt in body {
            match stmt {
                Stmt::With(with_stmt) => {
                    if let Some(violation) = self.check_with_statement(with_stmt, func_name) {
                        violations.push(violation);
                    }
                    // Recursively check the body
                    violations.extend(self.check_function_body(&with_stmt.body, func_name));
                }
                Stmt::AsyncWith(with_stmt) => {
                    if let Some(violation) = self.check_async_with_statement(with_stmt, func_name) {
                        violations.push(violation);
                    }
                    // Recursively check the body
                    violations.extend(self.check_function_body(&with_stmt.body, func_name));
                }
                Stmt::FunctionDef(func) => {
                    // If we're already in a test function, check all nested functions
                    violations.extend(self.check_function_body(&func.body, func.name.as_str()));
                }
                Stmt::AsyncFunctionDef(func) => {
                    // If we're already in a test function, check all nested functions
                    violations.extend(self.check_function_body(&func.body, func.name.as_str()));
                }
                Stmt::ClassDef(cls) => {
                    // Check methods inside test classes
                    violations.extend(
                        self.check_function_body(&cls.body, &format!("{}.{}", func_name, cls.name)),
                    );
                }
                Stmt::If(if_stmt) => {
                    violations.extend(self.check_function_body(&if_stmt.body, func_name));
                    violations.extend(self.check_function_body(&if_stmt.orelse, func_name));
                }
                Stmt::While(while_stmt) => {
                    violations.extend(self.check_function_body(&while_stmt.body, func_name));
                    violations.extend(self.check_function_body(&while_stmt.orelse, func_name));
                }
                Stmt::For(for_stmt) => {
                    violations.extend(self.check_function_body(&for_stmt.body, func_name));
                    violations.extend(self.check_function_body(&for_stmt.orelse, func_name));
                }
                Stmt::Try(try_stmt) => {
                    violations.extend(self.check_function_body(&try_stmt.body, func_name));
                    for handler in &try_stmt.handlers {
                        let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler;
                        violations.extend(self.check_function_body(&h.body, func_name));
                    }
                    violations.extend(self.check_function_body(&try_stmt.orelse, func_name));
                    violations.extend(self.check_function_body(&try_stmt.finalbody, func_name));
                }
                _ => {}
            }
        }

        // We're leaving this function
        self.in_test_function.pop();

        violations
    }

    /// Check a regular function definition
    fn check_function(&mut self, func: &StmtFunctionDef) -> Vec<Violation> {
        if Self::is_test_function(func.name.as_str(), &func.decorator_list) {
            self.check_function_body(&func.body, func.name.as_str())
        } else {
            Vec::new()
        }
    }

    /// Check an async function definition
    fn check_async_function(&mut self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        if Self::is_test_function(func.name.as_str(), &func.decorator_list) {
            self.check_function_body(&func.body, func.name.as_str())
        } else {
            Vec::new()
        }
    }
}

impl LintRule for NoDesignInTestFunctionsRule {
    fn rule_id(&self) -> &str {
        "PINJ043"
    }

    fn description(&self) -> &str {
        "design() cannot be used inside test functions. The 'with design()' pattern only works for IProxy entrypoints. Use register_fixtures_from_design() instead."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut rule = NoDesignInTestFunctionsRule::new();
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                let mut func_violations = rule.check_function(func);
                for violation in &mut func_violations {
                    violation.file_path = context.file_path.to_string();
                }
                violations.extend(func_violations);
            }
            Stmt::AsyncFunctionDef(func) => {
                let mut func_violations = rule.check_async_function(func);
                for violation in &mut func_violations {
                    violation.file_path = context.file_path.to_string();
                }
                violations.extend(func_violations);
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
        let rule = NoDesignInTestFunctionsRule::new();
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
    fn test_design_in_test_function() {
        let code = r#"
from pinjected import design

def test_user_creation():
    with design() as d:
        d.provide(user_service)
        d.provide(database)
    
    user = user_service.create_user("test@example.com")
    assert user.id in database
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ043");
        assert!(violations[0].message.contains("test_user_creation"));
        assert!(violations[0].message.contains("register_fixtures_from_design"));
    }

    #[test]
    fn test_design_in_async_test() {
        let code = r#"
from pinjected import design
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    async with design() as d:
        d.provide(async_service)
    
    result = await async_service.do_something()
    assert result is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ043");
        assert!(violations[0].message.contains("test_async_operation"));
    }

    #[test]
    fn test_design_with_pytest_decorator() {
        let code = r#"
import pytest
from pinjected import design

@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized(value):
    with design() as d:
        d.provide(service)
    
    assert service.process(value) > 0
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ043");
        assert!(violations[0].message.contains("test_parametrized"));
    }

    #[test]
    fn test_design_outside_test_function() {
        let code = r#"
from pinjected import design
from pinjected.test import register_fixtures_from_design

# Create design at module level
test_design = design()
test_design.provide(user_service)
test_design.provide(database)

# Register as pytest fixtures
register_fixtures_from_design(test_design)

def test_user_creation(user_service, database):
    # Now user_service and database are available as fixtures
    user = user_service.create_user("test@example.com")
    assert user.id in database

def helper_function():
    # Helper functions can use design()
    with design() as d:
        d.provide(something)
    return d
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_design_in_nested_function() {
        let code = r#"
from pinjected import design

def test_complex_scenario():
    def setup_test_data():
        with design() as d:
            d.provide(test_data_service)
        return d
    
    # This should still be detected
    setup_test_data()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ043");
    }

    #[test]
    fn test_design_in_conditional() {
        let code = r#"
from pinjected import design
import pytest

@pytest.mark.skipif(True, reason="Skip")
def test_conditional_design():
    if some_condition:
        with design() as d:
            d.provide(mock_service)
    else:
        with design() as d:
            d.provide(real_service)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ043"));
    }

    #[test]
    fn test_pinjected_module_design() {
        let code = r#"
import pinjected

def test_with_module_import():
    with pinjected.design() as d:
        d.provide(service)
    
    assert service is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ043");
    }

    #[test]
    fn test_non_test_function_not_checked() {
        let code = r#"
from pinjected import design

def setup_application():
    # This is not a test function, so design() is allowed
    with design() as d:
        d.provide(app_service)
        d.provide(database)
    return d

def create_test_data():
    # Also not a test function
    with design() as d:
        d.provide(test_data)
    return d
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}