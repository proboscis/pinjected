//! PINJ027: No nested @injected functions
//!
//! @injected functions cannot be defined inside other @injected functions.
//! This violates the principle that @injected functions build AST/computation graphs.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::is_injected_decorator;
use rustpython_ast::{Expr, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct NoNestedInjectedRule {
    in_injected_function: Vec<String>,
}

impl NoNestedInjectedRule {
    pub fn new() -> Self {
        Self {
            in_injected_function: Vec::new(),
        }
    }

    /// Check if a function has @injected decorator
    fn has_injected_decorator(decorator_list: &[Expr]) -> bool {
        for decorator in decorator_list {
            if is_injected_decorator(decorator) {
                return true;
            }
        }
        false
    }

    /// Check a function body for nested @injected definitions
    fn check_function_body(&mut self, body: &[Stmt], parent_name: &str) -> Vec<Violation> {
        let mut violations = Vec::new();

        // We're now inside an @injected function
        self.in_injected_function.push(parent_name.to_string());

        for stmt in body {
            match stmt {
                Stmt::FunctionDef(func) => {
                    if Self::has_injected_decorator(&func.decorator_list) {
                        violations.push(Violation {
                            rule_id: "PINJ027".to_string(),
                            message: format!(
                                "@injected function '{}' cannot be defined inside @injected function '{}'. \
                                @injected functions build computation graphs, not execute code. \
                                Move '{}' to module level and inject it as a dependency instead.",
                                func.name.as_str(),
                                parent_name,
                                func.name.as_str()
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: String::new(),
                            severity: Severity::Error,
                        });
                    }
                    // Check nested functions recursively
                    violations.extend(self.check_function_body(&func.body, func.name.as_str()));
                }
                Stmt::AsyncFunctionDef(func) => {
                    if Self::has_injected_decorator(&func.decorator_list) {
                        violations.push(Violation {
                            rule_id: "PINJ027".to_string(),
                            message: format!(
                                "@injected function '{}' cannot be defined inside @injected function '{}'. \
                                @injected functions build computation graphs, not execute code. \
                                Move '{}' to module level and inject it as a dependency instead.",
                                func.name.as_str(),
                                parent_name,
                                func.name.as_str()
                            ),
                            offset: func.range.start().to_usize(),
                            file_path: String::new(),
                            severity: Severity::Error,
                        });
                    }
                    // Check nested functions recursively
                    violations.extend(self.check_function_body(&func.body, func.name.as_str()));
                }
                Stmt::ClassDef(cls) => {
                    // Check methods inside classes
                    violations.extend(self.check_function_body(&cls.body, &format!("{}.{}", parent_name, cls.name)));
                }
                Stmt::If(if_stmt) => {
                    violations.extend(self.check_function_body(&if_stmt.body, parent_name));
                    violations.extend(self.check_function_body(&if_stmt.orelse, parent_name));
                }
                Stmt::While(while_stmt) => {
                    violations.extend(self.check_function_body(&while_stmt.body, parent_name));
                    violations.extend(self.check_function_body(&while_stmt.orelse, parent_name));
                }
                Stmt::For(for_stmt) => {
                    violations.extend(self.check_function_body(&for_stmt.body, parent_name));
                    violations.extend(self.check_function_body(&for_stmt.orelse, parent_name));
                }
                Stmt::With(with_stmt) => {
                    violations.extend(self.check_function_body(&with_stmt.body, parent_name));
                }
                Stmt::AsyncWith(with_stmt) => {
                    violations.extend(self.check_function_body(&with_stmt.body, parent_name));
                }
                Stmt::Try(try_stmt) => {
                    violations.extend(self.check_function_body(&try_stmt.body, parent_name));
                    for handler in &try_stmt.handlers {
                        if let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler {
                            violations.extend(self.check_function_body(&h.body, parent_name));
                        }
                    }
                    violations.extend(self.check_function_body(&try_stmt.orelse, parent_name));
                    violations.extend(self.check_function_body(&try_stmt.finalbody, parent_name));
                }
                _ => {}
            }
        }

        // We're leaving this function
        self.in_injected_function.pop();

        violations
    }

    /// Check a regular function definition
    fn check_function(&mut self, func: &StmtFunctionDef) -> Vec<Violation> {
        if Self::has_injected_decorator(&func.decorator_list) {
            self.check_function_body(&func.body, func.name.as_str())
        } else {
            Vec::new()
        }
    }

    /// Check an async function definition
    fn check_async_function(&mut self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        if Self::has_injected_decorator(&func.decorator_list) {
            self.check_function_body(&func.body, func.name.as_str())
        } else {
            Vec::new()
        }
    }
}

impl LintRule for NoNestedInjectedRule {
    fn rule_id(&self) -> &str {
        "PINJ027"
    }

    fn description(&self) -> &str {
        "@injected functions cannot be defined inside other @injected functions"
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
    fn test_nested_injected_function() {
        let code = r#"
from pinjected import injected

@injected
def outer_function(database, /, user_id: str):
    @injected
    def inner_processor(logger, /, data: dict):
        logger.info(f"Processing: {data}")
        return process(data)
    
    user = database.get_user(user_id)
    return inner_processor(user.data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ027");
        assert!(violations[0].message.contains("inner_processor"));
        assert!(violations[0].message.contains("outer_function"));
    }

    #[test]
    fn test_nested_async_injected() {
        let code = r#"
from pinjected import injected

@injected
async def a_test_v3_implementation(design, logger, /, sketch_path: str) -> dict:
    @injected
    async def a_tracking_sketch_to_line_art(
        a_auto_cached_sketch_to_line_art,
        /,
        sketch_path: str
    ) -> dict:
        return await a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)
    
    result = await a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ027");
        assert!(violations[0].message.contains("a_tracking_sketch_to_line_art"));
        assert!(violations[0].message.contains("a_test_v3_implementation"));
    }

    #[test]
    fn test_valid_separate_injected_functions() {
        let code = r#"
from pinjected import injected

@injected
def inner_processor(logger, /, data: dict):
    logger.info(f"Processing: {data}")
    return process(data)

@injected
def outer_function(database, inner_processor, /, user_id: str):
    user = database.get_user(user_id)
    return inner_processor(user.data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_regular_function_inside_injected() {
        let code = r#"
from pinjected import injected

@injected
def process_data(logger, /, items: list):
    def helper(item):
        return item * 2
    
    return [helper(item) for item in items]
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_within_conditional() {
        let code = r#"
from pinjected import injected

@injected
def configurable_processor(config, /, data: str):
    if config.debug:
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
}