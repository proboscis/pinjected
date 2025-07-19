//! PINJ026: a_ prefixed dependencies should not use Any type
//!
//! When @injected functions have a protocol parameter, their a_ prefixed
//! dependencies should have proper type annotations instead of Any.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Arguments, Expr, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct APrefixDependencyAnyTypeRule;

impl APrefixDependencyAnyTypeRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if the function has a protocol parameter in its @injected decorator
    fn has_protocol_parameter(decorators: &[Expr]) -> bool {
        for decorator in decorators {
            match decorator {
                Expr::Call(call) => {
                    // Check if this is an @injected call
                    if let Expr::Name(name) = &*call.func {
                        if name.id.as_str() == "injected" {
                            // Check for protocol keyword argument
                            for keyword in &call.keywords {
                                if let Some(arg_name) = &keyword.arg {
                                    if arg_name.as_str() == "protocol" {
                                        return true;
                                    }
                                }
                            }
                        }
                    }
                }
                _ => {}
            }
        }
        false
    }

    /// Check if a type annotation is Any
    fn is_any_type(annotation: &Expr) -> bool {
        match annotation {
            Expr::Name(name) => name.id.as_str() == "Any",
            Expr::Attribute(attr) => {
                // Check for typing.Any
                if let Expr::Name(module) = &*attr.value {
                    if module.id.as_str() == "typing" && attr.attr.as_str() == "Any" {
                        return true;
                    }
                }
                false
            }
            _ => false,
        }
    }

    /// Check arguments for a_ prefixed parameters with Any type
    fn check_args_for_a_prefix_any(args: &Arguments) -> Vec<(String, usize)> {
        let mut violations = Vec::new();

        // Only check positional-only args (before /) for @injected
        for (idx, arg) in args.posonlyargs.iter().enumerate() {
            let arg_name = arg.def.arg.as_str();

            // Check if it starts with a_ and has Any annotation
            if arg_name.starts_with("a_") {
                if let Some(annotation) = &arg.def.annotation {
                    if Self::is_any_type(annotation) {
                        violations.push((arg_name.to_string(), idx));
                    }
                }
            }
        }

        violations
    }

    /// Check a function definition
    fn check_function(&self, func: &StmtFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check @injected functions with protocol parameter
        if !has_injected_decorator(func) || !Self::has_protocol_parameter(&func.decorator_list) {
            return violations;
        }

        let a_prefix_any_deps = Self::check_args_for_a_prefix_any(&func.args);

        if !a_prefix_any_deps.is_empty() {
            let dep_names: Vec<String> = a_prefix_any_deps
                .iter()
                .map(|(name, _)| format!("'{}'", name))
                .collect();

            let message = if a_prefix_any_deps.len() == 1 {
                format!(
                    "@injected function '{}' with protocol has a_ prefixed dependency {} typed as Any. Use proper protocol or type annotation instead.",
                    func.name.as_str(),
                    dep_names[0]
                )
            } else {
                format!(
                    "@injected function '{}' with protocol has a_ prefixed dependencies {} typed as Any. Use proper protocol or type annotations instead.",
                    func.name.as_str(),
                    dep_names.join(", ")
                )
            };

            violations.push(Violation {
                rule_id: "PINJ026".to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
                            fix: None,});
        }

        violations
    }

    /// Check an async function definition
    fn check_async_function(&self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check @injected functions with protocol parameter
        if !has_injected_decorator_async(func)
            || !Self::has_protocol_parameter(&func.decorator_list)
        {
            return violations;
        }

        let a_prefix_any_deps = Self::check_args_for_a_prefix_any(&func.args);

        if !a_prefix_any_deps.is_empty() {
            let dep_names: Vec<String> = a_prefix_any_deps
                .iter()
                .map(|(name, _)| format!("'{}'", name))
                .collect();

            let message = if a_prefix_any_deps.len() == 1 {
                format!(
                    "@injected function '{}' with protocol has a_ prefixed dependency {} typed as Any. Use proper protocol or type annotation instead.",
                    func.name.as_str(),
                    dep_names[0]
                )
            } else {
                format!(
                    "@injected function '{}' with protocol has a_ prefixed dependencies {} typed as Any. Use proper protocol or type annotations instead.",
                    func.name.as_str(),
                    dep_names.join(", ")
                )
            };

            violations.push(Violation {
                rule_id: "PINJ026".to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
                            fix: None,});
        }

        violations
    }
}

impl LintRule for APrefixDependencyAnyTypeRule {
    fn rule_id(&self) -> &str {
        "PINJ026"
    }

    fn description(&self) -> &str {
        "a_ prefixed dependencies in @injected functions with protocol should not use Any type"
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
        let rule = APrefixDependencyAnyTypeRule::new();
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
    fn test_injected_with_protocol_a_prefix_any() {
        let code = r#"
from pinjected import injected
from typing import Any

@injected(protocol=SomeProtocol)
async def a_process_data(
    a_fetcher: Any,
    a_processor: Any,
    logger: Any,
    /,
    data: str
) -> Result:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ026");
        assert!(violations[0].message.contains("'a_fetcher', 'a_processor'"));
        assert!(!violations[0].message.contains("logger")); // Non a_ prefix not included
    }

    #[test]
    fn test_injected_with_protocol_proper_types() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class AFetcherProtocol(Protocol):
    async def fetch(self, data: str) -> dict: ...

class AProcessorProtocol(Protocol):
    async def process(self, data: dict) -> Result: ...

@injected(protocol=SomeProtocol)
async def a_process_data(
    a_fetcher: AFetcherProtocol,
    a_processor: AProcessorProtocol,
    logger: Any,  # OK - not a_ prefixed
    /,
    data: str
) -> Result:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_without_protocol() {
        let code = r#"
from pinjected import injected
from typing import Any

@injected
async def a_process_data(
    a_fetcher: Any,  # Should not trigger - no protocol parameter
    a_processor: Any,
    /,
    data: str
) -> Result:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_instance_function_ignored() {
        let code = r#"
from pinjected import instance
from typing import Any

@instance
def a_database(a_config: Any):
    return Database(a_config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_regular_function_ignored() {
        let code = r#"
from typing import Any

def a_regular_function(a_param: Any):
    return a_param
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_partial_a_prefix_any() {
        let code = r#"
from pinjected import injected
from typing import Any, Protocol

class AProcessorProtocol(Protocol):
    pass

@injected(protocol=SomeProtocol)
def process_data(
    a_fetcher: Any,  # Bad
    a_processor: AProcessorProtocol,  # Good
    non_a_param: Any,  # OK - not a_ prefixed
    /,
    data: str
) -> Result:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ026");
        assert!(violations[0].message.contains("'a_fetcher'"));
        assert!(!violations[0].message.contains("a_processor"));
        assert!(!violations[0].message.contains("non_a_param"));
    }

    #[test]
    fn test_typing_any() {
        let code = r#"
from pinjected import injected
import typing

@injected(protocol=SomeProtocol)
def process_data(
    a_fetcher: typing.Any,
    /,
    data: str
) -> Result:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ026");
        assert!(violations[0].message.contains("'a_fetcher'"));
    }
}
