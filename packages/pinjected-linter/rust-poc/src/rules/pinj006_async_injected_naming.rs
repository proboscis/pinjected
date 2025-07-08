//! PINJ006: Async injected naming
//!
//! Async @injected functions must have 'a_' prefix.
//! This helps distinguish async functions in dependency injection.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_async_prefix, has_injected_decorator_async};
use rustpython_ast::Stmt;

pub struct AsyncInjectedNamingRule;

impl AsyncInjectedNamingRule {
    pub fn new() -> Self {
        Self
    }
}

impl LintRule for AsyncInjectedNamingRule {
    fn rule_id(&self) -> &str {
        "PINJ006"
    }

    fn description(&self) -> &str {
        "Async @injected functions must have 'a_' prefix"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) && !has_async_prefix(&func.name) {
                    violations.push(Violation {
                        rule_id: self.rule_id().to_string(),
                        message: format!(
                            "Async @injected function '{}' must have 'a_' prefix. \
                            This helps distinguish async functions in dependency injection.",
                            func.name
                        ),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Error,
                    });
                }
            }
            _ => {}
        }

        violations
    }
}
