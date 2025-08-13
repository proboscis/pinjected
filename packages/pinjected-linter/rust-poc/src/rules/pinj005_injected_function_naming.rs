//! PINJ005: Injected function naming convention
//!
//! @injected functions represent actions or operations that can be performed
//! with injected dependencies. Using verb forms makes it clear that these
//! are functions to be called, not values to be provided.
//!
//! Note: If you're confident your function name is already in verb form,
//! you can suppress this warning with `# noqa: PINJ005`

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, is_verb_like,
};
use rustpython_ast::Stmt;

pub struct InjectedFunctionNamingRule;

impl InjectedFunctionNamingRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if name follows verb naming convention
    fn is_verb_form(name: &str) -> bool {
        // Empty or single char names are invalid
        if name.len() <= 1 {
            return false;
        }

        // Use the shared is_verb_like utility
        is_verb_like(name)
    }

    /// Suggest a verb form for a noun-named function
    fn suggest_verb_form(name: &str) -> String {
        // Common noun to verb transformations
        if name.ends_with("_data") {
            format!("get_{}", name)
        } else if name.ends_with("_info") || name.ends_with("_information") {
            format!("fetch_{}", name)
        } else if name.ends_with("_config") || name.ends_with("_configuration") {
            format!("load_{}", name)
        } else if name.ends_with("_result") {
            format!("calculate_{}", name)
        } else if name.ends_with("_response") {
            format!("get_{}", name)
        } else if name.ends_with("_manager") || name.ends_with("_handler") {
            // These are already action-oriented, might just need prefix
            format!("get_{}", name)
        } else if name == "data" {
            "get_data".to_string()
        } else if name == "info" {
            "get_info".to_string()
        } else if name == "config" {
            "load_config".to_string()
        } else if name == "configuration" {
            "load_configuration".to_string()
        } else if name == "result" {
            "get_result".to_string()
        } else if name == "response" {
            "get_response".to_string()
        } else if !name.contains('_') {
            // Single word, probably a noun
            format!("get_{}", name)
        } else {
            // For other cases, suggest adding a get_ prefix
            format!("get_{}", name)
        }
    }
}

impl LintRule for InjectedFunctionNamingRule {
    fn rule_id(&self) -> &str {
        "PINJ005"
    }

    fn description(&self) -> &str {
        "@injected functions should use verb forms (use `# noqa: PINJ005` if confident the name is already a verb)"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    let function_name = &func.name;

                    if !Self::is_verb_form(function_name) {
                        let suggestion = Self::suggest_verb_form(function_name);

                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message: format!(
                                "@injected function '{}' uses noun form. Use verb form instead. Consider renaming to '{}'. \
                                If you're confident this is already a verb, use `# noqa: PINJ005` to suppress this warning.",
                                function_name, suggestion
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Warning,
                            fix: None,
                        });
                    }
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    let function_name = &func.name;

                    // Handle async prefix for async functions
                    let (name_to_check, has_async_prefix) = if function_name.starts_with("a_") {
                        (&function_name[2..], true)
                    } else {
                        (function_name.as_str(), false)
                    };

                    if !Self::is_verb_form(name_to_check) {
                        let suggestion = Self::suggest_verb_form(name_to_check);
                        let final_suggestion = if has_async_prefix {
                            format!("a_{}", suggestion)
                        } else {
                            suggestion
                        };

                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message: format!(
                                "@injected function '{}' uses noun form. Use verb form instead. \
                                Consider renaming to '{}'. \
                                If you're confident this is already a verb, use `# noqa: PINJ005` to suppress this warning.",
                                function_name, final_suggestion
                            ),
                            offset: func.range.start().to_usize(),
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
