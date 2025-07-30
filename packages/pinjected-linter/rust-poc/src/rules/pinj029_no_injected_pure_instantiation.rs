//! PINJ029: No function/class calls inside Injected.pure()
//!
//! Detects when Injected.pure() is used with function calls or class instantiations,
//! which causes code execution during module loading time. These should be replaced
//! with IProxy pattern for lazy evaluation.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, ExprCall, Stmt};

pub struct NoInjectedPureInstantiationRule;

impl NoInjectedPureInstantiationRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if this is a call to Injected.pure()
    fn is_injected_pure_call(call: &ExprCall) -> bool {
        match &*call.func {
            Expr::Attribute(attr) => {
                // Check for Injected.pure
                attr.attr.as_str() == "pure"
                    && match &*attr.value {
                        Expr::Name(name) => name.id.as_str() == "Injected",
                        _ => false,
                    }
            }
            _ => false,
        }
    }

    /// Extract the callable name from an expression
    fn extract_callable_name(expr: &Expr) -> String {
        match expr {
            Expr::Name(name) => name.id.to_string(),
            Expr::Attribute(attr) => {
                let base = Self::extract_callable_name(&attr.value);
                format!("{}.{}", base, attr.attr)
            }
            Expr::Subscript(sub) => Self::extract_callable_name(&sub.value),
            Expr::Call(call) => Self::extract_callable_name(&call.func),
            Expr::Lambda(_) => "lambda".to_string(),
            _ => "<expression>".to_string(),
        }
    }

    /// Format arguments for display
    fn format_arguments(call: &ExprCall) -> String {
        let mut parts = Vec::new();

        // Count positional arguments
        for _ in &call.args {
            parts.push("...".to_string());
        }

        // For keyword arguments in ExprCall, we need to check if there are any
        // This is a simplified version since we don't have full keyword info

        if parts.is_empty() {
            "()".to_string()
        } else {
            format!("({})", parts.join(", "))
        }
    }

    /// Generate the IProxy suggestion
    fn generate_suggestion(call_expr: &Expr) -> String {
        if let Expr::Call(call) = call_expr {
            let callable_name = Self::extract_callable_name(&call.func);
            let args_str = Self::format_arguments(call);
            format!("IProxy({}){}", callable_name, args_str)
        } else {
            "IProxy(...)()".to_string()
        }
    }

    /// Check if the expression is a call expression
    fn check_injected_pure_arg(&self, expr: &Expr, call: &ExprCall) -> Option<Violation> {
        // Check if the argument is a call expression
        if let Expr::Call(inner_call) = expr {
            let callable_name = Self::extract_callable_name(&inner_call.func);
            let suggestion = Self::generate_suggestion(expr);

            Some(Violation {
                rule_id: "PINJ029".to_string(),
                message: format!(
                    "Avoid executing code inside Injected.pure() during module loading. Found: Injected.pure({}(...)). Replace with: {}. Reason: Code execution should be deferred until injection time. If this is intentional, add '# noqa: PINJ029' to suppress this warning.",
                    callable_name, suggestion
                ),
                offset: call.range.start().to_usize(),
                file_path: String::new(),
                severity: Severity::Warning,
                fix: None,
            })
        } else {
            None
        }
    }

    /// Check an expression for violations
    fn check_expression(&self, expr: &Expr) -> Option<Violation> {
        match expr {
            Expr::Call(call) => {
                // Check if this is Injected.pure()
                if Self::is_injected_pure_call(call) {
                    // Check the first argument
                    if let Some(arg) = call.args.first() {
                        return self.check_injected_pure_arg(arg, call);
                    }
                }

                // Recursively check nested expressions
                for arg in &call.args {
                    if let Some(violation) = self.check_expression(arg) {
                        return Some(violation);
                    }
                }

                // Check the function being called
                if let Some(violation) = self.check_expression(&call.func) {
                    return Some(violation);
                }
            }
            Expr::Attribute(attr) => {
                return self.check_expression(&attr.value);
            }
            Expr::Subscript(sub) => {
                if let Some(violation) = self.check_expression(&sub.value) {
                    return Some(violation);
                }
                return self.check_expression(&sub.slice);
            }
            Expr::List(list) => {
                for elem in &list.elts {
                    if let Some(violation) = self.check_expression(elem) {
                        return Some(violation);
                    }
                }
            }
            Expr::Dict(dict) => {
                for key in dict.keys.iter().flatten() {
                    if let Some(violation) = self.check_expression(key) {
                        return Some(violation);
                    }
                }
                for value in &dict.values {
                    if let Some(violation) = self.check_expression(value) {
                        return Some(violation);
                    }
                }
            }
            Expr::BinOp(binop) => {
                if let Some(violation) = self.check_expression(&binop.left) {
                    return Some(violation);
                }
                return self.check_expression(&binop.right);
            }
            Expr::UnaryOp(unaryop) => {
                return self.check_expression(&unaryop.operand);
            }
            _ => {}
        }
        None
    }
}

