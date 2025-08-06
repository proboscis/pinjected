//! PINJ052: Deprecated register_fixtures_from_design function
//!
//! The register_fixtures_from_design function is deprecated in favor of
//! using @injected_pytest decorator on test functions.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Stmt};

pub struct DeprecatedRegisterFixturesRule;

impl DeprecatedRegisterFixturesRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if an expression is a call to register_fixtures_from_design
    fn is_register_fixtures_call(&self, expr: &Expr) -> bool {
        if let Expr::Call(call) = expr {
            self.is_register_fixtures_func(&call.func)
        } else {
            false
        }
    }

    /// Check if the function being called is register_fixtures_from_design
    fn is_register_fixtures_func(&self, func: &Expr) -> bool {
        match func {
            Expr::Name(name) => name.id.as_str() == "register_fixtures_from_design",
            Expr::Attribute(attr) => {
                // Check for pinjected.test.register_fixtures_from_design
                if let Expr::Attribute(inner_attr) = &*attr.value {
                    if let Expr::Name(name) = &*inner_attr.value {
                        return name.id.as_str() == "pinjected"
                            && inner_attr.attr.as_str() == "test"
                            && attr.attr.as_str() == "register_fixtures_from_design";
                    }
                }
                // Check for test.register_fixtures_from_design
                if let Expr::Name(name) = &*attr.value {
                    return name.id.as_str() == "test"
                        && attr.attr.as_str() == "register_fixtures_from_design";
                }
                false
            }
            _ => false,
        }
    }

    /// Create deprecation message
    fn create_deprecation_message(&self) -> String {
        "The register_fixtures_from_design() function is deprecated and will be removed in a future version. \
         Use @injected_pytest decorator on individual test functions instead. \
         Migration guide: 1. Remove the register_fixtures_from_design() call. \
         2. Import: from pinjected.test_helpers import injected_pytest. \
         3. Add @injected_pytest decorator to each test function that needs dependency injection. \
         Example: @injected_pytest def test_something(service, database): ...".to_string()
    }
}

impl LintRule for DeprecatedRegisterFixturesRule {
    fn rule_id(&self) -> &str {
        "PINJ052"
    }

    fn description(&self) -> &str {
        "register_fixtures_from_design() is deprecated. Use @injected_pytest decorator instead."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            // Check expression statements (function calls)
            Stmt::Expr(expr_stmt) => {
                if self.is_register_fixtures_call(&expr_stmt.value) {
                    violations.push(Violation {
                        rule_id: "PINJ052".to_string(),
                        message: self.create_deprecation_message(),
                        offset: expr_stmt.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Warning,
                        fix: None,
                    });
                }
            }
            // Check assignments that might include register_fixtures_from_design calls
            Stmt::Assign(assign) => {
                if self.is_register_fixtures_call(&assign.value) {
                    violations.push(Violation {
                        rule_id: "PINJ052".to_string(),
                        message: self.create_deprecation_message(),
                        offset: assign.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Warning,
                        fix: None,
                    });
                }
            }
            // Check annotated assignments
            Stmt::AnnAssign(ann_assign) => {
                if let Some(value) = &ann_assign.value {
                    if self.is_register_fixtures_call(value) {
                        violations.push(Violation {
                            rule_id: "PINJ052".to_string(),
                            message: self.create_deprecation_message(),
                            offset: ann_assign.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Warning,
                            fix: None,
                        });
                    }
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
        let rule = DeprecatedRegisterFixturesRule::new();
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
    fn test_register_fixtures_deprecated() {
        let code = r#"
from pinjected.test import register_fixtures_from_design, design

test_design = design(
    service=service_func,
    database=database_func
)

register_fixtures_from_design(test_design)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ052");
        assert!(violations[0].message.contains("deprecated"));
        assert!(violations[0].message.contains("@injected_pytest"));
        assert_eq!(violations[0].severity, Severity::Warning);
    }

    #[test]
    fn test_different_import_styles() {
        // Test different ways of importing register_fixtures_from_design
        let code1 = r#"
from pinjected import test

test.register_fixtures_from_design(my_design)
"#;
        let violations1 = check_code(code1);
        assert_eq!(violations1.len(), 1);

        let code2 = r#"
import pinjected.test

pinjected.test.register_fixtures_from_design(my_design)
"#;
        let violations2 = check_code(code2);
        assert_eq!(violations2.len(), 1);
    }

    #[test]
    fn test_assignment_with_register_fixtures() {
        let code = r#"
from pinjected.test import register_fixtures_from_design

result = register_fixtures_from_design(test_design)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ052");
    }

    #[test]
    fn test_no_violation_for_injected_pytest() {
        let code = r#"
from pinjected.test_helpers import injected_pytest

@injected_pytest
def test_something(service):
    assert service is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_violation_for_other_functions() {
        let code = r#"
from pinjected import design

my_design = design(
    service=service_func
)

# Other function calls should not trigger
my_design.register_provider(some_provider)
setup_test_fixtures(my_design)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_multiple_calls() {
        let code = r#"
from pinjected.test import register_fixtures_from_design

# Multiple calls should all be flagged
register_fixtures_from_design(design1)
register_fixtures_from_design(design2)
result = register_fixtures_from_design(design3)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ052"));
    }
}