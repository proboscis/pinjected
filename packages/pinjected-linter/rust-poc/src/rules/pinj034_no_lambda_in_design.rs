//! PINJ034: No lambda or non-decorated functions in design()
//!
//! This rule forbids assigning lambda functions or non-decorated functions to design().
//! Only @injected or @instance decorated functions should be used.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{is_injected_decorator, is_instance_decorator};
use rustpython_ast::{Expr, ExprLambda, Ranged, Stmt, StmtAssign, StmtExpr, StmtWith, WithItem};
use std::collections::HashMap;

pub struct NoLambdaInDesignRule {
    /// Track if we're inside a design() context and the variable name
    in_design_context: Vec<String>,
    /// Track decorated functions in the module
    decorated_functions: HashMap<String, bool>,
}

impl NoLambdaInDesignRule {
    pub fn new() -> Self {
        Self {
            in_design_context: Vec::new(),
            decorated_functions: HashMap::new(),
        }
    }

    /// Check if a with item is a design() call
    fn is_design_call(item: &WithItem) -> Option<String> {
        match &item.context_expr {
            Expr::Call(call) => {
                // Check for design() call
                if let Expr::Name(name) = &*call.func {
                    if name.id.as_str() == "design" {
                        // Get the variable name from 'as' clause
                        if let Some(var) = &item.optional_vars {
                            if let Expr::Name(var_name) = &**var {
                                return Some(var_name.id.to_string());
                            }
                        }
                    }
                }
            }
            _ => {}
        }
        None
    }

    /// Check if an expression is assigning to a design object
    fn is_design_assignment(&self, expr: &Expr) -> Option<String> {
        match expr {
            // Check for d['key'] pattern
            Expr::Subscript(subscript) => {
                if let Expr::Name(name) = &*subscript.value {
                    let name_str = name.id.as_str();
                    if self.in_design_context.contains(&name_str.to_string()) {
                        return Some(name_str.to_string());
                    }
                }
            }
            // Check for d.provide() or similar method calls
            Expr::Attribute(attr) => {
                if let Expr::Name(name) = &*attr.value {
                    let name_str = name.id.as_str();
                    if self.in_design_context.contains(&name_str.to_string()) {
                        return Some(name_str.to_string());
                    }
                }
            }
            _ => {}
        }
        None
    }

    /// Check if a value being assigned is valid (decorated function)
    fn check_value(&self, value: &Expr, design_var: &str) -> Option<Violation> {
        match value {
            // Lambda functions are always invalid
            Expr::Lambda(lambda) => Some(self.create_lambda_violation(lambda, design_var)),

            // Function references need to be checked
            Expr::Name(name) => {
                let func_name = name.id.as_str();
                // Check if this function is decorated
                if let Some(&is_decorated) = self.decorated_functions.get(func_name) {
                    if !is_decorated {
                        return Some(self.create_undecorated_violation(func_name, design_var));
                    }
                }
                // If we don't know about the function, it might be imported or undefined
                None
            }

            // Call expressions might have lambdas as arguments
            Expr::Call(call) => {
                // Check if this is d.provide(value)
                if let Expr::Attribute(attr) = &*call.func {
                    if attr.attr.as_str() == "provide" || attr.attr.as_str() == "override" {
                        // Check arguments
                        for arg in &call.args {
                            if let Some(violation) = self.check_value(arg, design_var) {
                                return Some(violation);
                            }
                        }
                    }
                }
                None
            }

            _ => None,
        }
    }

    fn create_lambda_violation(&self, lambda: &ExprLambda, design_var: &str) -> Violation {
        Violation {
            rule_id: "PINJ034".to_string(),
            message: format!(
                "Lambda function cannot be assigned to design context '{}'. \
                Use @injected or @instance decorated functions instead.",
                design_var
            ),
            offset: lambda.range.start().to_usize(),
            file_path: String::new(),
            severity: Severity::Error,
            fix: None,
        }
    }

    fn create_undecorated_violation(&self, func_name: &str, design_var: &str) -> Violation {
        Violation {
            rule_id: "PINJ034".to_string(),
            message: format!(
                "Function '{}' is not decorated with @injected or @instance. \
                Only decorated functions should be assigned to design context '{}'.",
                func_name, design_var
            ),
            offset: 0, // Will be updated by caller
            file_path: String::new(),
            severity: Severity::Error,
            fix: None,
        }
    }

    /// Pre-scan module to find all decorated functions
    fn scan_module(&mut self, stmts: &[Stmt]) {
        for stmt in stmts {
            match stmt {
                Stmt::FunctionDef(func) => {
                    let is_decorated = func
                        .decorator_list
                        .iter()
                        .any(|d| is_injected_decorator(d) || is_instance_decorator(d));
                    self.decorated_functions
                        .insert(func.name.to_string(), is_decorated);
                }
                Stmt::AsyncFunctionDef(func) => {
                    let is_decorated = func
                        .decorator_list
                        .iter()
                        .any(|d| is_injected_decorator(d) || is_instance_decorator(d));
                    self.decorated_functions
                        .insert(func.name.to_string(), is_decorated);
                }
                Stmt::ClassDef(cls) => {
                    // Scan methods inside classes
                    self.scan_module(&cls.body);
                }
                _ => {}
            }
        }
    }

    /// Check a with statement
    fn check_with_stmt(&mut self, with_stmt: &StmtWith) -> Vec<Violation> {
        let mut violations = Vec::new();
        let mut design_vars = Vec::new();

        // Check if this is a design() context
        for item in &with_stmt.items {
            if let Some(var_name) = Self::is_design_call(item) {
                design_vars.push(var_name.clone());
                self.in_design_context.push(var_name);
            }
        }

        // If we're in a design context, check the body
        if !design_vars.is_empty() {
            violations.extend(self.check_body(&with_stmt.body));
        }

        // Pop the design context
        for _ in design_vars {
            self.in_design_context.pop();
        }

        violations
    }

