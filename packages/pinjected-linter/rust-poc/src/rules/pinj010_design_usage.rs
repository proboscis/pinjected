//! PINJ010: design() usage patterns
//!
//! The design() function is used to configure and override
//! dependencies in Pinjected. Common issues include:
//! 1. Calling @instance functions instead of referencing them
//! 2. Using decorator names as keys instead of dependency names
//! 3. Incorrect combination patterns

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_instance_decorator, has_instance_decorator_async};
use rustpython_ast::{Expr, ExprCall, Mod, Stmt};
use std::collections::HashSet;

pub struct DesignUsageRule {
    /// Track @instance decorated function names
    instance_functions: HashSet<String>,
    /// Track if design is imported and its alias
    has_design_import: bool,
    design_alias: Option<String>,
}

impl DesignUsageRule {
    pub fn new() -> Self {
        Self {
            instance_functions: HashSet::new(),
            has_design_import: false,
            design_alias: None,
        }
    }

    /// Collect all @instance functions and design imports in the module
    fn collect_definitions(&mut self, ast: &Mod) {
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
                if has_instance_decorator(func) {
                    self.instance_functions.insert(func.name.to_string());
                }
                // Check nested functions
                for stmt in &func.body {
                    self.collect_from_stmt(stmt);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_instance_decorator_async(func) {
                    self.instance_functions.insert(func.name.to_string());
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
            Stmt::ImportFrom(import) => {
                // Track design imports
                if let Some(module) = &import.module {
                    if module.as_str() == "pinjected" {
                        for alias in &import.names {
                            if alias.name.as_str() == "design" {
                                self.has_design_import = true;
                                self.design_alias = alias.asname.as_ref().map(|s| s.to_string());
                            }
                        }
                    }
                }
            }
            _ => {}
        }
    }

    /// Check if a call is to design()
    fn is_design_call(&self, call: &ExprCall) -> bool {
        if let Expr::Name(name) = &*call.func {
            let design_name = self.design_alias.as_deref().unwrap_or("design");
            name.id.as_str() == design_name
        } else {
            false
        }
    }

    /// Check design() usage patterns
    fn check_design_call(&self, call: &ExprCall, file_path: &str, violations: &mut Vec<Violation>) {
        // Check keyword arguments
        for keyword in &call.keywords {
            if let Some(arg_name) = &keyword.arg {
                // Rule 1: Check for decorator names as keys
                if ["injected", "instance", "provider"].contains(&arg_name.as_str()) {
                    violations.push(Violation {
                        rule_id: "PINJ010".to_string(),
                        message: format!(
                            "design() parameter '{}' looks like a decorator name. design() should map dependency names to their providers or values.",
                            arg_name
                        ),
                        offset: keyword.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Warning,
                        fix: None,
                    });
                }

                // Rule 2: Check for direct instance calls as values
                if let Expr::Call(value_call) = &keyword.value {
                    if let Expr::Name(func_name) = &*value_call.func {
                        // Only flag if this is actually an @instance decorated function
                        if self.instance_functions.contains(&func_name.id.to_string()) {
                            violations.push(Violation {
                                rule_id: "PINJ010".to_string(),
                                message: format!(
                                    "Calling @instance function '{}()' in design(). @instance functions should be referenced, not called. Use '{}': {} instead of '{}': {}().",
                                    func_name.id, arg_name, func_name.id, arg_name, func_name.id
                                ),
                                offset: value_call.range.start().to_usize(),
                                file_path: file_path.to_string(),
                                severity: Severity::Warning,
                                fix: None,
                            });
                        }
                    }
                }
            }
        }
    }

    /// Check expressions for design() calls
    fn check_expr(&self, expr: &Expr, file_path: &str, violations: &mut Vec<Violation>) {
        match expr {
            Expr::Call(call) => {
                if self.is_design_call(call) {
                    self.check_design_call(call, file_path, violations);
                }
                // Check arguments recursively
                for arg in &call.args {
                    self.check_expr(arg, file_path, violations);
                }
                // Check keyword values
                for keyword in &call.keywords {
                    self.check_expr(&keyword.value, file_path, violations);
                }
            }
            // Recurse into other expression types that might contain calls
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

    /// Check statements for design() calls
    fn check_stmt(&self, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
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
            _ => {}
        }
    }
}

impl LintRule for DesignUsageRule {
    fn rule_id(&self) -> &str {
        "PINJ010"
    }

    fn description(&self) -> &str {
        "design() should be used correctly for dependency configuration"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Create a mutable instance for stateful tracking
        let mut checker = DesignUsageRule::new();

        // First pass: collect all @instance functions and design imports
        checker.collect_definitions(context.ast);

        // Second pass: check the current statement
        checker.check_stmt(context.stmt, context.file_path, &mut violations);

        violations
    }
}
