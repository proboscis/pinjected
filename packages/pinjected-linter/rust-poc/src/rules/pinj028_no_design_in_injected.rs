//! PINJ028: No design() usage inside @injected functions
//!
//! The design() context manager should not be used inside @injected functions.
//! design() is for configuration, not runtime execution.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::is_injected_decorator;
use rustpython_ast::{Expr, Stmt, StmtAsyncFunctionDef, StmtFunctionDef, StmtWith, StmtAsyncWith};

pub struct NoDesignInInjectedRule {
    in_injected_function: Vec<String>,
}

impl NoDesignInInjectedRule {
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

    /// Check if an expression is a call to design()
    fn is_design_call(expr: &Expr) -> bool {
        match expr {
            Expr::Call(call) => {
                match &*call.func {
                    Expr::Name(name) => name.id.as_str() == "design",
                    Expr::Attribute(attr) => {
                        if attr.attr.as_str() == "design" {
                            if let Expr::Name(module) = &*attr.value {
                                return module.id.as_str() == "pinjected";
                            }
                        }
                        false
                    }
                    _ => false,
                }
            }
            _ => false,
        }
    }

    /// Check a with statement for design() usage
    fn check_with_statement(&self, with_stmt: &StmtWith, parent_name: &str) -> Option<Violation> {
        if self.in_injected_function.is_empty() {
            return None;
        }

        for item in &with_stmt.items {
            if Self::is_design_call(&item.context_expr) {
                return Some(Violation {
                    rule_id: "PINJ028".to_string(),
                    message: format!(
                        "design() context manager cannot be used inside @injected function '{}'. \
                        design() is for configuring dependency blueprints outside of execution context. \
                        Move the design() configuration outside of @injected functions.",
                        parent_name
                    ),
                    offset: with_stmt.range.start().to_usize(),
                    file_path: String::new(),
                    severity: Severity::Error,
                });
            }
        }
        None
    }

    /// Check an async with statement for design() usage
    fn check_async_with_statement(&self, with_stmt: &StmtAsyncWith, parent_name: &str) -> Option<Violation> {
        if self.in_injected_function.is_empty() {
            return None;
        }

        for item in &with_stmt.items {
            if Self::is_design_call(&item.context_expr) {
                return Some(Violation {
                    rule_id: "PINJ028".to_string(),
                    message: format!(
                        "design() context manager cannot be used inside @injected function '{}'. \
                        design() is for configuring dependency blueprints outside of execution context. \
                        Move the design() configuration outside of @injected functions.",
                        parent_name
                    ),
                    offset: with_stmt.range.start().to_usize(),
                    file_path: String::new(),
                    severity: Severity::Error,
                });
            }
        }
        None
    }

