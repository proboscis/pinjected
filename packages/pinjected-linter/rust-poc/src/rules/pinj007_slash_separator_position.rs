//! PINJ007: Slash separator position
//! 
//! The slash separator (/) must correctly separate injected dependencies
//! (left side) from runtime arguments (right side). Dependencies placed
//! after the slash will not be injected and will cause runtime errors.
//! 
//! Note: This rule is currently disabled as we can't reliably determine
//! developer intent for parameters after the slash.

use rustpython_ast::Stmt;
use crate::models::{Violation, RuleContext};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_injected_decorator, has_injected_decorator_async,
                                       find_slash_position, find_slash_position_async};

pub struct SlashSeparatorPositionRule;

impl SlashSeparatorPositionRule {
    pub fn new() -> Self {
        Self
    }
}

impl LintRule for SlashSeparatorPositionRule {
    fn rule_id(&self) -> &str {
        "PINJ007"
    }
    
    fn description(&self) -> &str {
        "/ must separate injected dependencies (left) from runtime args (right)"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    let _slash_pos = find_slash_position(func);
                    // Currently disabled - we can't determine intent
                    // The developer might intentionally want parameters with 
                    // dependency-like names as runtime arguments
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    let _slash_pos = find_slash_position_async(func);
                    // Currently disabled - we can't determine intent
                }
            }
            _ => {}
        }

        violations
    }
}