//! PINJ001: Instance naming convention
//!
//! @instance decorated functions should have noun-like names

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_instance_decorator, has_instance_decorator_async, is_noun_like,
};
use rustpython_ast::Stmt;

pub struct InstanceNamingRule;

impl InstanceNamingRule {
    pub fn new() -> Self {
        Self
    }
}

impl LintRule for InstanceNamingRule {
    fn rule_id(&self) -> &str {
        "PINJ001"
    }

    fn description(&self) -> &str {
        "Instance naming convention (@instance functions should be nouns)"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                if has_instance_decorator(func) && !is_noun_like(&func.name) {
                    violations.push(Violation {
                        rule_id: self.rule_id().to_string(),
                        message: format!(
                            "@instance function '{}' should be a noun. Consider using a name like 'logger' or 'database'.",
                            func.name
                        ),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_instance_decorator_async(func) && !is_noun_like(&func.name) {
                    violations.push(Violation {
                        rule_id: self.rule_id().to_string(),
                        message: format!(
                            "@instance function '{}' should be a noun. Consider using a name like 'logger' or 'database'.",
                            func.name
                        ),
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
