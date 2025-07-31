//! PINJ049: Enforce protocol type annotations for dependencies
//!
//! When @injected functions have protocol=T annotations, dependencies that use these functions
//! should have type annotation T instead of generic types like Callable, Any, or object.

use crate::models::{Fix, RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::{
    Arguments, Expr, Mod, Stmt,
};
use std::collections::HashMap;
use std::path::PathBuf;

pub struct EnforceProtocolTypeAnnotationsRule;

impl EnforceProtocolTypeAnnotationsRule {
    pub fn new() -> Self {
        Self
    }

    /// Extract protocol type from @injected or @instance decorator
    fn extract_protocol_type(decorators: &[Expr]) -> Option<String> {
        for decorator in decorators {
            match decorator {
                Expr::Call(call) => {
                    // Check if this is an @injected or @instance call
                    let (is_injected, is_instance) = match &*call.func {
                        Expr::Name(name) => {
                            let n = name.id.as_str();
                            (n == "injected", n == "instance")
                        }
                        Expr::Attribute(attr) => {
                            if let Expr::Name(name) = &*attr.value {
                                let module = name.id.as_str();
                                let attr_name = attr.attr.as_str();
                                (
                                    module == "pinjected" && attr_name == "injected",
                                    module == "pinjected" && attr_name == "instance"
                                )
                            } else {
                                (false, false)
                            }
                        }
                        _ => (false, false),
                    };

                    if is_injected || is_instance {
                        // Look for protocol keyword argument
                        for keyword in &call.keywords {
                            if let Some(arg_name) = &keyword.arg {
                                if arg_name.as_str() == "protocol" {
                                    return Self::expr_to_type_string(&keyword.value);
                                }
                            }
                        }
                    }
                }
                _ => {}
            }
        }
        None
    }

    /// Convert an expression to a type string
    fn expr_to_type_string(expr: &Expr) -> Option<String> {
        match expr {
            Expr::Name(name) => Some(name.id.to_string()),
            Expr::Attribute(attr) => {
                if let Some(base) = Self::expr_to_type_string(&attr.value) {
                    Some(format!("{}.{}", base, attr.attr))
                } else {
                    None
                }
            }
            Expr::Subscript(sub) => {
                // Handle generic types like Protocol[T]
                if let Some(base) = Self::expr_to_type_string(&sub.value) {
                    if let Some(slice) = Self::expr_to_type_string(&sub.slice) {
                        Some(format!("{}[{}]", base, slice))
                    } else {
                        Some(base)
                    }
                } else {
                    None
                }
            }
            _ => None,
        }
    }

    /// Check if a type annotation is a generic type (Callable, Any, object)
    fn is_generic_type(annotation: &Expr) -> bool {
        match annotation {
            Expr::Name(name) => {
                matches!(name.id.as_str(), "Callable" | "Any" | "object")
            }
            Expr::Attribute(attr) => {
                if let Expr::Name(module) = &*attr.value {
                    let module_name = module.id.as_str();
                    let attr_name = attr.attr.as_str();
                    matches!(
                        (module_name, attr_name),
                        ("typing", "Callable") | ("typing", "Any")
                    )
                } else {
                    false
                }
            }
            Expr::Subscript(sub) => {
                // Check for Callable[...]
                Self::is_generic_type(&sub.value)
            }
            _ => false,
        }
    }

    /// Build a map of function names to their protocol types
    fn build_protocol_map(ast: &Mod) -> HashMap<String, String> {
        let mut protocol_map = HashMap::new();

        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    match stmt {
                        Stmt::FunctionDef(func) => {
                            if has_injected_decorator(func) || has_instance_decorator(func) {
                                if let Some(protocol) =
                                    Self::extract_protocol_type(&func.decorator_list)
                                {
                                    protocol_map.insert(func.name.to_string(), protocol);
                                }
                            }
                        }
                        Stmt::AsyncFunctionDef(func) => {
                            if has_injected_decorator_async(func)
                                || has_instance_decorator_async(func)
                            {
                                if let Some(protocol) =
                                    Self::extract_protocol_type(&func.decorator_list)
                                {
                                    protocol_map.insert(func.name.to_string(), protocol);
                                }
                            }
                        }
                        _ => {}
                    }
                }
            }
            _ => {}
        }

        protocol_map
    }

    /// Check function arguments for incorrect type annotations
    fn check_args_for_incorrect_types(
        args: &Arguments,
        protocol_map: &HashMap<String, String>,
        is_injected: bool,
    ) -> Vec<(String, String, String, usize)> {
        let mut violations = Vec::new();

        if is_injected {
            // For @injected, only check positional-only args (before /)
            for (idx, arg) in args.posonlyargs.iter().enumerate() {
                let arg_name = arg.def.arg.as_str();

                // Check if this parameter name corresponds to a function with a protocol
                if let Some(expected_type) = protocol_map.get(arg_name) {
                    if let Some(annotation) = &arg.def.annotation {
                        if Self::is_generic_type(annotation) {
                            let current_type = Self::expr_to_type_string(annotation)
                                .unwrap_or_else(|| "Unknown".to_string());
                            violations.push((
                                arg_name.to_string(),
                                current_type,
                                expected_type.clone(),
                                idx,
                            ));
                        }
                    }
                }
            }
        } else {
            // For @instance, check all arguments
            // Check posonlyargs
            for (idx, arg) in args.posonlyargs.iter().enumerate() {
                let arg_name = arg.def.arg.as_str();

                if let Some(expected_type) = protocol_map.get(arg_name) {
                    if let Some(annotation) = &arg.def.annotation {
                        if Self::is_generic_type(annotation) {
                            let current_type = Self::expr_to_type_string(annotation)
                                .unwrap_or_else(|| "Unknown".to_string());
                            violations.push((
                                arg_name.to_string(),
                                current_type,
                                expected_type.clone(),
                                idx,
                            ));
                        }
                    }
                }
            }

            // Check regular args
            for (idx, arg) in args.args.iter().enumerate() {
                let arg_name = arg.def.arg.as_str();

                if let Some(expected_type) = protocol_map.get(arg_name) {
                    if let Some(annotation) = &arg.def.annotation {
                        if Self::is_generic_type(annotation) {
                            let current_type = Self::expr_to_type_string(annotation)
                                .unwrap_or_else(|| "Unknown".to_string());
                            let actual_idx = args.posonlyargs.len() + idx;
                            violations.push((
                                arg_name.to_string(),
                                current_type,
                                expected_type.clone(),
                                actual_idx,
                            ));
                        }
                    }
                }
            }
        }

        violations
    }

    /// Generate fix content by replacing the type annotation
    fn generate_fix(
        source: &str,
        func_offset: usize,
        arg_name: &str,
        new_type: &str,
    ) -> Option<String> {
        // This is a simplified fix generation. In a real implementation,
        // we would use proper AST manipulation to ensure correct replacement.
        let lines: Vec<&str> = source.lines().collect();
        let mut result = String::new();
        let mut char_count = 0;

        for line in lines {
            if char_count <= func_offset && func_offset < char_count + line.len() + 1 {
                // This line contains the function definition
                // Look for the argument and its type annotation
                if let Some(arg_pos) = line.find(&format!("{}: ", arg_name)) {
                    let type_start = arg_pos + arg_name.len() + 2;
                    let rest = &line[type_start..];
                    
                    // Find the end of the type annotation (comma, slash, or closing paren)
                    let type_end = rest.chars()
                        .position(|c| matches!(c, ',' | '/' | ')'))
                        .unwrap_or(rest.len());
                    
                    let new_line = format!(
                        "{}{}{}",
                        &line[..type_start],
                        new_type,
                        &rest[type_end..]
                    );
                    result.push_str(&new_line);
                } else {
                    result.push_str(line);
                }
            } else {
                result.push_str(line);
            }
            result.push('\n');
            char_count += line.len() + 1;
        }

        // Remove trailing newline
        if result.ends_with('\n') {
            result.pop();
        }

        Some(result)
    }

}

