//! PINJ057: Enforce Protocol type annotations for dependencies
//!
//! Dependencies in @injected functions should use Protocol types as type annotations.
//! Using generic types like `callable`, `Any`, or other non-Protocol types is forbidden.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async,
};
use rustpython_ast::{Arguments, Expr, Stmt};

pub struct NoCallableTypeAnnotationRule;

impl NoCallableTypeAnnotationRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a type annotation is a Protocol type
    fn is_protocol_type(annotation: &Expr) -> bool {
        match annotation {
            Expr::Name(name) => {
                // Check if the name ends with "Protocol" (common convention)
                // or is one of the known Protocol types
                let name_str = name.id.as_str();
                name_str.ends_with("Protocol") || name_str == "Protocol"
            }
            Expr::Attribute(attr) => {
                // Check for typing.Protocol or similar
                attr.attr.as_str() == "Protocol" || attr.attr.as_str().ends_with("Protocol")
            }
            Expr::Subscript(sub) => {
                // Check for Protocol[...] or SomethingProtocol[...]
                Self::is_protocol_type(&sub.value)
            }
            _ => false,
        }
    }

    /// Get a descriptive name for the type annotation
    fn get_type_name(annotation: &Expr) -> String {
        match annotation {
            Expr::Name(name) => name.id.to_string(),
            Expr::Attribute(attr) => {
                if let Expr::Name(module) = &*attr.value {
                    format!("{}.{}", module.id, attr.attr)
                } else {
                    attr.attr.to_string()
                }
            }
            Expr::Subscript(sub) => {
                let base = Self::get_type_name(&sub.value);
                format!("{}[...]", base)
            }
            Expr::Constant(c) => {
                if c.value.is_none() {
                    "None".to_string()
                } else {
                    "constant".to_string()
                }
            }
            _ => "unknown".to_string(),
        }
    }

    /// Check if this is a special type that should be allowed
    fn is_allowed_non_protocol_type(annotation: &Expr) -> bool {
        match annotation {
            Expr::Name(name) => {
                let name_str = name.id.as_str();
                // Allow basic types that are not typically wrapped in Protocols
                matches!(name_str, "str" | "int" | "float" | "bool" | "bytes" | "None" | "dict" | "list" | "tuple" | "set")
            }
            Expr::Constant(c) => {
                // Allow None as a type annotation
                c.value.is_none()
            }
            _ => false,
        }
    }

    /// Check function arguments for non-Protocol type annotations
    fn check_args_for_non_protocol_types(
        args: &Arguments,
        _func_name: &str,
    ) -> Vec<(String, String, usize)> {
        let mut violations = Vec::new();

        // Check positional-only args first (these are definitely dependencies)
        for arg in args.posonlyargs.iter() {
            let arg_name = arg.def.arg.as_str();
            
            if let Some(annotation) = &arg.def.annotation {
                // Skip if it's a Protocol type or an allowed basic type
                if !Self::is_protocol_type(annotation) && !Self::is_allowed_non_protocol_type(annotation) {
                    let type_name = Self::get_type_name(annotation);
                    violations.push((arg_name.to_string(), type_name, arg.def.range.start().to_usize()));
                }
            }
        }

        // If there are no positional-only args, we need to check regular args
        // In @injected functions without '/', all args are considered dependencies
        // In @injected functions with '/', only args before '/' are dependencies
        // Since we can't easily detect '/' position here, we check all regular args
        // when posonlyargs is empty (which means either no '/' or parser doesn't recognize it)
        if args.posonlyargs.is_empty() {
            for arg in args.args.iter() {
                let arg_name = arg.def.arg.as_str();
                
                // Skip 'self' in methods
                if arg_name == "self" {
                    continue;
                }
                
                if let Some(annotation) = &arg.def.annotation {
                    // Skip if it's a Protocol type or an allowed basic type
                    if !Self::is_protocol_type(annotation) && !Self::is_allowed_non_protocol_type(annotation) {
                        let type_name = Self::get_type_name(annotation);
                        violations.push((arg_name.to_string(), type_name, arg.def.range.start().to_usize()));
                    }
                }
            }
        }

        violations
    }

    /// Check a function for non-Protocol type annotations
    fn check_function(&self, func: &rustpython_ast::StmtFunctionDef) -> Vec<Violation> {
        if !has_injected_decorator(func) {
            return vec![];
        }

        let violations_info = Self::check_args_for_non_protocol_types(&func.args, func.name.as_str());
        let mut violations = Vec::new();

        for (param_name, type_name, offset) in violations_info {
            let capitalized_name = if !param_name.is_empty() {
                param_name.chars().next().unwrap().to_uppercase().to_string() + &param_name[1..]
            } else {
                param_name.clone()
            };

            let message = if type_name == "callable" || type_name == "Callable" || type_name.contains("Callable") {
                format!(
                    "Dependency '{}' in @injected function '{}' uses '{}' type annotation. \
                    This is forbidden. Instead, define and use a specific Protocol type that describes \
                    the expected interface. For example:\n\n\
                    class {}Protocol(Protocol):\n    \
                    def __call__(self, ...) -> ...: ...\n\n\
                    Then use '{}Protocol' as the type annotation.",
                    param_name, func.name, type_name, capitalized_name, capitalized_name
                )
            } else if type_name == "Any" || type_name.contains(".Any") {
                format!(
                    "Dependency '{}' in @injected function '{}' uses '{}' type annotation. \
                    This is too generic. Define and use a specific Protocol type that describes \
                    the expected interface of this dependency.",
                    param_name, func.name, type_name
                )
            } else {
                format!(
                    "Dependency '{}' in @injected function '{}' uses non-Protocol type '{}'. \
                    Dependencies should use Protocol types to define their interface. \
                    Consider creating a Protocol type that describes the expected interface.",
                    param_name, func.name, type_name
                )
            };

            violations.push(Violation {
                rule_id: "PINJ057".to_string(),
                message,
                offset,
                file_path: String::new(),
                severity: Severity::Warning,
                fix: None,
            });
        }

        violations
    }

    /// Check an async function for non-Protocol type annotations
    fn check_async_function(&self, func: &rustpython_ast::StmtAsyncFunctionDef) -> Vec<Violation> {
        if !has_injected_decorator_async(func) {
            return vec![];
        }

        let violations_info = Self::check_args_for_non_protocol_types(&func.args, func.name.as_str());
        let mut violations = Vec::new();

        for (param_name, type_name, offset) in violations_info {
            let capitalized_name = if !param_name.is_empty() {
                param_name.chars().next().unwrap().to_uppercase().to_string() + &param_name[1..]
            } else {
                param_name.clone()
            };

            let message = if type_name == "callable" || type_name == "Callable" || type_name.contains("Callable") {
                format!(
                    "Dependency '{}' in @injected async function '{}' uses '{}' type annotation. \
                    This is forbidden. Instead, define and use a specific Protocol type that describes \
                    the expected interface. For example:\n\n\
                    class {}Protocol(Protocol):\n    \
                    async def __call__(self, ...) -> ...: ...\n\n\
                    Then use '{}Protocol' as the type annotation.",
                    param_name, func.name, type_name, capitalized_name, capitalized_name
                )
            } else if type_name == "Any" || type_name.contains(".Any") {
                format!(
                    "Dependency '{}' in @injected async function '{}' uses '{}' type annotation. \
                    This is too generic. Define and use a specific Protocol type that describes \
                    the expected interface of this dependency.",
                    param_name, func.name, type_name
                )
            } else {
                format!(
                    "Dependency '{}' in @injected async function '{}' uses non-Protocol type '{}'. \
                    Dependencies should use Protocol types to define their interface. \
                    Consider creating a Protocol type that describes the expected interface.",
                    param_name, func.name, type_name
                )
            };

            violations.push(Violation {
                rule_id: "PINJ057".to_string(),
                message,
                offset,
                file_path: String::new(),
                severity: Severity::Warning,
                fix: None,
            });
        }

        violations
    }
}

