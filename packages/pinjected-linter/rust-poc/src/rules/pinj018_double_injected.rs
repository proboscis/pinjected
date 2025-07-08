//! PINJ018: Don't call injected() on already @injected decorated functions
//!
//! If a function is already decorated with @injected, calling injected() on it
//! is redundant and incorrect. The @injected decorator already wraps the function
//! with the necessary injection logic.
//!
//! Bad:
//! ```python
//! @injected
//! def my_function(...): ...
//!
//! # Wrong - my_function is already @injected
//! result = injected(my_function).proxy(...)
//! ```
//!
//! Good:
//! ```python
//! @injected
//! def my_function(...): ...
//!
//! # Correct - use the already decorated function
//! result = my_function.proxy(...)
//! ```

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Expr, ExprCall, Mod, Stmt};
use std::collections::HashSet;

pub struct DoubleInjectedRule {
    /// All @injected function names in the module
    injected_functions: HashSet<String>,
}

impl DoubleInjectedRule {
    pub fn new() -> Self {
        Self {
            injected_functions: HashSet::new(),
        }
    }

    /// Collect all @injected functions in the module
    fn collect_injected_functions(&mut self, ast: &Mod) {
        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.collect_from_stmt(stmt);
                }
            }
            _ => {}
        }
    }

    fn collect_from_stmt(&mut self, stmt: &Stmt) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    self.injected_functions.insert(func.name.to_string());
                }
                // Check nested functions
                for stmt in &func.body {
                    self.collect_from_stmt(stmt);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    self.injected_functions.insert(func.name.to_string());
                }
                // Check nested functions
                for stmt in &func.body {
                    self.collect_from_stmt(stmt);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.collect_from_stmt(stmt);
                }
            }
            _ => {}
        }
    }

    /// Check if a call is to injected() with an already @injected function
    fn check_injected_call(
        &self,
        call: &ExprCall,
        file_path: &str,
        violations: &mut Vec<Violation>,
    ) {
        // Check if this is a call to injected()
        let is_injected_call = match &*call.func {
            Expr::Name(name) => name.id.as_str() == "injected",
            Expr::Attribute(attr) => {
                if let Expr::Name(name) = &*attr.value {
                    name.id.as_str() == "pinjected" && attr.attr.as_str() == "injected"
                } else {
                    false
                }
            }
            _ => false,
        };

        if !is_injected_call {
            return;
        }
        

        // Check if the argument is an already @injected function
        if call.args.len() == 1 {
            if let Expr::Name(name) = &call.args[0] {
                if self.injected_functions.contains(name.id.as_str()) {
                    violations.push(Violation {
                        rule_id: "PINJ018".to_string(),
                        message: format!(
                            "Function '{}' is already decorated with @injected. \
                            Calling injected() on it is redundant and incorrect. \
                            Use '{}.proxy(...)' directly instead of 'injected({}).proxy(...)'.",
                            name.id, name.id, name.id
                        ),
                        offset: call.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                    });
                }
            }
        }
    }

    /// Check expressions for injected() calls
    fn check_expr(&self, expr: &Expr, file_path: &str, violations: &mut Vec<Violation>) {
        match expr {
            Expr::Call(call) => {
                self.check_injected_call(call, file_path, violations);

                // Also check if this is a method call on injected()
                if let Expr::Attribute(attr) = &*call.func {
                    // Check the value of the attribute (what the method is called on)
                    self.check_expr(&attr.value, file_path, violations);
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
            _ => {}
        }
    }

    /// Check statements for injected() calls
    fn check_stmt(&self, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                for stmt in &func.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                for stmt in &func.body {
                    self.check_stmt(stmt, file_path, violations);
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

impl LintRule for DoubleInjectedRule {
    fn rule_id(&self) -> &str {
        "PINJ018"
    }

    fn description(&self) -> &str {
        "Don't call injected() on already @injected decorated functions"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Create a mutable instance for stateful tracking
        let mut checker = DoubleInjectedRule::new();

        // First pass: collect all @injected functions from the entire AST
        checker.collect_injected_functions(context.ast);

        // If no @injected functions, nothing to check
        if checker.injected_functions.is_empty() {
            return violations;
        }


        // Second pass: check only the current statement
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
        let rule = DoubleInjectedRule::new();
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
    fn test_double_injected_basic() {
        let code = r#"
from pinjected import injected

@injected
def a_user_registration_workflow(
    create_user_fn,
    logger,
    /,
    user_data: list[dict]
) -> None:
    for data in user_data:
        create_user_fn(
            user_id=data["id"],
            name=data["name"],
            email_address=data["email"]
        )

# Wrong - calling injected() on already @injected function
test_workflow = injected(a_user_registration_workflow).proxy(
    user_data=[
        {"id": "1", "name": "Alice", "email": "alice@example.com"},
    ]
)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ018");
        assert!(violations[0]
            .message
            .contains("already decorated with @injected"));
        assert!(violations[0]
            .message
            .contains("a_user_registration_workflow"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_double_injected_pinjected_module() {
        let code = r#"
import pinjected

@pinjected.injected
def process_data(data: str) -> str:
    return data.upper()

# Wrong - using pinjected.injected() on already decorated function
result = pinjected.injected(process_data).proxy()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ018");
        assert!(violations[0].message.contains("process_data"));
    }

    #[test]
    fn test_no_violation_undecorated_function() {
        let code = r#"
from pinjected import injected

def regular_function(data: str) -> str:
    return data.upper()

# OK - regular_function is not decorated with @injected
result = injected(regular_function).proxy()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_violation_direct_proxy_call() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data: str) -> str:
    return data.upper()

# OK - calling proxy() directly on decorated function
result = process_data.proxy()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_double_injected_in_assignment() {
        let code = r#"
from pinjected import injected

@injected
async def a_fetch_data(url: str) -> dict:
    return {"data": "example"}

# Wrong in various contexts
data_fetcher = injected(a_fetch_data).proxy(url="https://example.com")
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ018");
        assert!(violations[0].message.contains("a_fetch_data"));
    }

    #[test]
    fn test_double_injected_nested_function() {
        let code = r#"
from pinjected import injected

def outer():
    @injected
    def inner(data: str) -> str:
        return data
    
    # Wrong - inner is already @injected
    return injected(inner).proxy()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ018");
        assert!(violations[0].message.contains("inner"));
    }
}
