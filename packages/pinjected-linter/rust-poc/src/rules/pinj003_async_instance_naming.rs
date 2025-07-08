//! PINJ003: Async instance naming
//! 
//! Async @instance functions should NOT have 'a_' prefix.
//! The 'a_' prefix is only for @injected functions.

use rustpython_ast::Stmt;
use crate::models::{Violation, RuleContext, Severity};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_instance_decorator_async, has_async_prefix};

pub struct AsyncInstanceNamingRule;

impl AsyncInstanceNamingRule {
    pub fn new() -> Self {
        Self
    }
}

impl LintRule for AsyncInstanceNamingRule {
    fn rule_id(&self) -> &str {
        "PINJ003"
    }
    
    fn description(&self) -> &str {
        "Async @instance functions should NOT have 'a_' prefix"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::AsyncFunctionDef(func) => {
                if has_instance_decorator_async(func) && has_async_prefix(&func.name) {
                    let _suggested_name = &func.name[2..]; // Remove 'a_' prefix
                    
                    violations.push(Violation {
                        rule_id: self.rule_id().to_string(),
                        message: format!(
                            "Async @instance function '{}' should not have 'a_' prefix. \
                            The 'a_' prefix is only for @injected functions.",
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