//! PINJ059: Enforce test file placement in tests directory
//!
//! Python files that start with 'test' must be placed under a 'tests' directory.
//! This ensures proper organization and separation of test code from production code.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use std::path::Path;

pub struct TestFilePlacementRule;

impl TestFilePlacementRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a file name indicates it's a test file
    fn is_test_file(&self, file_path: &str) -> bool {
        if let Some(file_name) = Path::new(file_path).file_name() {
            if let Some(name_str) = file_name.to_str() {
                // Check if the file starts with "test_" or "test." and has .py extension
                // This matches pytest conventions for test file naming
                return (name_str.starts_with("test_") || name_str == "test.py") && name_str.ends_with(".py");
            }
        }
        false
    }

    /// Check if the file is properly placed in a tests directory
    fn is_in_tests_directory(&self, file_path: &str) -> bool {
        let path = Path::new(file_path);
        // Check if any parent directory is named "tests"
        for ancestor in path.ancestors() {
            if let Some(dir_name) = ancestor.file_name() {
                if let Some(name_str) = dir_name.to_str() {
                    if name_str == "tests" {
                        return true;
                    }
                }
            }
        }
        false
    }

    /// Create error message for misplaced test file
    fn create_error_message(&self, file_path: &str) -> String {
        let file_name = Path::new(file_path)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("test file");
        
        format!(
            "Test file '{}' must be placed under a 'tests' directory. \
             Files starting with 'test' should be organized in the tests directory structure \
             (e.g., tests/test_module.py, tests/unit/test_service.py). \
             Current location: {}. \
             Migration: Move this file to an appropriate location under the 'tests' directory.",
            file_name, file_path
        )
    }
}

impl LintRule for TestFilePlacementRule {
    fn rule_id(&self) -> &str {
        "PINJ059"
    }

    fn description(&self) -> &str {
        "Test files (starting with 'test') must be placed under a 'tests' directory"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check on the first statement to avoid duplicate violations for the same file
        // This prevents multiple violations for the same file
        if let rustpython_ast::Mod::Module(module) = context.ast {
            if !module.body.is_empty() && !std::ptr::eq(context.stmt, &module.body[0]) {
                return violations;
            }
        } else {
            return violations;
        }

        // Check if this is a test file that's not in a tests directory
        if self.is_test_file(context.file_path) && !self.is_in_tests_directory(context.file_path) {
            violations.push(Violation {
                rule_id: "PINJ059".to_string(),
                message: self.create_error_message(context.file_path),
                offset: 0, // File-level violation, position at start
                file_path: context.file_path.to_string(),
                severity: Severity::Error,
                fix: None,
            });
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
        let rule = TestFilePlacementRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                // Only check the first statement to avoid duplicates
                if let Some(first_stmt) = module.body.first() {
                    let context = RuleContext {
                        stmt: first_stmt,
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
    fn test_file_not_in_tests_directory() {
        let code = r#"
import pytest

def test_something():
    assert 1 == 1
"#;
        let violations = check_code(code, "src/test_module.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ059");
        assert!(violations[0].message.contains("must be placed under a 'tests' directory"));
        assert!(violations[0].message.contains("test_module.py"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_file_in_tests_directory() {
        let code = r#"
import pytest

def test_something():
    assert 1 == 1
"#;
        let violations = check_code(code, "tests/test_module.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_file_in_nested_tests_directory() {
        let code = r#"
def test_nested():
    pass
"#;
        let violations = check_code(code, "tests/unit/test_service.py");
        assert_eq!(violations.len(), 0);
        
        let violations = check_code(code, "tests/integration/api/test_endpoints.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_file_in_wrong_location() {
        let code = r#"
def test_something():
    pass
"#;
        // Various wrong locations
        let violations = check_code(code, "test_module.py");
        assert_eq!(violations.len(), 1);
        
        let violations = check_code(code, "src/test_utils.py");
        assert_eq!(violations.len(), 1);
        
        let violations = check_code(code, "lib/test_helpers.py");
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn test_non_test_file_allowed_anywhere() {
        let code = r#"
def some_function():
    pass
"#;
        // Non-test files can be anywhere
        let violations = check_code(code, "src/module.py");
        assert_eq!(violations.len(), 0);
        
        let violations = check_code(code, "helpers.py");
        assert_eq!(violations.len(), 0);
        
        let violations = check_code(code, "testing_utils.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_file_with_test_in_middle() {
        let code = r#"
def function():
    pass
"#;
        // Files that don't start with "test" are allowed anywhere
        let violations = check_code(code, "my_test_file.py");
        assert_eq!(violations.len(), 0);
        
        let violations = check_code(code, "src/integration_test.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_various_test_file_patterns() {
        let code = r#"
def test_func():
    pass
"#;
        // Files starting with "test" should be in tests/
        let violations = check_code(code, "test_unit.py");
        assert_eq!(violations.len(), 1);
        
        let violations = check_code(code, "test_integration.py");
        assert_eq!(violations.len(), 1);
        
        let violations = check_code(code, "testing.py");
        assert_eq!(violations.len(), 0); // Doesn't start with "test"
        
        let violations = check_code(code, "tests.py");
        assert_eq!(violations.len(), 0); // Doesn't start with "test"
    }

    #[test]
    fn test_deeply_nested_wrong_location() {
        let code = r#"
def test_something():
    pass
"#;
        // Deep nesting but not under tests/
        let violations = check_code(code, "src/services/auth/test_auth.py");
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("test_auth.py"));
        assert!(violations[0].message.contains("src/services/auth/test_auth.py"));
    }

    #[test]
    fn test_project_with_tests_in_name() {
        let code = r#"
def test_something():
    pass
"#;
        // Project directory named something with "tests" but not exactly "tests"
        let violations = check_code(code, "my_tests_project/test_module.py");
        assert_eq!(violations.len(), 1); // Should still violate
        
        let violations = check_code(code, "unit_tests/test_module.py");
        assert_eq!(violations.len(), 1); // Should still violate - must be exactly "tests"
    }

    #[test]
    fn test_non_python_files_ignored() {
        // This rule only applies to Python files
        // Non-Python files wouldn't be parsed, but let's ensure the logic is correct
        let rule = TestFilePlacementRule::new();
        assert!(!rule.is_test_file("test_something.txt"));
        assert!(!rule.is_test_file("test_module.js"));
        assert!(rule.is_test_file("test_module.py"));
    }

    #[test]
    fn test_conftest_file_placement() {
        let code = r#"
import pytest

@pytest.fixture
def my_fixture():
    return "test"
"#;
        // conftest.py doesn't start with "test", so it's allowed anywhere
        let violations = check_code(code, "conftest.py");
        assert_eq!(violations.len(), 0);
        
        let violations = check_code(code, "src/conftest.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_edge_case_tests_directory_itself() {
        let code = r#"
def test_something():
    pass
"#;
        // Edge case: file directly in tests/ directory
        let violations = check_code(code, "tests/test_main.py");
        assert_eq!(violations.len(), 0);
    }
}