impl LintRule for NoCallableTypeAnnotationRule {
    fn rule_id(&self) -> &str {
        "PINJ057"
    }

    fn description(&self) -> &str {
        "Dependencies in @injected functions must use Protocol types as type annotations, not generic types like 'callable', 'Any', or other non-Protocol types."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        match context.stmt {
            Stmt::FunctionDef(func) => self.check_function(func),
            Stmt::AsyncFunctionDef(func) => self.check_async_function(func),
            _ => vec![],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = NoCallableTypeAnnotationRule::new();
        let mut violations = Vec::new();

        match &ast {
            rustpython_ast::Mod::Module(module) => {
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
    fn test_callable_type_annotation() {
        let code = r#"
from pinjected import injected

@injected
def process_data(
    fetch_data: callable,
    store_data: callable,
    /,
    data: str
) -> str:
    fetched = fetch_data()
    store_data(fetched)
    return fetched
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("'fetch_data'"));
        assert!(violations[0].message.contains("uses 'callable' type annotation"));
        assert!(violations[1].message.contains("'store_data'"));
        assert!(violations[1].message.contains("uses 'callable' type annotation"));
    }

    #[test]
    fn test_typing_callable() {
        let code = r#"
from pinjected import injected
from typing import Callable

@injected
def process_data(
    fetch_data: Callable,
    store_data: Callable[[str], None],
    /,
    data: str
) -> str:
    fetched = fetch_data()
    store_data(fetched)
    return fetched
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("'fetch_data'"));
        assert!(violations[1].message.contains("'store_data'"));
    }

    #[test]
    fn test_collections_callable() {
        let code = r#"
from pinjected import injected
import collections.abc

@injected
def process_data(
    fetch_data: collections.abc.Callable,
    /,
    data: str
) -> str:
    return fetch_data()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("'fetch_data'"));
    }

    #[test]
    fn test_protocol_type_annotation() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class FetchDataProtocol(Protocol):
    def __call__(self) -> str: ...

class StoreDataProtocol(Protocol):
    def __call__(self, data: str) -> None: ...

@injected
def process_data(
    fetch_data: FetchDataProtocol,
    store_data: StoreDataProtocol,
    /,
    data: str
) -> str:
    fetched = fetch_data()
    store_data(fetched)
    return fetched
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_async_function_with_callable() {
        let code = r#"
from pinjected import injected
from typing import Callable

@injected
async def a_process_data(
    a_fetch_data: Callable,
    a_store_data: callable,
    /,
    data: str
) -> str:
    fetched = await a_fetch_data()
    await a_store_data(fetched)
    return fetched
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("'a_fetch_data'"));
        assert!(violations[0].message.contains("async function"));
        assert!(violations[1].message.contains("'a_store_data'"));
    }