impl LintRule for EnforceProtocolTypeAnnotationsRule {
    fn rule_id(&self) -> &str {
        "PINJ049"
    }

    fn description(&self) -> &str {
        "Dependencies with protocol annotations should use the protocol type instead of generic types"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Build protocol map for the entire module
        let protocol_map = Self::build_protocol_map(context.ast);

        // Now check each function in the module
        match context.ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    match stmt {
                        Stmt::FunctionDef(func) => {
                            // Only check @injected and @instance functions
                            if has_injected_decorator(func) || has_instance_decorator(func) {
                                let is_injected = has_injected_decorator(func);
                                let incorrect_types = Self::check_args_for_incorrect_types(
                                    &func.args,
                                    &protocol_map,
                                    is_injected,
                                );

                                for (param_name, current_type, expected_type, _) in incorrect_types {
                                    let message = format!(
                                        "Dependency '{}' has type '{}' but should use '{}' as defined by its protocol annotation",
                                        param_name, current_type, expected_type
                                    );

                                    let fix = Self::generate_fix(
                                        context.source,
                                        func.range.start().to_usize(),
                                        &param_name,
                                        &expected_type,
                                    ).map(|content| Fix {
                                        description: format!("Replace {} with {}", current_type, expected_type),
                                        file_path: PathBuf::from(context.file_path),
                                        content,
                                    });

                                    violations.push(Violation {
                                        rule_id: "PINJ049".to_string(),
                                        message,
                                        offset: func.range.start().to_usize(),
                                        file_path: context.file_path.to_string(),
                                        severity: Severity::Warning,
                                        fix,
                                    });
                                }
                            }
                        }
                        Stmt::AsyncFunctionDef(func) => {
                            // Only check @injected and @instance functions
                            if has_injected_decorator_async(func) || has_instance_decorator_async(func) {
                                let is_injected = has_injected_decorator_async(func);
                                let incorrect_types = Self::check_args_for_incorrect_types(
                                    &func.args,
                                    &protocol_map,
                                    is_injected,
                                );

                                for (param_name, current_type, expected_type, _) in incorrect_types {
                                    let message = format!(
                                        "Dependency '{}' has type '{}' but should use '{}' as defined by its protocol annotation",
                                        param_name, current_type, expected_type
                                    );

                                    let fix = Self::generate_fix(
                                        context.source,
                                        func.range.start().to_usize(),
                                        &param_name,
                                        &expected_type,
                                    ).map(|content| Fix {
                                        description: format!("Replace {} with {}", current_type, expected_type),
                                        file_path: PathBuf::from(context.file_path),
                                        content,
                                    });

                                    violations.push(Violation {
                                        rule_id: "PINJ049".to_string(),
                                        message,
                                        offset: func.range.start().to_usize(),
                                        file_path: context.file_path.to_string(),
                                        severity: Severity::Warning,
                                        fix,
                                    });
                                }
                            }
                        }
                        _ => {}
                    }
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
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = EnforceProtocolTypeAnnotationsRule::new();
        
        // Create a module-level context
        let context = RuleContext {
            stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass {
                range: rustpython_ast::text_size::TextRange::default(),
            }),
            file_path: "test.py",
            source: code,
            ast: &ast,
        };
        