    /// Check a function body for design() usage
    fn check_function_body(&mut self, body: &[Stmt], func_name: &str) -> Vec<Violation> {
        let mut violations = Vec::new();

        // We're now inside an @injected function
        self.in_injected_function.push(func_name.to_string());

        for stmt in body {
            match stmt {
                Stmt::With(with_stmt) => {
                    if let Some(violation) = self.check_with_statement(with_stmt, func_name) {
                        violations.push(violation);
                    }
                    // Recursively check the body
                    violations.extend(self.check_function_body(&with_stmt.body, func_name));
                }
                Stmt::AsyncWith(with_stmt) => {
                    if let Some(violation) = self.check_async_with_statement(with_stmt, func_name) {
                        violations.push(violation);
                    }
                    // Recursively check the body
                    violations.extend(self.check_function_body(&with_stmt.body, func_name));
                }
                Stmt::FunctionDef(func) => {
                    // Check nested functions
                    violations.extend(self.check_function_body(&func.body, func.name.as_str()));
                }
                Stmt::AsyncFunctionDef(func) => {
                    // Check nested functions
                    violations.extend(self.check_function_body(&func.body, func.name.as_str()));
                }
                Stmt::ClassDef(cls) => {
                    // Check methods inside classes
                    violations.extend(self.check_function_body(&cls.body, &format!("{}.{}", func_name, cls.name)));
                }
                Stmt::If(if_stmt) => {
                    violations.extend(self.check_function_body(&if_stmt.body, func_name));
                    violations.extend(self.check_function_body(&if_stmt.orelse, func_name));
                }
                Stmt::While(while_stmt) => {
                    violations.extend(self.check_function_body(&while_stmt.body, func_name));
                    violations.extend(self.check_function_body(&while_stmt.orelse, func_name));
                }
                Stmt::For(for_stmt) => {
                    violations.extend(self.check_function_body(&for_stmt.body, func_name));
                    violations.extend(self.check_function_body(&for_stmt.orelse, func_name));
                }
                Stmt::Try(try_stmt) => {
                    violations.extend(self.check_function_body(&try_stmt.body, func_name));
                    for handler in &try_stmt.handlers {
                        if let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler {
                            violations.extend(self.check_function_body(&h.body, func_name));
                        }
                    }
                    violations.extend(self.check_function_body(&try_stmt.orelse, func_name));
                    violations.extend(self.check_function_body(&try_stmt.finalbody, func_name));
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

impl LintRule for NoDesignInInjectedRule {
    fn rule_id(&self) -> &str {
        "PINJ028"
    }

    fn description(&self) -> &str {
        "design() context manager cannot be used inside @injected functions"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut rule = NoDesignInInjectedRule::new();
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
        let rule = NoDesignInInjectedRule::new();
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
    fn test_design_in_injected() {
        let code = r#"
from pinjected import injected, design

@injected
async def a_test_v3_implementation(logger, /, sketch_path: str) -> dict:
    with design() as d:
        @injected
        async def a_tracking_sketch_to_line_art(
            a_auto_cached_sketch_to_line_art,
            /,
            sketch_path: str
        ) -> dict:
            return await a_auto_cached_sketch_to_line_art(sketch_path=sketch_path)
        
        d.provide(a_tracking_sketch_to_line_art)
    
    result = await a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ028");
        assert!(violations[0].message.contains("a_test_v3_implementation"));
        assert!(violations[0].message.contains("design()"));
    }

    #[test]
    fn test_design_with_pinjected_module() {
        let code = r#"
from pinjected import injected
import pinjected

@injected
def configure_dynamically(config_loader, /, env: str):
    config = config_loader.load(env)
    
    with pinjected.design() as d:
        if config.use_mock:
            d.provide(mock_database)
        else:
            d.provide(real_database)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ028");
        assert!(violations[0].message.contains("configure_dynamically"));
    }

    #[test]
    fn test_design_outside_injected() {
        let code = r#"
from pinjected import injected, design

def configure_app(use_mock: bool = False):
    with design() as d:
        d.provide(a_tracking_sketch_to_line_art)
        d.provide(a_auto_cached_sketch_to_line_art)
        
        if use_mock:
            d.provide(mock_database)
        else:
            d.provide(real_database)
    
    return d.to_graph()

@injected
async def a_test_v3_implementation(
    a_tracking_sketch_to_line_art,
    logger,
    /,
    sketch_path: str
) -> dict:
    result = a_tracking_sketch_to_line_art(sketch_path=sketch_path)
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_design_in_conditional() {
        let code = r#"
from pinjected import injected, design

@injected
def dynamic_config(env_var, /, mode: str):
    if mode == "test":
        with design() as d:
            d.provide(test_database)
            return d.to_graph()
    else:
        return production_graph()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ028");
        assert!(violations[0].message.contains("dynamic_config"));
    }

    #[test]
    fn test_regular_with_in_injected() {
        let code = r#"
from pinjected import injected

@injected
def file_processor(file_system, /, path: str):
    with open(path) as f:
        content = f.read()
    
    with file_system.lock():
        result = process(content)
    
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}