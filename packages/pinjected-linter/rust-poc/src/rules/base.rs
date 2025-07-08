use crate::models::{RuleContext, Violation};

/// Base trait for all linting rules
pub trait LintRule: Send + Sync {
    /// The unique identifier for this rule (e.g., "PINJ001")
    fn rule_id(&self) -> &str;

    /// Check if this rule is enabled
    fn is_enabled(&self) -> bool {
        true
    }

    /// Perform the lint check on a statement
    fn check(&self, context: &RuleContext) -> Vec<Violation>;

    /// Get the rule description
    fn description(&self) -> &str;
}