    #[test]
    fn test_non_injected_function() {
        let code = r#"
from typing import Callable

def process_data(
    fetch_data: Callable,
    store_data: callable,
    data: str
) -> str:
    fetched = fetch_data()
    store_data(fetched)
    return fetched
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_with_protocol_defined() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class AFetchBloombergTopHeadlinesProtocol(Protocol):
    async def __call__(self, source: str) -> list: ...

@injected(protocol=AFetchAndStoreNewBloombergHeadlinesProtocol)
async def a_fetch_and_store_new_bloomberg_headlines(
    a_fetch_bloomberg_top_headlines: AFetchBloombergTopHeadlinesProtocol,
    a_store_raw_bloomberg_article: callable,
    a_query_latest_stored_bloomberg_article_time: callable,
    a_ensure_bloomberg_influxdb_bucket: callable,
    a_emit_bloomberg_fetch_metrics: callable,
    a_check_bloomberg_article_exists_by_id: callable,
    /,
    source: str = "homepage_latest",
) -> int:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 5);  // All the callable-typed parameters
        assert!(violations[0].message.contains("'a_store_raw_bloomberg_article'"));
        assert!(violations[1].message.contains("'a_query_latest_stored_bloomberg_article_time'"));
        assert!(violations[2].message.contains("'a_ensure_bloomberg_influxdb_bucket'"));
        assert!(violations[3].message.contains("'a_emit_bloomberg_fetch_metrics'"));
        assert!(violations[4].message.contains("'a_check_bloomberg_article_exists_by_id'"));
    }

    #[test]
    fn test_mixed_types() {
        let code = r#"
from pinjected import injected
from typing import Callable, Protocol, Any

class ServiceProtocol(Protocol):
    def serve(self) -> None: ...

@injected
def orchestrate(
    service: ServiceProtocol,  # Good
    helper: Callable,  # Bad
    logger: Any,  # Bad - too generic
    processor: callable,  # Bad
    /,
) -> None:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
        assert!(violations[0].message.contains("'helper'"));
        assert!(violations[1].message.contains("'logger'"));
        assert!(violations[2].message.contains("'processor'"));
    }

    #[test]
    fn test_arguments_after_slash() {
        let code = r#"
from pinjected import injected
from typing import Callable

@injected
def process_data(
    fetch_data: Callable,  # Bad - before slash
    /,
    store_data: Callable,  # OK - after slash, not a dependency
    data: str
) -> str:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("'fetch_data'"));
        // store_data should not be flagged since it's after the slash
    }

    #[test]
    fn test_any_type_annotation() {
        let code = r#"
from pinjected import injected
from typing import Any

@injected
def process_data(
    service: Any,
    processor: Any,
    /,
    data: str
) -> str:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("'service'"));
        assert!(violations[0].message.contains("uses 'Any' type annotation"));
        assert!(violations[0].message.contains("too generic"));
        assert!(violations[1].message.contains("'processor'"));
    }

    #[test]
    fn test_non_protocol_class_type() {
        let code = r#"
from pinjected import injected

class MyService:
    def serve(self) -> None: ...

@injected
def process_data(
    service: MyService,  # Bad - not a Protocol
    /,
    data: str
) -> str:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("'service'"));
        assert!(violations[0].message.contains("uses non-Protocol type 'MyService'"));
    }

    #[test]
    fn test_allowed_basic_types() {
        let code = r#"
from pinjected import injected

@injected
def process_data(
    config: dict,  # OK - basic type
    count: int,    # OK - basic type
    names: list,   # OK - basic type
    /,
    data: str
) -> str:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0, "Basic types should be allowed");
    }

    #[test]
    fn test_object_type() {
        let code = r#"
from pinjected import injected

@injected
def process_data(
    service: object,  # Bad - too generic
    /,
    data: str
) -> str:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("'service'"));
        assert!(violations[0].message.contains("uses non-Protocol type 'object'"));
    }

    #[test]
    fn test_custom_protocol_ending() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class ServiceProtocol(Protocol):
    def serve(self) -> None: ...

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

@injected
def process_data(
    service: ServiceProtocol,      # OK - ends with Protocol
    database: DatabaseProtocol,    # OK - ends with Protocol
    /,
    data: str
) -> str:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0, "Protocol types should be allowed");
    }

    #[test]
    fn test_typing_protocol_import() {
        let code = r#"
from pinjected import injected
import typing

@injected
def process_data(
    service: typing.Protocol,  # OK - is Protocol
    helper: typing.Any,        # Bad - is Any
    processor: typing.Callable, # Bad - is Callable
    /,
    data: str
) -> str:
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("'helper'"));
        assert!(violations[0].message.contains("typing.Any"));
        assert!(violations[1].message.contains("'processor'"));
        assert!(violations[1].message.contains("typing.Callable"));
    }
}