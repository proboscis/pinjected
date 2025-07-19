//! PINJ031: No calls to injected() inside @instance/@injected functions
//!
//! Inside @instance and @injected functions, you're building a dependency graph,
//! not executing code. Calling injected() inside these functions indicates
//! a fundamental misunderstanding of how pinjected works.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::{Expr, ExprCall, Stmt};

pub struct NoInjectedCallsInDecoratorsRule {
    /// Whether we're currently inside an @instance or @injected function
    in_special_function: bool,
    /// Name of the current function for error messages
    current_function: Option<String>,
}

impl NoInjectedCallsInDecoratorsRule {
    pub fn new() -> Self {
        Self {
            in_special_function: false,
            current_function: None,
        }
    }

    /// Check if a call is to the injected() function
    fn is_injected_call(&self, call: &ExprCall) -> bool {
        match &*call.func {
            Expr::Name(name) => name.id.as_str() == "injected",
            Expr::Attribute(attr) => {
                if let Expr::Name(name) = &*attr.value {
                    name.id.as_str() == "pinjected" && attr.attr.as_str() == "injected"
                } else {
                    false
                }
            }
            _ => false,
        }
    }

    /// Check expressions for injected() calls
    fn check_expr(&self, expr: &Expr, file_path: &str, violations: &mut Vec<Violation>) {
        match expr {
            Expr::Call(call) => {
                if self.in_special_function && self.is_injected_call(call) {
                    violations.push(Violation {
                        rule_id: "PINJ031".to_string(),
                        message: format!(
                            "Function '{}' calls injected() inside its body. \
                            @instance and @injected functions build dependency graphs, they don't execute code. \
                            Remove the injected() call - dependencies should be declared as function parameters.",
                            self.current_function.as_ref().unwrap()
                        ),
                        offset: call.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
                // Check arguments
                for arg in &call.args {
                    self.check_expr(arg, file_path, violations);
                }
            }
            // Recurse into other expression types
            Expr::BinOp(binop) => {
                self.check_expr(&binop.left, file_path, violations);
                self.check_expr(&binop.right, file_path, violations);
            }
            Expr::UnaryOp(unaryop) => {
                self.check_expr(&unaryop.operand, file_path, violations);
            }
            Expr::Lambda(lambda) => {
                self.check_expr(&lambda.body, file_path, violations);
            }
            Expr::IfExp(ifexp) => {
                self.check_expr(&ifexp.test, file_path, violations);
                self.check_expr(&ifexp.body, file_path, violations);
                self.check_expr(&ifexp.orelse, file_path, violations);
            }
            Expr::Dict(dict) => {
                for key in &dict.keys {
                    if let Some(k) = key {
                        self.check_expr(k, file_path, violations);
                    }
                }
                for value in &dict.values {
                    self.check_expr(value, file_path, violations);
                }
            }
            Expr::Set(set) => {
                for elem in &set.elts {
                    self.check_expr(elem, file_path, violations);
                }
            }
            Expr::ListComp(comp) => {
                self.check_expr(&comp.elt, file_path, violations);
            }
            Expr::SetComp(comp) => {
                self.check_expr(&comp.elt, file_path, violations);
            }
            Expr::DictComp(comp) => {
                self.check_expr(&comp.key, file_path, violations);
                self.check_expr(&comp.value, file_path, violations);
            }
            Expr::GeneratorExp(comp) => {
                self.check_expr(&comp.elt, file_path, violations);
            }
            Expr::Yield(yield_expr) => {
                if let Some(value) = &yield_expr.value {
                    self.check_expr(value, file_path, violations);
                }
            }
            Expr::YieldFrom(yieldfrom) => {
                self.check_expr(&yieldfrom.value, file_path, violations);
            }
            Expr::Compare(compare) => {
                self.check_expr(&compare.left, file_path, violations);
                for comp in &compare.comparators {
                    self.check_expr(comp, file_path, violations);
                }
            }
            Expr::List(list) => {
                for elem in &list.elts {
                    self.check_expr(elem, file_path, violations);
                }
            }
            Expr::Tuple(tuple) => {
                for elem in &tuple.elts {
                    self.check_expr(elem, file_path, violations);
                }
            }
            Expr::Subscript(subscript) => {
                self.check_expr(&subscript.value, file_path, violations);
                self.check_expr(&subscript.slice, file_path, violations);
            }
            Expr::Starred(starred) => {
                self.check_expr(&starred.value, file_path, violations);
            }
            Expr::Attribute(attr) => {
                self.check_expr(&attr.value, file_path, violations);
            }
            Expr::Await(await_expr) => {
                self.check_expr(&await_expr.value, file_path, violations);
            }
            _ => {}
        }
    }

    /// Check statements for injected() calls
    fn check_stmt(&mut self, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                let is_special = has_injected_decorator(func) || has_instance_decorator(func);
                if is_special {
                    // Enter special function context
                    let old_func = self.current_function.take();
                    let old_in_special = self.in_special_function;

                    self.current_function = Some(func.name.to_string());
                    self.in_special_function = true;

                    // Check function body
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }

                    // Restore context
                    self.current_function = old_func;
                    self.in_special_function = old_in_special;
                } else {
                    // Check nested functions
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                let is_special =
                    has_injected_decorator_async(func) || has_instance_decorator_async(func);
                if is_special {
                    // Enter special function context
                    let old_func = self.current_function.take();
                    let old_in_special = self.in_special_function;

                    self.current_function = Some(func.name.to_string());
                    self.in_special_function = true;

                    // Check function body
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }

                    // Restore context
                    self.current_function = old_func;
                    self.in_special_function = old_in_special;
                } else {
                    // Check nested functions
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }
                }
            }
            Stmt::ClassDef(class) => {
                for stmt in &class.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::Return(ret) => {
                if let Some(value) = &ret.value {
                    self.check_expr(value, file_path, violations);
                }
            }
            Stmt::Delete(del) => {
                for target in &del.targets {
                    self.check_expr(target, file_path, violations);
                }
            }
            Stmt::Assign(assign) => {
                self.check_expr(&assign.value, file_path, violations);
                for target in &assign.targets {
                    self.check_expr(target, file_path, violations);
                }
            }
            Stmt::AugAssign(augassign) => {
                self.check_expr(&augassign.value, file_path, violations);
                self.check_expr(&augassign.target, file_path, violations);
            }
            Stmt::AnnAssign(annassign) => {
                if let Some(value) = &annassign.value {
                    self.check_expr(value, file_path, violations);
                }
            }
            Stmt::For(for_stmt) => {
                self.check_expr(&for_stmt.iter, file_path, violations);
                for stmt in &for_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::AsyncFor(for_stmt) => {
                self.check_expr(&for_stmt.iter, file_path, violations);
                for stmt in &for_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::While(while_stmt) => {
                self.check_expr(&while_stmt.test, file_path, violations);
                for stmt in &while_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &while_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::If(if_stmt) => {
                self.check_expr(&if_stmt.test, file_path, violations);
                for stmt in &if_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &if_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::With(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(&item.context_expr, file_path, violations);
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::AsyncWith(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(&item.context_expr, file_path, violations);
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::Raise(raise_stmt) => {
                if let Some(exc) = &raise_stmt.exc {
                    self.check_expr(exc, file_path, violations);
                }
                if let Some(cause) = &raise_stmt.cause {
                    self.check_expr(cause, file_path, violations);
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for handler in &try_stmt.handlers {
                    match handler {
                        rustpython_ast::ExceptHandler::ExceptHandler(h) => {
                            for stmt in &h.body {
                                self.check_stmt(stmt, file_path, violations);
                            }
                        }
                    }
                }
                for stmt in &try_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &try_stmt.finalbody {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::Assert(assert_stmt) => {
                self.check_expr(&assert_stmt.test, file_path, violations);
                if let Some(msg) = &assert_stmt.msg {
                    self.check_expr(msg, file_path, violations);
                }
            }
            Stmt::Expr(expr_stmt) => {
                self.check_expr(&expr_stmt.value, file_path, violations);
            }
            _ => {}
        }
    }
}

impl LintRule for NoInjectedCallsInDecoratorsRule {
    fn rule_id(&self) -> &str {
        "PINJ031"
    }

    fn description(&self) -> &str {
        "No calls to injected() inside @instance/@injected functions"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Create a mutable instance for stateful tracking
        let mut checker = NoInjectedCallsInDecoratorsRule::new();

        // Check the current statement
        checker.check_stmt(context.stmt, context.file_path, &mut violations);

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
        let rule = NoInjectedCallsInDecoratorsRule::new();
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
    fn test_injected_call_in_instance() {
        let code = r#"
from pinjected import instance, injected

@instance
def my_service():
    # ERROR: Calling injected() inside @instance
    dep = injected(SomeDependency)
    return ServiceImpl(dep)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ031");
        assert!(violations[0].message.contains("my_service"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_injected_call_in_injected() {
        let code = r#"
from pinjected import injected

@injected
def process_data(logger, /, data):
    # ERROR: Calling injected() inside @injected
    processor = injected(DataProcessor)
    return processor.process(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ031");
        assert!(violations[0].message.contains("process_data"));
    }

    #[test]
    fn test_no_violation_outside_special_functions() {
        let code = r#"
from pinjected import injected

def regular_function():
    # OK: Not inside @instance/@injected
    dep = injected(SomeDependency)
    return dep

class MyClass:
    def setup(self):
        # OK: Not inside @instance/@injected
        self.dep = injected(SomeDependency)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_injected_calls() {
        let code = r#"
from pinjected import instance, injected

@instance
def complex_service():
    # ERROR: Multiple injected() calls
    deps = [injected(Dep1), injected(Dep2)]
    
    # ERROR: Nested in dict
    config = {
        'handler': injected(Handler)
    }
    
    return Service(deps, config)
"#;
        let violations = check_code(code);
        assert!(violations.len() >= 3); // Should detect all injected() calls
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ031");
            assert_eq!(v.severity, Severity::Error);
        }
    }

    #[test]
    fn test_async_functions() {
        let code = r#"
from pinjected import instance, injected

@instance
async def async_service():
    # ERROR: injected() in async @instance
    dep = injected(AsyncDep)
    return await dep.start()

@injected
async def async_processor(data):
    # ERROR: injected() in async @injected
    handler = injected(AsyncHandler)
    return await handler.process(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ031");
        }
    }
}
