//! PINJ004: Direct instance call detection
//!
//! @instance decorated functions cannot be called directly.
//! They should be used in design() or injected as dependencies.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::ast_walker::{collect_instance_callable_functions, collect_instance_functions};
use rustpython_ast::{Expr, ExprCall, Stmt};
use std::collections::HashSet;

pub struct DirectInstanceCallRule {
    /// Tracks if we're inside a design() call
    in_design_call: bool,
    design_level: usize,
}

impl DirectInstanceCallRule {
    pub fn new() -> Self {
        Self {
            in_design_call: false,
            design_level: 0,
        }
    }

    fn check_call(
        &mut self,
        call: &ExprCall,
        instance_functions: &HashSet<String>,
        instance_callable_functions: &HashSet<String>,
        file_path: &str,
        violations: &mut Vec<Violation>,
    ) {
        // Check if this is a design() call
        if let Expr::Name(name) = &*call.func {
            if name.id.as_str() == "design" {
                self.design_level += 1;
                self.in_design_call = true;
                // Check arguments recursively
                for arg in &call.args {
                    self.check_expr(
                        arg,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                self.design_level -= 1;
                if self.design_level == 0 {
                    self.in_design_call = false;
                }
                return;
            }
        }

        // Skip if we're inside a design() call
        if self.in_design_call {
            // Still need to check nested calls
            for arg in &call.args {
                self.check_expr(
                    arg,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            return;
        }

        // Check for direct instance function calls
        if let Expr::Name(name) = &*call.func {
            let func_name = name.id.to_string();
            // Skip if it's a callable instance function
            if instance_functions.contains(&func_name)
                && !instance_callable_functions.contains(&func_name)
            {
                violations.push(Violation {
                    rule_id: "PINJ004".to_string(),
                    message: format!(
                        "Direct call to @instance function '{}'. \
                        @instance functions should be used in design() or as dependencies, not called directly.",
                        name.id
                    ),
                    offset: call.range.start().to_usize(),
                    file_path: file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }

        // Check arguments recursively
        for arg in &call.args {
            self.check_expr(
                arg,
                instance_functions,
                instance_callable_functions,
                file_path,
                violations,
            );
        }
    }

    fn check_expr(
        &mut self,
        expr: &Expr,
        instance_functions: &HashSet<String>,
        instance_callable_functions: &HashSet<String>,
        file_path: &str,
        violations: &mut Vec<Violation>,
    ) {
        match expr {
            Expr::Call(call) => {
                self.check_call(
                    call,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            // Check other expression types that might contain calls
            Expr::BinOp(binop) => {
                self.check_expr(
                    &binop.left,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                self.check_expr(
                    &binop.right,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::UnaryOp(unaryop) => {
                self.check_expr(
                    &unaryop.operand,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::Lambda(lambda) => {
                self.check_expr(
                    &lambda.body,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::IfExp(ifexp) => {
                self.check_expr(
                    &ifexp.test,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                self.check_expr(
                    &ifexp.body,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                self.check_expr(
                    &ifexp.orelse,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::Dict(dict) => {
                for key in &dict.keys {
                    if let Some(k) = key {
                        self.check_expr(
                            k,
                            instance_functions,
                            instance_callable_functions,
                            file_path,
                            violations,
                        );
                    }
                }
                for value in &dict.values {
                    self.check_expr(
                        value,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Expr::Set(set) => {
                for elem in &set.elts {
                    self.check_expr(
                        elem,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Expr::ListComp(comp) => {
                self.check_expr(
                    &comp.elt,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                // Could check generators too, but keeping it simple for now
            }
            Expr::SetComp(comp) => {
                self.check_expr(
                    &comp.elt,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::GeneratorExp(comp) => {
                self.check_expr(
                    &comp.elt,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::DictComp(comp) => {
                self.check_expr(
                    &comp.key,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                self.check_expr(
                    &comp.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::Await(await_expr) => {
                self.check_expr(
                    &await_expr.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::Yield(yield_expr) => {
                if let Some(value) = &yield_expr.value {
                    self.check_expr(
                        value,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Expr::YieldFrom(yieldfrom) => {
                self.check_expr(
                    &yieldfrom.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::Compare(compare) => {
                self.check_expr(
                    &compare.left,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                for comp in &compare.comparators {
                    self.check_expr(
                        comp,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Expr::List(list) => {
                for elem in &list.elts {
                    self.check_expr(
                        elem,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Expr::Tuple(tuple) => {
                for elem in &tuple.elts {
                    self.check_expr(
                        elem,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Expr::Subscript(subscript) => {
                self.check_expr(
                    &subscript.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                self.check_expr(
                    &subscript.slice,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::Starred(starred) => {
                self.check_expr(
                    &starred.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Expr::Attribute(attr) => {
                self.check_expr(
                    &attr.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            _ => {} // Other expression types don't contain calls
        }
    }

    fn check_stmt(
        &mut self,
        stmt: &Stmt,
        instance_functions: &HashSet<String>,
        instance_callable_functions: &HashSet<String>,
        file_path: &str,
        violations: &mut Vec<Violation>,
    ) {
        match stmt {
            Stmt::FunctionDef(func) => {
                // Check function body
                for stmt in &func.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                // Check decorators
                for decorator in &func.decorator_list {
                    self.check_expr(
                        decorator,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                // Check function body
                for stmt in &func.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                // Check decorators
                for decorator in &func.decorator_list {
                    self.check_expr(
                        decorator,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::ClassDef(class) => {
                // Check class body
                for stmt in &class.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::Return(ret) => {
                if let Some(value) = &ret.value {
                    self.check_expr(
                        value,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::Delete(del) => {
                for target in &del.targets {
                    self.check_expr(
                        target,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::Assign(assign) => {
                self.check_expr(
                    &assign.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                for target in &assign.targets {
                    self.check_expr(
                        target,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::AugAssign(augassign) => {
                self.check_expr(
                    &augassign.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                self.check_expr(
                    &augassign.target,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            Stmt::AnnAssign(annassign) => {
                if let Some(value) = &annassign.value {
                    self.check_expr(
                        value,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::For(for_stmt) => {
                self.check_expr(
                    &for_stmt.iter,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                for stmt in &for_stmt.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::AsyncFor(for_stmt) => {
                self.check_expr(
                    &for_stmt.iter,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                for stmt in &for_stmt.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::While(while_stmt) => {
                self.check_expr(
                    &while_stmt.test,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                for stmt in &while_stmt.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for stmt in &while_stmt.orelse {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::If(if_stmt) => {
                self.check_expr(
                    &if_stmt.test,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                for stmt in &if_stmt.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for stmt in &if_stmt.orelse {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::With(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(
                        &item.context_expr,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::AsyncWith(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(
                        &item.context_expr,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::Raise(raise_stmt) => {
                if let Some(exc) = &raise_stmt.exc {
                    self.check_expr(
                        exc,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                if let Some(cause) = &raise_stmt.cause {
                    self.check_expr(
                        cause,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for handler in &try_stmt.handlers {
                    match handler {
                        rustpython_ast::ExceptHandler::ExceptHandler(h) => {
                            for stmt in &h.body {
                                self.check_stmt(
                                    stmt,
                                    instance_functions,
                                    instance_callable_functions,
                                    file_path,
                                    violations,
                                );
                            }
                        }
                    }
                }
                for stmt in &try_stmt.orelse {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
                for stmt in &try_stmt.finalbody {
                    self.check_stmt(
                        stmt,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::Assert(assert_stmt) => {
                self.check_expr(
                    &assert_stmt.test,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
                if let Some(msg) = &assert_stmt.msg {
                    self.check_expr(
                        msg,
                        instance_functions,
                        instance_callable_functions,
                        file_path,
                        violations,
                    );
                }
            }
            Stmt::Expr(expr_stmt) => {
                self.check_expr(
                    &expr_stmt.value,
                    instance_functions,
                    instance_callable_functions,
                    file_path,
                    violations,
                );
            }
            _ => {} // Other statement types don't contain expressions
        }
    }
}

impl LintRule for DirectInstanceCallRule {
    fn rule_id(&self) -> &str {
        "PINJ004"
    }

    fn description(&self) -> &str {
        "@instance decorated functions cannot be called directly"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // First, collect all @instance functions in the module
        let instance_functions = collect_instance_functions(context.ast);

        if instance_functions.is_empty() {
            return violations; // No instance functions, nothing to check
        }

        // Also collect @instance(callable=True) functions
        let instance_callable_functions = collect_instance_callable_functions(context.ast);

        // Create a mutable checker for stateful tracking
        let mut checker = DirectInstanceCallRule::new();

        // Then check the current statement for calls
        checker.check_stmt(
            context.stmt,
            &instance_functions,
            &instance_callable_functions,
            context.file_path,
            &mut violations,
        );

        violations
    }
}