    /// Check statements in a body
    fn check_body(&mut self, body: &[Stmt]) -> Vec<Violation> {
        let mut violations = Vec::new();

        for stmt in body {
            match stmt {
                // Check assignments like d['key'] = value
                Stmt::Assign(assign) => {
                    violations.extend(self.check_assign(assign));
                }
                // Check expression statements like d.provide(value)
                Stmt::Expr(expr_stmt) => {
                    violations.extend(self.check_expr_stmt(expr_stmt));
                }
                // Nested with statements
                Stmt::With(with_stmt) => {
                    violations.extend(self.check_with_stmt(with_stmt));
                }
                // Check other control flow statements
                Stmt::If(if_stmt) => {
                    violations.extend(self.check_body(&if_stmt.body));
                    violations.extend(self.check_body(&if_stmt.orelse));
                }
                Stmt::For(for_stmt) => {
                    violations.extend(self.check_body(&for_stmt.body));
                    violations.extend(self.check_body(&for_stmt.orelse));
                }
                Stmt::While(while_stmt) => {
                    violations.extend(self.check_body(&while_stmt.body));
                    violations.extend(self.check_body(&while_stmt.orelse));
                }
                Stmt::Try(try_stmt) => {
                    violations.extend(self.check_body(&try_stmt.body));
                    for handler in &try_stmt.handlers {
                        let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler;
                        violations.extend(self.check_body(&h.body));
                    }
                    violations.extend(self.check_body(&try_stmt.orelse));
                    violations.extend(self.check_body(&try_stmt.finalbody));
                }
                _ => {}
            }
        }

        violations
    }

    /// Check assignment statements
    fn check_assign(&self, assign: &StmtAssign) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Check each target
        for target in &assign.targets {
            if let Some(ref design_var) = self.is_design_assignment(target) {
                if let Some(mut violation) = self.check_value(&assign.value, design_var) {
                    violation.offset = assign.range.start().to_usize();
                    violations.push(violation);
                }
            }
        }

        violations
    }

    /// Check expression statements (like d.provide(...))
    fn check_expr_stmt(&self, expr_stmt: &StmtExpr) -> Vec<Violation> {
        let mut violations = Vec::new();

        if let Expr::Call(call) = &*expr_stmt.value {
            if let Expr::Attribute(attr) = &*call.func {
                if let Some(ref design_var) = self.is_design_assignment(&*call.func) {
                    if attr.attr.as_str() == "provide" || attr.attr.as_str() == "override" {
                        // Check arguments
                        for arg in &call.args {
                            if let Some(mut violation) = self.check_value(arg, design_var) {
                                violation.offset = arg.range().start().to_usize();
                                violations.push(violation);
                            }
                        }
                    }
                }
            }
        }

        violations
    }
}

impl LintRule for NoLambdaInDesignRule {
    fn rule_id(&self) -> &str {
        "PINJ034"
    }

    fn description(&self) -> &str {
        "Lambda and non-decorated functions cannot be used in design() context"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut rule = NoLambdaInDesignRule::new();
        let mut violations = Vec::new();

        // First, scan the entire module to find decorated functions
        if let rustpython_ast::Mod::Module(module) = context.ast {
            rule.scan_module(&module.body);
        }

        // Then check the specific statement
        match context.stmt {
            Stmt::With(with_stmt) => {
                let mut with_violations = rule.check_with_stmt(with_stmt);
                for violation in &mut with_violations {
                    violation.file_path = context.file_path.to_string();
                }
                violations.extend(with_violations);
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
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let rule = NoLambdaInDesignRule::new(); // Create new rule for each stmt
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
    fn test_lambda_in_design_subscript() {
        let code = r#"
from pinjected import design

with design() as d:
    d['get_config'] = lambda: {'debug': True}
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ034");
        assert!(violations[0].message.contains("Lambda function"));
    }

    #[test]
    fn test_lambda_in_provide() {
        let code = r#"
from pinjected import design

with design() as d:
    d.provide(lambda: DatabaseConnection())
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ034");
        assert!(violations[0].message.contains("Lambda function"));
    }

    #[test]
    fn test_undecorated_function() {
        let code = r#"
from pinjected import design

def create_logger():
    return Logger()

with design() as d:
    d['logger'] = create_logger
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ034");
        assert!(violations[0].message.contains("not decorated"));
        assert!(violations[0].message.contains("create_logger"));
    }

    #[test]
    fn test_valid_injected_function() {
        let code = r#"
from pinjected import design, injected

@injected
def get_config():
    return {'debug': True}

with design() as d:
    d['config'] = get_config
    d.provide(get_config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_valid_instance_function() {
        let code = r#"
from pinjected import design, instance

@instance
def database_connection(config, /):
    return DatabaseConnection(config)

with design() as d:
    d.provide(database_connection)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_design_context() {
        let code = r#"
from pinjected import design

with design() as d1:
    with design() as d2:
        d2['func'] = lambda: 42
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("d2"));
    }

    #[test]
    fn test_conditional_lambda() {
        let code = r#"
from pinjected import design

with design() as d:
    if debug_mode:
        d['logger'] = lambda: DebugLogger()
    else:
        d['logger'] = lambda: ProductionLogger()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ034"));
    }

    #[test]
    fn test_simple_case() {
        let code = r#"
from pinjected import design

with design() as d:
    d['x'] = lambda: 42
"#;
        let violations = check_code(code);
        println!("Violations found: {}", violations.len());
        for v in &violations {
            println!("  - {} at offset {}: {}", v.rule_id, v.offset, v.message);
        }
        assert_eq!(violations.len(), 1);
    }
}
