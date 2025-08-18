use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Mod, Stmt};

pub struct EnforceModuleDesignInPytestsRule;

impl EnforceModuleDesignInPytestsRule {
    pub fn new() -> Self {
        Self
    }

    fn is_test_module(file_path: &str) -> bool {
        if let Some(name) = std::path::Path::new(file_path).file_name() {
            let n = name.to_str().unwrap_or("");
            return n.starts_with("test_") && n.ends_with(".py");
        }
        false
    }

    fn has_module_design(ast: &Mod) -> bool {
        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    match stmt {
                        Stmt::Assign(assign) => {
                            for target in &assign.targets {
                                if let Expr::Name(name) = target {
                                    if name.id.as_str() == "__design__" {
                                        return true;
                                    }
                                }
                            }
                        }
                        Stmt::AnnAssign(ann) => {
                            if let Expr::Name(name) = ann.target.as_ref() {
                                if name.id.as_str() == "__design__" {
                                    return true;
                                }
                            }
                        }
                        _ => {}
                    }
                }
                false
            }
            _ => false,
        }
    }

    fn message(file_path: &str) -> String {
        let file = std::path::Path::new(file_path)
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or(file_path);
        format!(
r#"Pytest module '{}' is missing a module-level __design__ variable.
Define a top-level __design__ so @injected_pytest can resolve dependencies.
Dependencies referenced in test function parameters must be bound in __design__.

Example:
from pinjected import design, instance
from pinjected.test import injected_pytest

__design__ = design(
    logger=instance("test-logger")
)

@injected_pytest
def test_example(logger):
    assert logger == "test-logger"
"#,
            file
        )
    }
}

impl LintRule for EnforceModuleDesignInPytestsRule {
    fn rule_id(&self) -> &str {
        "PINJ061"
    }

    fn description(&self) -> &str {
        "Pytest modules (test_*.py) must define a module-level __design__ for use with @injected_pytest."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        if !Self::is_test_module(context.file_path) {
            return violations;
        }

        if !Self::has_module_design(context.ast) {
            violations.push(Violation {
                rule_id: "PINJ061".to_string(),
                message: Self::message(context.file_path),
                offset: 0,
                file_path: context.file_path.to_string(),
                severity: Severity::Error,
                fix: None,
            });
        }

        violations
    }
}
