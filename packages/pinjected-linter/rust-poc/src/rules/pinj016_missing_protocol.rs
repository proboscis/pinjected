//! PINJ016: Missing protocol parameter in @injected decorator
//!
//! @injected functions should always define and use Protocol by specifying
//! it in the protocol parameter of the decorator.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::is_injected_decorator;
use rustpython_ast::{Arguments, Expr, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct MissingProtocolRule;

impl MissingProtocolRule {
    pub fn new() -> Self {
        Self
    }

    /// Generate the protocol signature for an @injected function
    fn generate_protocol_signature(
        func_name: &str,
        args: &Arguments,
        returns: Option<&Expr>,
    ) -> String {
        let mut signature_parts = Vec::new();

        // Add regular args (after the slash)
        for arg in &args.args {
            let arg_name = arg.def.arg.as_str();
            if let Some(ann) = &arg.def.annotation {
                // Try to extract a simple type annotation
                let type_str = Self::expr_to_type_string(ann);
                signature_parts.push(format!("{}: {}", arg_name, type_str));
            } else {
                signature_parts.push(arg_name.to_string());
            }
        }

        // Add keyword-only args
        for arg in &args.kwonlyargs {
            let arg_name = arg.def.arg.as_str();
            if let Some(ann) = &arg.def.annotation {
                let type_str = Self::expr_to_type_string(ann);
                signature_parts.push(format!("{}: {}", arg_name, type_str));
            } else {
                signature_parts.push(arg_name.to_string());
            }
        }

        // Build the return type
        let return_type = if let Some(ret) = returns {
            format!(" -> {}", Self::expr_to_type_string(ret))
        } else {
            String::new()
        };

        // Convert function name to PascalCase for the protocol name
        let protocol_name = func_name
            .split('_')
            .map(|part| {
                part.chars()
                    .enumerate()
                    .map(|(i, c)| {
                        if i == 0 {
                            c.to_uppercase().to_string()
                        } else {
                            c.to_string()
                        }
                    })
                    .collect::<String>()
            })
            .collect::<String>();

        // Format the protocol
        format!(
            "class {}Protocol(Protocol):\n    def __call__(self, {}){}: ...",
            protocol_name,
            signature_parts.join(", "),
            return_type
        )
    }

    /// Convert an expression to a type string (simplified)
    fn expr_to_type_string(expr: &Expr) -> String {
        match expr {
            Expr::Name(name) => name.id.to_string(),
            Expr::Constant(c) => match &c.value {
                rustpython_ast::Constant::Str(s) => format!("'{}'", s),
                _ => "Any".to_string(),
            },
            Expr::Subscript(sub) => {
                if let Expr::Name(name) = &*sub.value {
                    format!("{}[{}]", name.id, Self::expr_to_type_string(&sub.slice))
                } else {
                    "Any".to_string()
                }
            }
            Expr::Tuple(tuple) => {
                let elements: Vec<String> = tuple
                    .elts
                    .iter()
                    .map(|e| Self::expr_to_type_string(e))
                    .collect();
                format!("({})", elements.join(", "))
            }
            Expr::List(list) => {
                let elements: Vec<String> = list
                    .elts
                    .iter()
                    .map(|e| Self::expr_to_type_string(e))
                    .collect();
                format!("[{}]", elements.join(", "))
            }
            _ => "Any".to_string(),
        }
    }

    /// Check if an @injected decorator has a protocol parameter
    fn has_protocol_parameter(decorator: &Expr) -> bool {
        match decorator {
            Expr::Call(call) => {
                // Check if this is a call to @injected
                if !Self::is_injected_call(&call.func) {
                    return false;
                }

                // Check if any keyword argument is named "protocol"
                call.keywords.iter().any(|kw| {
                    kw.arg
                        .as_ref()
                        .map_or(false, |arg| arg.as_str() == "protocol")
                })
            }
            _ => {
                // Simple @injected without parameters - no protocol
                false
            }
        }
    }

    /// Check if the function expression is an @injected decorator
    fn is_injected_call(func: &Expr) -> bool {
        is_injected_decorator(func)
    }

    /// Check a function definition
    fn check_function(&self, func: &StmtFunctionDef) -> Option<Violation> {
        // Check if any decorator is @injected
        let mut has_injected = false;
        let mut has_protocol = false;

        for decorator in &func.decorator_list {
            match decorator {
                Expr::Name(name) if name.id.as_str() == "injected" => {
                    has_injected = true;
                    // Simple @injected without parameters
                }
                Expr::Attribute(attr) => {
                    if let Expr::Name(name) = &*attr.value {
                        if name.id.as_str() == "pinjected" && attr.attr.as_str() == "injected" {
                            has_injected = true;
                            // Simple pinjected.injected without parameters
                        }
                    }
                }
                Expr::Call(call) => {
                    if Self::is_injected_call(&call.func) {
                        has_injected = true;
                        has_protocol = Self::has_protocol_parameter(decorator);
                    }
                }
                _ => {}
            }
        }

        if has_injected && !has_protocol {
            let protocol_signature = Self::generate_protocol_signature(
                func.name.as_str(),
                &func.args,
                func.returns.as_ref().map(|r| &**r),
            );
            // Extract just the protocol name
            let protocol_name = func
                .name
                .split('_')
                .map(|part| {
                    part.chars()
                        .enumerate()
                        .map(|(i, c)| {
                            if i == 0 {
                                c.to_uppercase().to_string()
                            } else {
                                c.to_string()
                            }
                        })
                        .collect::<String>()
                })
                .collect::<String>()
                + "Protocol";
            Some(Violation {
                rule_id: "PINJ016".to_string(),
                message: format!(
                    "@injected function '{}' should specify a Protocol using the protocol parameter. Example:\n\n{}\n\n@injected(protocol={})",
                    func.name.as_str(),
                    protocol_signature,
                    protocol_name
                ),
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
            })
        } else {
            None
        }
    }

    /// Check an async function definition
    fn check_async_function(&self, func: &StmtAsyncFunctionDef) -> Option<Violation> {
        // Check if any decorator is @injected
        let mut has_injected = false;
        let mut has_protocol = false;

        for decorator in &func.decorator_list {
            match decorator {
                Expr::Name(name) if name.id.as_str() == "injected" => {
                    has_injected = true;
                    // Simple @injected without parameters
                }
                Expr::Attribute(attr) => {
                    if let Expr::Name(name) = &*attr.value {
                        if name.id.as_str() == "pinjected" && attr.attr.as_str() == "injected" {
                            has_injected = true;
                            // Simple pinjected.injected without parameters
                        }
                    }
                }
                Expr::Call(call) => {
                    if Self::is_injected_call(&call.func) {
                        has_injected = true;
                        has_protocol = Self::has_protocol_parameter(decorator);
                    }
                }
                _ => {}
            }
        }

        if has_injected && !has_protocol {
            let protocol_signature = Self::generate_protocol_signature(
                func.name.as_str(),
                &func.args,
                func.returns.as_ref().map(|r| &**r),
            );
            // Extract just the protocol name
            let protocol_name = func
                .name
                .split('_')
                .map(|part| {
                    part.chars()
                        .enumerate()
                        .map(|(i, c)| {
                            if i == 0 {
                                c.to_uppercase().to_string()
                            } else {
                                c.to_string()
                            }
                        })
                        .collect::<String>()
                })
                .collect::<String>()
                + "Protocol";
            Some(Violation {
                rule_id: "PINJ016".to_string(),
                message: format!(
                    "@injected function '{}' should specify a Protocol using the protocol parameter. Example:\n\n{}\n\n@injected(protocol={})",
                    func.name.as_str(),
                    protocol_signature,
                    protocol_name
                ),
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Warning,
            })
        } else {
            None
        }
    }
}

impl LintRule for MissingProtocolRule {
    fn rule_id(&self) -> &str {
        "PINJ016"
    }

    fn description(&self) -> &str {
        "@injected functions should specify a Protocol using the protocol parameter"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            rustpython_ast::Stmt::FunctionDef(func) => {
                if let Some(mut violation) = self.check_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            rustpython_ast::Stmt::AsyncFunctionDef(func) => {
                if let Some(mut violation) = self.check_async_function(func) {
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
        let rule = MissingProtocolRule::new();
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
    fn test_injected_without_protocol() {
        let code = r#"
from pinjected import injected

@injected
def process_data(logger, /, data: str) -> str:
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ016");
        assert!(violations[0].message.contains("process_data"));
    }

    #[test]
    fn test_injected_with_protocol() {
        let code = r#"
from typing import Protocol
from pinjected import injected

class ProcessorProtocol(Protocol):
    def __call__(self, data: str) -> str: ...

@injected(protocol=ProcessorProtocol)
def process_data(logger, /, data: str) -> str:
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_with_other_params_no_protocol() {
        let code = r#"
from pinjected import injected

@injected(cache=True)
def process_data(logger, /, data: str) -> str:
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ016");
    }

    #[test]
    fn test_async_injected_without_protocol() {
        let code = r#"
from pinjected import injected

@injected
async def a_process_data(logger, /, data: str) -> str:
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ016");
    }

    #[test]
    fn test_not_injected() {
        let code = r#"
from pinjected import instance

@instance
def logger():
    return Logger()
    
def regular_function(data: str) -> str:
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}
