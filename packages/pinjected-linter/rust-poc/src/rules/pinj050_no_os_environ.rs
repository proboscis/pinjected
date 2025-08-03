//! PINJ050: Forbid use of os.environ
//!
//! os.environ should not be used directly in pinjected code.
//! Instead, use dependency injection to inject configuration values.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{
    Expr, Mod, Stmt, Ranged,
};

pub struct NoOsEnvironRule;

impl NoOsEnvironRule {
    pub fn new() -> Self {
        Self
    }
    
    /// Check if an expression is accessing os.environ
    fn is_os_environ_access(expr: &Expr) -> bool {
        match expr {
            Expr::Attribute(attr) => {
                if attr.attr.as_str() == "environ" {
                    match &*attr.value {
                        Expr::Name(name) => name.id.as_str() == "os",
                        _ => false,
                    }
                } else {
                    false
                }
            }
            _ => false,
        }
    }
    
    /// Check expressions recursively for os.environ usage
    fn check_expr(&self, expr: &Expr, violations: &mut Vec<Violation>, file_path: &str, source: &str) {
        match expr {
            // Direct os.environ access
            Expr::Attribute(attr) if Self::is_os_environ_access(expr) => {
                violations.push(Violation {
                    rule_id: "PINJ050".to_string(),
                    message: "Use of os.environ is forbidden. Use pinjected dependency injection for configuration values instead.".to_string(),
                    offset: expr.range().start().to_usize(),
                    file_path: file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
            
            // Check os.environ.get() calls
            Expr::Call(call) => {
                if let Expr::Attribute(attr) = &*call.func {
                    if matches!(attr.attr.as_str(), "get" | "setdefault" | "pop") {
                        if Self::is_os_environ_access(&attr.value) {
                            violations.push(Violation {
                                rule_id: "PINJ050".to_string(),
                                message: format!(
                                    "Use of os.environ.{} is forbidden. Use pinjected dependency injection for configuration values instead.",
                                    attr.attr
                                ),
                                offset: call.func.range().start().to_usize(),
                                file_path: file_path.to_string(),
                                severity: Severity::Error,
                                fix: None,
                            });
                        }
                    }
                }
                
                // Recursively check arguments
                for arg in &call.args {
                    self.check_expr(arg, violations, file_path, source);
                }
                for keyword in &call.keywords {
                    self.check_expr(&keyword.value, violations, file_path, source);
                }
            }
            
            // Check os.environ[key] access
            Expr::Subscript(sub) => {
                if Self::is_os_environ_access(&sub.value) {
                    violations.push(Violation {
                        rule_id: "PINJ050".to_string(),
                        message: "Use of os.environ[...] is forbidden. Use pinjected dependency injection for configuration values instead.".to_string(),
                        offset: sub.value.range().start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
                
                // Recursively check the subscript expression
                self.check_expr(&sub.slice, violations, file_path, source);
            }
            
            // Recursively check other expression types
            Expr::BinOp(binop) => {
                self.check_expr(&binop.left, violations, file_path, source);
                self.check_expr(&binop.right, violations, file_path, source);
            }
            Expr::UnaryOp(unop) => {
                self.check_expr(&unop.operand, violations, file_path, source);
            }
            Expr::Lambda(lambda) => {
                self.check_expr(&lambda.body, violations, file_path, source);
            }
            Expr::IfExp(ifexp) => {
                self.check_expr(&ifexp.test, violations, file_path, source);
                self.check_expr(&ifexp.body, violations, file_path, source);
                self.check_expr(&ifexp.orelse, violations, file_path, source);
            }
            Expr::Dict(dict) => {
                for key in dict.keys.iter().flatten() {
                    self.check_expr(key, violations, file_path, source);
                }
                for value in &dict.values {
                    self.check_expr(value, violations, file_path, source);
                }
            }
            Expr::Set(set) => {
                for elem in &set.elts {
                    self.check_expr(elem, violations, file_path, source);
                }
            }
            Expr::ListComp(comp) => {
                self.check_expr(&comp.elt, violations, file_path, source);
                for generator in &comp.generators {
                    self.check_expr(&generator.iter, violations, file_path, source);
                }
            }
            Expr::SetComp(comp) => {
                self.check_expr(&comp.elt, violations, file_path, source);
                for generator in &comp.generators {
                    self.check_expr(&generator.iter, violations, file_path, source);
                }
            }
            Expr::DictComp(comp) => {
                self.check_expr(&comp.key, violations, file_path, source);
                self.check_expr(&comp.value, violations, file_path, source);
                for generator in &comp.generators {
                    self.check_expr(&generator.iter, violations, file_path, source);
                }
            }
            Expr::GeneratorExp(comp) => {
                self.check_expr(&comp.elt, violations, file_path, source);
                for generator in &comp.generators {
                    self.check_expr(&generator.iter, violations, file_path, source);
                }
            }
            Expr::Await(await_expr) => {
                self.check_expr(&await_expr.value, violations, file_path, source);
            }
            Expr::Yield(yield_expr) => {
                if let Some(value) = &yield_expr.value {
                    self.check_expr(value, violations, file_path, source);
                }
            }
            Expr::YieldFrom(yield_from) => {
                self.check_expr(&yield_from.value, violations, file_path, source);
            }
            Expr::Compare(compare) => {
                self.check_expr(&compare.left, violations, file_path, source);
                for comp in &compare.comparators {
                    self.check_expr(comp, violations, file_path, source);
                }
            }
            Expr::FormattedValue(fval) => {
                self.check_expr(&fval.value, violations, file_path, source);
                if let Some(format_spec) = &fval.format_spec {
                    self.check_expr(format_spec, violations, file_path, source);
                }
            }
            Expr::JoinedStr(jstr) => {
                for value in &jstr.values {
                    self.check_expr(value, violations, file_path, source);
                }
            }
            Expr::Slice(slice) => {
                if let Some(lower) = &slice.lower {
                    self.check_expr(lower, violations, file_path, source);
                }
                if let Some(upper) = &slice.upper {
                    self.check_expr(upper, violations, file_path, source);
                }
                if let Some(step) = &slice.step {
                    self.check_expr(step, violations, file_path, source);
                }
            }
            Expr::Tuple(tuple) => {
                for elem in &tuple.elts {
                    self.check_expr(elem, violations, file_path, source);
                }
            }
            Expr::List(list) => {
                for elem in &list.elts {
                    self.check_expr(elem, violations, file_path, source);
                }
            }
            Expr::Starred(starred) => {
                self.check_expr(&starred.value, violations, file_path, source);
            }
            Expr::NamedExpr(named) => {
                self.check_expr(&named.target, violations, file_path, source);
                self.check_expr(&named.value, violations, file_path, source);
            }
            _ => {}
        }
    }
    
    /// Check statements recursively
    fn check_stmt(&self, stmt: &Stmt, violations: &mut Vec<Violation>, file_path: &str, source: &str) {
        match stmt {
            Stmt::FunctionDef(func) => {
                for stmt in &func.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for decorator in &func.decorator_list {
                    self.check_expr(decorator, violations, file_path, source);
                }
                if let Some(returns) = &func.returns {
                    self.check_expr(returns, violations, file_path, source);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                for stmt in &func.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for decorator in &func.decorator_list {
                    self.check_expr(decorator, violations, file_path, source);
                }
                if let Some(returns) = &func.returns {
                    self.check_expr(returns, violations, file_path, source);
                }
            }
            Stmt::ClassDef(class) => {
                for stmt in &class.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for decorator in &class.decorator_list {
                    self.check_expr(decorator, violations, file_path, source);
                }
            }
            Stmt::Return(ret) => {
                if let Some(value) = &ret.value {
                    self.check_expr(value, violations, file_path, source);
                }
            }
            Stmt::Delete(del) => {
                for target in &del.targets {
                    self.check_expr(target, violations, file_path, source);
                }
            }
            Stmt::Assign(assign) => {
                self.check_expr(&assign.value, violations, file_path, source);
                for target in &assign.targets {
                    self.check_expr(target, violations, file_path, source);
                }
            }
            Stmt::AugAssign(aug) => {
                self.check_expr(&aug.target, violations, file_path, source);
                self.check_expr(&aug.value, violations, file_path, source);
            }
            Stmt::AnnAssign(ann) => {
                self.check_expr(&ann.target, violations, file_path, source);
                self.check_expr(&ann.annotation, violations, file_path, source);
                if let Some(value) = &ann.value {
                    self.check_expr(value, violations, file_path, source);
                }
            }
            Stmt::For(for_stmt) => {
                self.check_expr(&for_stmt.iter, violations, file_path, source);
                for stmt in &for_stmt.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(stmt, violations, file_path, source);
                }
            }
            Stmt::AsyncFor(for_stmt) => {
                self.check_expr(&for_stmt.iter, violations, file_path, source);
                for stmt in &for_stmt.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(stmt, violations, file_path, source);
                }
            }
            Stmt::While(while_stmt) => {
                self.check_expr(&while_stmt.test, violations, file_path, source);
                for stmt in &while_stmt.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for stmt in &while_stmt.orelse {
                    self.check_stmt(stmt, violations, file_path, source);
                }
            }
            Stmt::If(if_stmt) => {
                self.check_expr(&if_stmt.test, violations, file_path, source);
                for stmt in &if_stmt.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for stmt in &if_stmt.orelse {
                    self.check_stmt(stmt, violations, file_path, source);
                }
            }
            Stmt::With(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(&item.context_expr, violations, file_path, source);
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
            }
            Stmt::AsyncWith(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(&item.context_expr, violations, file_path, source);
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
            }
            Stmt::Match(match_stmt) => {
                self.check_expr(&match_stmt.subject, violations, file_path, source);
                for case in &match_stmt.cases {
                    for stmt in &case.body {
                        self.check_stmt(stmt, violations, file_path, source);
                    }
                }
            }
            Stmt::Raise(raise_stmt) => {
                if let Some(exc) = &raise_stmt.exc {
                    self.check_expr(exc, violations, file_path, source);
                }
                if let Some(cause) = &raise_stmt.cause {
                    self.check_expr(cause, violations, file_path, source);
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for handler in &try_stmt.handlers {
                    if let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler {
                        if let Some(type_) = &h.type_ {
                            self.check_expr(type_, violations, file_path, source);
                        }
                        for stmt in &h.body {
                            self.check_stmt(stmt, violations, file_path, source);
                        }
                    }
                }
                for stmt in &try_stmt.orelse {
                    self.check_stmt(stmt, violations, file_path, source);
                }
                for stmt in &try_stmt.finalbody {
                    self.check_stmt(stmt, violations, file_path, source);
                }
            }
            Stmt::Assert(assert_stmt) => {
                self.check_expr(&assert_stmt.test, violations, file_path, source);
                if let Some(msg) = &assert_stmt.msg {
                    self.check_expr(msg, violations, file_path, source);
                }
            }
            Stmt::Expr(expr_stmt) => {
                self.check_expr(&expr_stmt.value, violations, file_path, source);
            }
            _ => {}
        }
    }
}

impl LintRule for NoOsEnvironRule {
    fn rule_id(&self) -> &str {
        "PINJ050"
    }

    fn description(&self) -> &str {
        "os.environ should not be used directly. Use dependency injection for configuration values."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.check_stmt(stmt, &mut violations, context.file_path, context.source);
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
        let rule = NoOsEnvironRule::new();
        
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
    fn test_direct_os_environ_access() {
        let code = r#"
import os

def get_config():
    return os.environ
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ050");
        assert!(violations[0].message.contains("os.environ is forbidden"));
    }

    #[test]
    fn test_os_environ_get() {
        let code = r#"
import os

def get_config():
    api_key = os.environ.get('API_KEY')
    return api_key
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ050");
        assert!(violations[0].message.contains("os.environ.get is forbidden"));
    }

    #[test]
    fn test_os_environ_subscript() {
        let code = r#"
import os

def get_config():
    return os.environ['DATABASE_URL']
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ050");
        assert!(violations[0].message.contains("os.environ[...] is forbidden"));
    }

    #[test]
    fn test_os_environ_setdefault() {
        let code = r#"
import os

def setup():
    os.environ.setdefault('DJANGO_SETTINGS', 'dev')
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ050");
        assert!(violations[0].message.contains("os.environ.setdefault is forbidden"));
    }

    #[test]
    fn test_no_violation_without_os_environ() {
        let code = r#"
from pinjected import injected

@injected
def get_config(config: dict, /):
    return config['API_KEY']
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_expressions() {
        let code = r#"
import os

def get_all_config():
    return {
        'api_key': os.environ.get('API_KEY', 'default'),
        'db_url': os.environ['DATABASE_URL'] if 'DATABASE_URL' in os.environ else 'sqlite:///db.sqlite'
    }
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);  // get, subscript, and attribute access
    }

    #[test]
    fn test_in_class_method() {
        let code = r#"
import os

class Config:
    def __init__(self):
        self.api_key = os.environ.get('API_KEY')
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ050");
    }

    #[test]
    fn test_lambda_expression() {
        let code = r#"
import os

configs = list(map(lambda key: os.environ.get(key), ['API_KEY', 'DB_URL']))
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
    }
}