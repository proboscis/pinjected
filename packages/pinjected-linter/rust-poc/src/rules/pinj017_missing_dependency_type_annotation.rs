//! PINJ017: Missing type annotation for dependencies
//!
//! Dependencies in @instance and @injected functions should have type annotations
//! for better type safety and IDE support.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::{Arguments, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct MissingDependencyTypeAnnotationRule;

impl MissingDependencyTypeAnnotationRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if arguments have type annotations
    fn check_args_for_annotations(
        args: &Arguments,
        _func_name: &str,
        is_injected: bool,
    ) -> Vec<(String, usize)> {
        let mut missing_annotations = Vec::new();

        if is_injected {
            // For @injected, only check positional-only args (before /)
            for (idx, arg) in args.posonlyargs.iter().enumerate() {
                if arg.def.annotation.is_none() {
                    missing_annotations.push((arg.def.arg.to_string(), idx));
                }
            }
        } else {
            // For @instance, check all arguments
            // Check posonlyargs
            for (idx, arg) in args.posonlyargs.iter().enumerate() {
                if arg.def.annotation.is_none() {
                    missing_annotations.push((arg.def.arg.to_string(), idx));
                }
            }

            // Check regular args
            for (idx, arg) in args.args.iter().enumerate() {
                if arg.def.annotation.is_none() {
                    let actual_idx = args.posonlyargs.len() + idx;
                    missing_annotations.push((arg.def.arg.to_string(), actual_idx));
                }
            }

            // Check kwonlyargs
            for arg in args.kwonlyargs.iter() {
                if arg.def.annotation.is_none() {
                    missing_annotations.push((arg.def.arg.to_string(), 0)); // Position doesn't matter for kwargs
                }
            }
        }

        missing_annotations
    }

    /// Check a function definition
    fn check_function(&self, func: &StmtFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        let is_instance = has_instance_decorator(func);
        let is_injected = has_injected_decorator(func);

        if !is_instance && !is_injected {
            return violations;
        }

        let missing = Self::check_args_for_annotations(&func.args, func.name.as_str(), is_injected);

        if !missing.is_empty() {
            let decorator_type = if is_instance {
                "@instance"
            } else {
                "@injected"
            };
            let missing_params: Vec<String> = missing
                .iter()
                .map(|(name, _)| format!("'{}'", name))
                .collect();
            let message = if missing.len() == 1 {
                format!(
                    "{} function '{}' has dependency {} without type annotation. Add type annotation for better type safety.",
                    decorator_type,
                    func.name.as_str(),
                    missing_params[0]
                )
            } else {
                format!(
                    "{} function '{}' has dependencies {} without type annotations. Add type annotations for better type safety.",
                    decorator_type,
                    func.name.as_str(),
                    missing_params.join(", ")
                )
            };

            violations.push(Violation {
                rule_id: "PINJ017".to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
            });
        }

        violations
    }

    /// Check an async function definition
    fn check_async_function(&self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        let is_instance = has_instance_decorator_async(func);
        let is_injected = has_injected_decorator_async(func);

        if !is_instance && !is_injected {
            return violations;
        }

        let missing = Self::check_args_for_annotations(&func.args, func.name.as_str(), is_injected);

        if !missing.is_empty() {
            let decorator_type = if is_instance {
                "@instance"
            } else {
                "@injected"
            };
            let missing_params: Vec<String> = missing
                .iter()
                .map(|(name, _)| format!("'{}'", name))
                .collect();
            let message = if missing.len() == 1 {
                format!(
                    "{} function '{}' has dependency {} without type annotation. Add type annotation for better type safety.",
                    decorator_type,
                    func.name.as_str(),
                    missing_params[0]
                )
            } else {
                format!(
                    "{} function '{}' has dependencies {} without type annotations. Add type annotations for better type safety.",
                    decorator_type,
                    func.name.as_str(),
                    missing_params.join(", ")
                )
            };

            violations.push(Violation {
                rule_id: "PINJ017".to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
            });
        }

        violations
    }
}

impl LintRule for MissingDependencyTypeAnnotationRule {
    fn rule_id(&self) -> &str {
        "PINJ017"
    }

    fn description(&self) -> &str {
        "Dependencies in @instance and @injected functions should have type annotations"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            rustpython_ast::Stmt::FunctionDef(func) => {
                for mut violation in self.check_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            rustpython_ast::Stmt::AsyncFunctionDef(func) => {
                for mut violation in self.check_async_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
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
        let rule = MissingDependencyTypeAnnotationRule::new();
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
    fn test_instance_without_annotations() {
        let code = r#"
from pinjected import instance

@instance
def database(host, port):
    return Database(host, port)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ017");
        assert!(violations[0].message.contains("'host', 'port'"));
    }

    #[test]
    fn test_instance_with_annotations() {
        let code = r#"
from pinjected import instance

@instance
def database(host: str, port: int):
    return Database(host, port)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_instance_partial_annotations() {
        let code = r#"
from pinjected import instance

@instance
def database(host: str, port):
    return Database(host, port)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ017");
        assert!(violations[0].message.contains("'port'"));
    }

    #[test]
    fn test_injected_without_annotations() {
        let code = r#"
from pinjected import injected

@injected
def process_data(logger, database, /, data: str) -> str:
    return database.query(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ017");
        assert!(violations[0].message.contains("'logger', 'database'"));
    }

    #[test]
    fn test_injected_with_annotations() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class Logger(Protocol):
    def info(self, msg: str) -> None: ...

class Database(Protocol):
    def query(self, q: str) -> str: ...

@injected
def process_data(logger: Logger, database: Database, /, data: str) -> str:
    return database.query(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_no_dependencies() {
        let code = r#"
from pinjected import injected

@injected
def simple_function(data: str) -> str:
    # pinjected: no dependencies
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_async_instance_without_annotations() {
        let code = r#"
from pinjected import instance

@instance
async def a_database(host, port):
    return await AsyncDatabase.connect(host, port)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ017");
    }

    #[test]
    fn test_async_injected_without_annotations() {
        let code = r#"
from pinjected import injected

@injected
async def a_fetch_data(client, cache, /, url: str) -> dict:
    return await client.get(url)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ017");
        assert!(violations[0].message.contains("'client', 'cache'"));
    }

    #[test]
    fn test_regular_function_ignored() {
        let code = r#"
def regular_function(arg1, arg2):
    return arg1 + arg2
    
class MyClass:
    def method(self, param):
        return param
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}
