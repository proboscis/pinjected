//! PINJ027: No nested @injected or @instance definitions
//!
//! @injected and @instance functions cannot be defined inside any function or class.
//! They must be defined at module level only.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{is_injected_decorator, is_instance_decorator};
use rustpython_ast::{Expr, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};

#[derive(Debug)]
enum ScopeType {
    Function(String),
    Class(String),
}

pub struct NoNestedInjectedRule {
    scope_stack: Vec<ScopeType>,
}

impl NoNestedInjectedRule {
    pub fn new() -> Self {
        Self {
            scope_stack: Vec::new(),
        }
    }

    /// Check if a function has @injected or @instance decorator
    fn has_injected_or_instance_decorator(decorator_list: &[Expr]) -> (bool, bool) {
        let mut has_injected = false;
        let mut has_instance = false;

        for decorator in decorator_list {
            if is_injected_decorator(decorator) {
                has_injected = true;
            }
            if is_instance_decorator(decorator) {
                has_instance = true;
            }
        }

        (has_injected, has_instance)
    }

    /// Check a body (function or class) for nested @injected/@instance definitions
    fn check_body(&mut self, body: &[Stmt]) -> Vec<Violation> {
        let mut violations = Vec::new();

        for stmt in body {
            match stmt {
                Stmt::FunctionDef(func) => {
                    let (has_injected, has_instance) =
                        Self::has_injected_or_instance_decorator(&func.decorator_list);

                    if has_injected || has_instance {
                        let decorator_name = if has_injected {
                            "@injected"
                        } else {
                            "@instance"
                        };
                        let location_desc = self.get_location_description();

                        violations.push(Violation {
                            rule_id: "PINJ027".to_string(),
                            message: format!(
                                "{} function '{}' cannot be defined {}. \
                                {} functions must be defined at module level only.",
                                decorator_name,
                                func.name.as_str(),
                                location_desc,
                                decorator_name
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: String::new(),
                            severity: Severity::Error,
                        });
                    }

                    // Check nested functions recursively
                    self.scope_stack
                        .push(ScopeType::Function(func.name.to_string()));
                    violations.extend(self.check_body(&func.body));
                    self.scope_stack.pop();
                }
                Stmt::AsyncFunctionDef(func) => {
                    let (has_injected, has_instance) =
                        Self::has_injected_or_instance_decorator(&func.decorator_list);

                    if has_injected || has_instance {
                        let decorator_name = if has_injected {
                            "@injected"
                        } else {
                            "@instance"
                        };
                        let location_desc = self.get_location_description();

                        violations.push(Violation {
                            rule_id: "PINJ027".to_string(),
                            message: format!(
                                "{} function '{}' cannot be defined {}. \
                                {} functions must be defined at module level only.",
                                decorator_name,
                                func.name.as_str(),
                                location_desc,
                                decorator_name
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: String::new(),
                            severity: Severity::Error,
                        });
                    }

                    // Check nested functions recursively
                    self.scope_stack
                        .push(ScopeType::Function(func.name.to_string()));
                    violations.extend(self.check_body(&func.body));
                    self.scope_stack.pop();
                }
                Stmt::ClassDef(cls) => {
                    // Check methods inside classes
                    self.scope_stack
                        .push(ScopeType::Class(cls.name.to_string()));
                    violations.extend(self.check_body(&cls.body));
                    self.scope_stack.pop();
                }
                Stmt::If(if_stmt) => {
                    violations.extend(self.check_body(&if_stmt.body));
                    violations.extend(self.check_body(&if_stmt.orelse));
                }
                Stmt::While(while_stmt) => {
                    violations.extend(self.check_body(&while_stmt.body));
                    violations.extend(self.check_body(&while_stmt.orelse));
                }
                Stmt::For(for_stmt) => {
                    violations.extend(self.check_body(&for_stmt.body));
                    violations.extend(self.check_body(&for_stmt.orelse));
                }
                Stmt::With(with_stmt) => {
                    violations.extend(self.check_body(&with_stmt.body));
                }
                Stmt::AsyncWith(with_stmt) => {
                    violations.extend(self.check_body(&with_stmt.body));
                }
                Stmt::Try(try_stmt) => {
                    violations.extend(self.check_body(&try_stmt.body));
                    for handler in &try_stmt.handlers {
                        if let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler {
                            violations.extend(self.check_body(&h.body));
                        }
                    }
                    violations.extend(self.check_body(&try_stmt.orelse));
                    violations.extend(self.check_body(&try_stmt.finalbody));
                }
                _ => {}
            }
        }

        violations
    }

    /// Get description of current location
    fn get_location_description(&self) -> String {
        if self.scope_stack.is_empty() {
            return "at module level".to_string();
        }

        let mut parts = Vec::new();
        for scope in &self.scope_stack {
            match scope {
                ScopeType::Function(name) => parts.push(format!("function '{}'", name)),
                ScopeType::Class(name) => parts.push(format!("class '{}'", name)),
            }
        }

        format!("inside {}", parts.join(" inside "))
    }

    /// Check a regular function definition
    fn check_function(&mut self, func: &StmtFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Check the function body for nested @injected/@instance
        self.scope_stack
            .push(ScopeType::Function(func.name.to_string()));
        violations.extend(self.check_body(&func.body));
        self.scope_stack.pop();

        violations
    }

    /// Check an async function definition
    fn check_async_function(&mut self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Check the function body for nested @injected/@instance
        self.scope_stack
            .push(ScopeType::Function(func.name.to_string()));
        violations.extend(self.check_body(&func.body));
        self.scope_stack.pop();

        violations
    }

    /// Check a class definition
    fn check_class(&mut self, cls: &rustpython_ast::StmtClassDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Check the class body for nested @injected/@instance
        self.scope_stack
            .push(ScopeType::Class(cls.name.to_string()));
        violations.extend(self.check_body(&cls.body));
        self.scope_stack.pop();

        violations
    }
}

impl LintRule for NoNestedInjectedRule {
    fn rule_id(&self) -> &str {
        "PINJ027"
    }

    fn description(&self) -> &str {
        "@injected and @instance functions cannot be defined inside any function or class"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut rule = NoNestedInjectedRule::new();
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                let mut func_violations = rule.check_function(func);
                for violation in &mut func_violations {
                    violation.file_path = context.file_path.to_string();
                }
                violations.extend(func_violations);
            }
            Stmt::AsyncFunctionDef(func) => {
                let mut func_violations = rule.check_async_function(func);
                for violation in &mut func_violations {
                    violation.file_path = context.file_path.to_string();
                }
                violations.extend(func_violations);
            }
            Stmt::ClassDef(cls) => {
                let mut cls_violations = rule.check_class(cls);
                for violation in &mut cls_violations {
                    violation.file_path = context.file_path.to_string();
                }
                violations.extend(cls_violations);
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
        let rule = NoNestedInjectedRule::new();
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
    fn test_injected_inside_regular_function() {
        let code = r#"
from pinjected import injected

def outer_function(user_id: str):
    @injected
    def inner_processor(logger, /, data: dict):
        logger.info(f"Processing: {data}")
        return process(data)
    
    return inner_processor({})
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ027");
        assert!(violations[0]
            .message
            .contains("@injected function 'inner_processor'"));
        assert!(violations[0]
            .message
            .contains("inside function 'outer_function'"));
    }

    #[test]
    fn test_instance_inside_class() {
        let code = r#"
from pinjected import instance

class MyClass:
    @instance
    def my_service(self, config, /):
        return ServiceImpl(config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ027");
        assert!(violations[0]
            .message
            .contains("@instance function 'my_service'"));
        assert!(violations[0].message.contains("inside class 'MyClass'"));
    }

    #[test]
    fn test_valid_module_level_injected() {
        let code = r#"
from pinjected import injected, instance

@injected
def process_data(logger, /, data: dict):
    logger.info(f"Processing: {data}")
    return process(data)

@instance
def my_service(config, /):
    return ServiceImpl(config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_regular_function_allowed_inside() {
        let code = r#"
from pinjected import injected

def process_data(items: list):
    def helper(item):  # Regular function without @injected/@instance is OK
        return item * 2
    
    return [helper(item) for item in items]
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_within_conditional() {
        let code = r#"
from pinjected import injected

def configurable_function(data: str):
    if True:
        @injected
        def debug_processor(logger, /, item):
            logger.debug(f"Debug: {item}")
            return item
        
        return debug_processor(data)
    return data
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ027");
        assert!(violations[0].message.contains("debug_processor"));
    }

    #[test]
    fn test_nested_scope() {
        let code = r#"
from pinjected import injected, instance

class OuterClass:
    def method(self):
        @injected
        def nested_func(logger, /):
            return "nested"
        return nested_func()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ027");
        // Check the actual message format
        assert!(violations[0].message.contains("inside function 'method'"));
        assert!(violations[0].message.contains("inside class 'OuterClass'"));
    }
}
