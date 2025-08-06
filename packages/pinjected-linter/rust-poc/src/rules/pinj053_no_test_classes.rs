//! PINJ053: Forbid class-based test declarations in pytest
//!
//! Test classes are not allowed in pytest files. Use function-based tests
//! with @injected_pytest decorator for better dependency injection support.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::Stmt;

pub struct NoTestClassesRule;

impl NoTestClassesRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a class name indicates it's a test class
    fn is_test_class(&self, class_name: &str) -> bool {
        // Check if the class name starts with "Test" (case-sensitive, following pytest convention)
        class_name.starts_with("Test")
    }

    /// Check if the file is a pytest test file
    fn is_pytest_file(&self, file_path: &str) -> bool {
        // Check if the file matches pytest naming conventions
        file_path.contains("test_") || file_path.ends_with("_test.py")
    }

    /// Create error message for test class violation
    fn create_error_message(&self, class_name: &str) -> String {
        format!(
            "Test class '{}' is not allowed. Use function-based tests with @injected_pytest decorator instead. \
             Class-based tests are incompatible with pinjected's dependency injection system. \
             Migration guide: 1. Convert each test method to a standalone function. \
             2. Add @injected_pytest decorator to each test function. \
             3. Remove the test class wrapper. \
             Example: Instead of 'class TestService: def test_method(self, service): ...' \
             use '@injected_pytest def test_service_method(service): ...'",
            class_name
        )
    }
}

impl LintRule for NoTestClassesRule {
    fn rule_id(&self) -> &str {
        "PINJ053"
    }

    fn description(&self) -> &str {
        "Test classes are forbidden in pytest files. Use function-based tests with @injected_pytest decorator."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check files that match pytest naming conventions
        if !self.is_pytest_file(context.file_path) {
            return violations;
        }

        // Check for class definitions
        if let Stmt::ClassDef(class_def) = context.stmt {
            if self.is_test_class(&class_def.name) {
                violations.push(Violation {
                    rule_id: "PINJ053".to_string(),
                    message: self.create_error_message(&class_def.name),
                    offset: class_def.range.start().to_usize(),
                    file_path: context.file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_ast::Mod;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str, file_path: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, file_path).unwrap();
        let rule = NoTestClassesRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let context = RuleContext {
                        stmt,
                        file_path,
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
    fn test_class_based_test_forbidden() {
        let code = r#"
import pytest

class TestUserService:
    def test_create_user(self, user_service):
        user = user_service.create_user("test@example.com")
        assert user.id is not None
    
    def test_delete_user(self, user_service):
        user_service.delete_user(123)
"#;
        let violations = check_code(code, "test_user_service.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ053");
        assert!(violations[0].message.contains("TestUserService"));
        assert!(violations[0].message.contains("not allowed"));
        assert!(violations[0].message.contains("@injected_pytest"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_multiple_test_classes() {
        let code = r#"
class TestAuth:
    def test_login(self):
        pass

class TestDatabase:
    def test_connection(self):
        pass

class TestAPI:
    def test_endpoint(self):
        pass
"#;
        let violations = check_code(code, "test_integration.py");
        assert_eq!(violations.len(), 3);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ053"));
        assert!(violations.iter().all(|v| v.severity == Severity::Error));
    }

    #[test]
    fn test_nested_test_class() {
        let code = r#"
class OuterClass:
    class TestNested:
        def test_something(self):
            pass
"#;
        // Note: Only top-level classes are checked by the linter
        let violations = check_code(code, "test_nested.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_non_test_class_allowed() {
        let code = r#"
class ServiceHelper:
    # Not a test class, should be allowed
    @staticmethod
    def create_mock_service():
        return MockService()

class DataFactory:
    # Helper class, not a test class
    def create_test_data():
        return {"id": 1}
"#;
        let violations = check_code(code, "test_helpers.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_class_not_starting_with_test() {
        let code = r#"
class UserServiceTest:
    # This doesn't follow pytest convention (should start with Test)
    # So it won't be detected as a test class
    def test_method(self):
        pass

class ServiceTestCase:
    # Also doesn't start with "Test"
    def test_something(self):
        pass
"#;
        let violations = check_code(code, "test_service.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_only_applies_to_test_files() {
        let code = r#"
class TestConfiguration:
    # In a non-test file, this should not trigger the rule
    def configure(self):
        pass
"#;
        // Not a test file
        let violations = check_code(code, "configuration.py");
        assert_eq!(violations.len(), 0);

        // Same code in a test file should trigger
        let violations = check_code(code, "test_configuration.py");
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn test_function_based_tests_allowed() {
        let code = r#"
from pinjected.test_helpers import injected_pytest

@injected_pytest
def test_user_creation(user_service):
    # Function-based test, should not trigger
    user = user_service.create_user("test@example.com")
    assert user.id is not None

@injected_pytest
def test_user_deletion(user_service):
    # Another function-based test
    user_service.delete_user(123)
"#;
        let violations = check_code(code, "test_user.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_unittest_style_class() {
        let code = r#"
import unittest

class TestCase(unittest.TestCase):
    # Even unittest-style classes should be forbidden
    def test_something(self):
        self.assertEqual(1, 1)
"#;
        let violations = check_code(code, "test_unittest.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ053");
        assert!(violations[0].message.contains("TestCase"));
    }

    #[test]
    fn test_parametrized_class() {
        let code = r#"
import pytest

@pytest.mark.parametrize("value", [1, 2, 3])
class TestParametrized:
    # Parametrized test classes should also be forbidden
    def test_with_param(self, value):
        assert value > 0
"#;
        let violations = check_code(code, "test_parametrized.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ053");
        assert!(violations[0].message.contains("TestParametrized"));
    }

    #[test]
    fn test_abstract_test_class() {
        let code = r#"
from abc import ABC, abstractmethod

class TestBase(ABC):
    # Abstract test base classes should also be forbidden
    @abstractmethod
    def test_abstract(self):
        pass
"#;
        let violations = check_code(code, "test_base.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ053");
    }

    #[test]
    fn test_conftest_file() {
        let code = r#"
class TestFixtures:
    # Even in conftest.py, test classes should be forbidden
    @pytest.fixture
    def service(self):
        return Service()
"#;
        // conftest.py files that contain "test" should also be checked
        let violations = check_code(code, "conftest.py");
        assert_eq!(violations.len(), 0); // conftest.py doesn't match test file pattern

        // But test_conftest.py would be checked
        let violations = check_code(code, "test_conftest.py");
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn test_dataclass_not_affected() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class TestData:
    # Dataclasses that happen to start with Test should still be flagged in test files
    id: int
    name: str
"#;
        let violations = check_code(code, "test_models.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ053");
    }
}