        rule.check(&context)
    }

    #[test]
    fn test_injected_with_protocol_using_generic_type() {
        let code = r#"
from pinjected import injected
from typing import Callable, Protocol

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

@injected(protocol=DatabaseProtocol)
def database(config, /, host: str) -> DatabaseProtocol:
    return SQLDatabase(config, host)

@injected
def process_data(database: Callable, /, data: str) -> str:
    return database().query(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ049");
        assert!(violations[0].message.contains("'database'"));
        assert!(violations[0].message.contains("'Callable'"));
        assert!(violations[0].message.contains("'DatabaseProtocol'"));
    }

    #[test]
    fn test_injected_with_protocol_using_correct_type() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

@injected(protocol=DatabaseProtocol)
def database(config, /, host: str) -> DatabaseProtocol:
    return SQLDatabase(config, host)

@injected
def process_data(database: DatabaseProtocol, /, data: str) -> str:
    return database.query(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_instance_with_protocol_using_any() {
        let code = r#"
from pinjected import instance, injected
from typing import Any, Protocol

class CacheProtocol(Protocol):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...

@instance(protocol=CacheProtocol)
def redis_cache(host: str, port: int) -> CacheProtocol:
    return RedisCache(host, port)

@injected
def fetch_data(redis_cache: Any, /, key: str) -> Any:
    return redis_cache.get(key)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ049");
        assert!(violations[0].message.contains("'redis_cache'"));
        assert!(violations[0].message.contains("'Any'"));
        assert!(violations[0].message.contains("'CacheProtocol'"));
    }

    #[test]
    fn test_multiple_dependencies_mixed_types() {
        let code = r#"
from pinjected import injected
from typing import Any, Callable, Protocol

class LoggerProtocol(Protocol):
    def log(self, msg: str) -> None: ...

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

@injected(protocol=LoggerProtocol)
def logger(level: str) -> LoggerProtocol:
    return Logger(level)

@injected(protocol=DatabaseProtocol)
def database(config, /, host: str) -> DatabaseProtocol:
    return Database(config, host)

@injected
def process_data(
    logger: Callable,  # Should be LoggerProtocol
    database: DatabaseProtocol,  # Correct
    cache: Any,  # Not a known protocol, OK
    /, 
    data: str
) -> str:
    logger().log("Processing data")
    return database.query(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ049");
        assert!(violations[0].message.contains("'logger'"));
        assert!(violations[0].message.contains("'Callable'"));
        assert!(violations[0].message.contains("'LoggerProtocol'"));
    }

    #[test]
    fn test_async_functions() {
        let code = r#"
from pinjected import injected
from typing import Any, Protocol

class AsyncClientProtocol(Protocol):
    async def fetch(self, url: str) -> dict: ...

@injected(protocol=AsyncClientProtocol)
async def a_http_client(timeout, /, base_url: str) -> AsyncClientProtocol:
    return await AsyncHTTPClient.create(timeout, base_url)

@injected
async def a_fetch_data(
    a_http_client: Any,  # Should be AsyncClientProtocol
    /, 
    endpoint: str
) -> dict:
    return await a_http_client.fetch(endpoint)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ049");
        assert!(violations[0].message.contains("'a_http_client'"));
        assert!(violations[0].message.contains("'Any'"));
        assert!(violations[0].message.contains("'AsyncClientProtocol'"));
    }

    #[test]
    fn test_typing_module_annotations() {
        let code = r#"
from pinjected import injected
import typing

class ServiceProtocol(typing.Protocol):
    def serve(self) -> None: ...

@injected(protocol=ServiceProtocol)
def service(config, /) -> ServiceProtocol:
    return Service(config)

@injected
def run_service(
    service: typing.Any,  # Should be ServiceProtocol
    /, 
) -> None:
    service.serve()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ049");
        assert!(violations[0].message.contains("'service'"));
        assert!(violations[0].message.contains("ServiceProtocol"));
    }

    #[test]
    fn test_object_type() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class ManagerProtocol(Protocol):
    def manage(self) -> None: ...

@injected(protocol=ManagerProtocol)
def manager(settings: dict) -> ManagerProtocol:
    return Manager(settings)

@injected
def orchestrate(
    manager: object,  # Should be ManagerProtocol
    /, 
) -> None:
    manager.manage()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ049");
        assert!(violations[0].message.contains("'manager'"));
        assert!(violations[0].message.contains("'object'"));
        assert!(violations[0].message.contains("'ManagerProtocol'"));
    }

    #[test]
    fn test_no_protocol_annotation() {
        let code = r#"
from pinjected import injected
from typing import Any

@injected
def simple_service(config, /) -> dict:
    return {"status": "ok"}

@injected
def use_service(
    simple_service: Any,  # OK - simple_service has no protocol
    /, 
) -> str:
    return simple_service()["status"]
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}