impl LintRule for NoInjectedPureInstantiationRule {
    fn rule_id(&self) -> &str {
        "PINJ029"
    }

    fn description(&self) -> &str {
        "Avoid executing code inside Injected.pure() during module loading"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::Assign(assign) => {
                // Check assignment expressions
                if let Some(mut violation) = self.check_expression(&assign.value) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            Stmt::Expr(expr_stmt) => {
                // Check standalone expressions
                if let Some(mut violation) = self.check_expression(&expr_stmt.value) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            Stmt::AnnAssign(ann_assign) => {
                // Check annotated assignments
                if let Some(value) = &ann_assign.value {
                    if let Some(mut violation) = self.check_expression(value) {
                        violation.file_path = context.file_path.to_string();
                        violations.push(violation);
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
    use rustpython_ast::Mod;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = NoInjectedPureInstantiationRule::new();
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
    fn test_class_instantiation() {
        let code = r#"
from pinjected import Injected

service = Injected.pure(MyService())
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ029");
        assert!(violations[0].message.contains("MyService"));
        assert!(violations[0].message.contains("IProxy(MyService)"));
    }

    #[test]
    fn test_function_call() {
        let code = r#"
from pinjected import Injected

config = Injected.pure(get_config())
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ029");
        assert!(violations[0].message.contains("get_config"));
        assert!(violations[0].message.contains("IProxy(get_config)"));
    }

    #[test]
    fn test_method_call() {
        let code = r#"
from pinjected import Injected

result = Injected.pure(obj.method())
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ029");
        assert!(violations[0].message.contains("obj.method"));
        assert!(violations[0].message.contains("IProxy(obj.method)"));
    }

    #[test]
    fn test_lambda_call() {
        let code = r#"
from pinjected import Injected

value = Injected.pure((lambda x: x + 1)(5))
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ029");
        assert!(violations[0].message.contains("lambda"));
    }

    #[test]
    fn test_no_call_ok() {
        let code = r#"
from pinjected import Injected

# These should not trigger
ref1 = Injected.pure(42)
ref2 = Injected.pure("string")
ref3 = Injected.pure(factory)
ref4 = Injected.pure(MyClass)
ref5 = Injected.pure(lambda x: x + 1)
ref6 = Injected.pure([1, 2, 3])
ref7 = Injected.pure({"key": "value"})
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_iproxy_pattern_ok() {
        let code = r#"
from pinjected import IProxy

# These should not trigger
service = IProxy(MyService)()
config = IProxy(get_config)()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_calls() {
        let code = r#"
from pinjected import Injected

service = Injected.pure(MyService(get_config()))
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ029");
        // Should detect the outer call
        assert!(violations[0].message.contains("MyService"));
    }

    #[test]
    fn test_with_args() {
        let code = r#"
from pinjected import Injected

db = Injected.pure(DatabaseClient(host="localhost", port=5432))
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ029");
        assert!(violations[0].message.contains("DatabaseClient"));
        assert!(violations[0].message.contains("IProxy(DatabaseClient)"));
    }

    #[test]
    fn test_simple_case() {
        let code = r#"
from pinjected import Injected

service = Injected.pure(MyService())
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ029");
        assert!(violations[0].message.contains("MyService"));
    }
}
