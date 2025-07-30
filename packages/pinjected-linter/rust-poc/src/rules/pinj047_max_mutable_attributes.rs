//! PINJ047: Maximum mutable attributes per class
//!
//! Limits the number of mutable attributes (those assigned outside __init__/__post_init__)
//! in a class to N (default 1, configurable).

use crate::config::RuleConfig;
use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{
    Expr, ExprAttribute, ExprName, Stmt, StmtAssign, StmtAugAssign, StmtClassDef,
    StmtFunctionDef, StmtAnnAssign,
};
use std::collections::HashSet;

pub struct MaxMutableAttributesRule {
    max_mutable_attributes: usize,
}

impl MaxMutableAttributesRule {
    pub fn new() -> Self {
        Self {
            max_mutable_attributes: 1, // Default limit
        }
    }

    pub fn with_max(max_mutable_attributes: usize) -> Self {
        Self {
            max_mutable_attributes,
        }
    }

    pub fn with_config(config: Option<&RuleConfig>) -> Self {
        match config {
            Some(cfg) => Self {
                max_mutable_attributes: cfg.max_mutable_attributes.unwrap_or(1),
            },
            None => Self::new(),
        }
    }

    /// Check if a function is __init__ or __post_init__
    fn is_init_method(func_name: &str) -> bool {
        func_name == "__init__" || func_name == "__post_init__"
    }

    /// Check if an expression is self.attribute
    fn extract_self_attribute(expr: &Expr) -> Option<&str> {
        match expr {
            Expr::Attribute(ExprAttribute { value, attr, .. }) => {
                if let Expr::Name(ExprName { id, .. }) = &**value {
                    if id.as_str() == "self" {
                        return Some(attr.as_str());
                    }
                }
            }
            _ => {}
        }
        None
    }

    /// Collect all unique mutable attributes in a class
    fn collect_mutable_attributes(&self, class_def: &StmtClassDef) -> HashSet<String> {
        let mut all_attributes = HashSet::new();
        let mut init_only_attributes = HashSet::new();
        let mut non_init_attributes = HashSet::new();
        
        for stmt in &class_def.body {
            match stmt {
                Stmt::FunctionDef(func) => {
                    let is_init = Self::is_init_method(func.name.as_str());
                    let mut func_attributes = Vec::new();
                    self.collect_function_attributes(func, is_init, &mut func_attributes, &mut init_only_attributes);
                    
                    for attr in func_attributes {
                        all_attributes.insert(attr.clone());
                        if !is_init {
                            non_init_attributes.insert(attr);
                        }
                    }
                }
                Stmt::Assign(assign) => {
                    let mut attrs = Vec::new();
                    self.collect_assign_attributes(assign, false, &mut attrs, &mut init_only_attributes);
                    for attr in attrs {
                        all_attributes.insert(attr.clone());
                        non_init_attributes.insert(attr);
                    }
                }
                Stmt::AugAssign(aug_assign) => {
                    let mut attrs = Vec::new();
                    self.collect_aug_assign_attributes(aug_assign, false, &mut attrs, &mut init_only_attributes);
                    for attr in attrs {
                        all_attributes.insert(attr.clone());
                        non_init_attributes.insert(attr);
                    }
                }
                Stmt::AnnAssign(ann_assign) => {
                    let mut attrs = Vec::new();
                    self.collect_ann_assign_attributes(ann_assign, false, &mut attrs, &mut init_only_attributes);
                    for attr in attrs {
                        all_attributes.insert(attr.clone());
                        non_init_attributes.insert(attr);
                    }
                }
                _ => {}
            }
        }
        
        // Mutable attributes are those assigned outside of init methods
        non_init_attributes
    }

    /// Collect attributes from a function
    fn collect_function_attributes(
        &self,
        func: &StmtFunctionDef,
        is_init: bool,
        all_attributes: &mut Vec<String>,
        _init_attributes: &mut HashSet<String>,
    ) {
        for stmt in &func.body {
            self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
        }
    }

    /// Recursively collect attributes from statements
    fn collect_stmt_attributes(
        &self,
        stmt: &Stmt,
        is_init: bool,
        all_attributes: &mut Vec<String>,
        _init_attributes: &mut HashSet<String>,
    ) {
        match stmt {
            Stmt::Assign(assign) => {
                self.collect_assign_attributes(assign, is_init, all_attributes, _init_attributes);
            }
            Stmt::AugAssign(aug_assign) => {
                self.collect_aug_assign_attributes(aug_assign, is_init, all_attributes, _init_attributes);
            }
            Stmt::AnnAssign(ann_assign) => {
                self.collect_ann_assign_attributes(ann_assign, is_init, all_attributes, _init_attributes);
            }
            Stmt::If(if_stmt) => {
                for stmt in &if_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
                for stmt in &if_stmt.orelse {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
            }
            Stmt::While(while_stmt) => {
                for stmt in &while_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
            }
            Stmt::For(for_stmt) => {
                for stmt in &for_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
                for stmt in &for_stmt.orelse {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
            }
            Stmt::With(with_stmt) => {
                for stmt in &with_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
                for handler in &try_stmt.handlers {
                    match handler {
                        rustpython_ast::ExceptHandler::ExceptHandler(h) => {
                            for stmt in &h.body {
                                self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                            }
                        }
                    }
                }
                for stmt in &try_stmt.orelse {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
                for stmt in &try_stmt.finalbody {
                    self.collect_stmt_attributes(stmt, is_init, all_attributes, _init_attributes);
                }
            }
            _ => {}
        }
    }

    /// Collect attributes from assignment
    fn collect_assign_attributes(
        &self,
        assign: &StmtAssign,
        _is_init: bool,
        all_attributes: &mut Vec<String>,
        _init_attributes: &mut HashSet<String>,
    ) {
        for target in &assign.targets {
            if let Some(attr_name) = Self::extract_self_attribute(target) {
                all_attributes.push(attr_name.to_string());
            }
        }
    }

    /// Collect attributes from augmented assignment
    fn collect_aug_assign_attributes(
        &self,
        aug_assign: &StmtAugAssign,
        _is_init: bool,
        all_attributes: &mut Vec<String>,
        _init_attributes: &mut HashSet<String>,
    ) {
        if let Some(attr_name) = Self::extract_self_attribute(&aug_assign.target) {
            all_attributes.push(attr_name.to_string());
        }
    }

    /// Collect attributes from annotated assignment
    fn collect_ann_assign_attributes(
        &self,
        ann_assign: &StmtAnnAssign,
        _is_init: bool,
        all_attributes: &mut Vec<String>,
        _init_attributes: &mut HashSet<String>,
    ) {
        if let Some(attr_name) = Self::extract_self_attribute(&ann_assign.target) {
            all_attributes.push(attr_name.to_string());
        }
    }

    /// Check a class definition
    fn check_class(&self, class_def: &StmtClassDef) -> Vec<Violation> {
        let mut violations = Vec::new();
        let mutable_attrs = self.collect_mutable_attributes(class_def);
        
        if mutable_attrs.len() > self.max_mutable_attributes {
            let mut attr_list: Vec<_> = mutable_attrs.into_iter().collect();
            attr_list.sort(); // For consistent output
            
            let message = if self.max_mutable_attributes == 0 {
                format!(
                    "Class '{}' has {} mutable attributes ({}), but mutable attributes are not allowed. \
                    Classes should be immutable; use functional patterns or the strategy pattern instead.",
                    class_def.name.as_str(),
                    attr_list.len(),
                    attr_list.join(", ")
                )
            } else if self.max_mutable_attributes == 1 {
                format!(
                    "Class '{}' has {} mutable attributes ({}), exceeding the limit of 1. \
                    Consider refactoring to reduce mutable state or use composition.",
                    class_def.name.as_str(),
                    attr_list.len(),
                    attr_list.join(", ")
                )
            } else {
                format!(
                    "Class '{}' has {} mutable attributes ({}), exceeding the limit of {}. \
                    Consider refactoring to reduce mutable state.",
                    class_def.name.as_str(),
                    attr_list.len(),
                    attr_list.join(", "),
                    self.max_mutable_attributes
                )
            };
            
            violations.push(Violation {
                rule_id: self.rule_id().to_string(),
                message,
                offset: class_def.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Error,
                fix: None,
            });
        }
        
        violations
    }
}

impl LintRule for MaxMutableAttributesRule {
    fn rule_id(&self) -> &str {
        "PINJ047"
    }

    fn description(&self) -> &str {
        "Limit the number of mutable attributes per class"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::ClassDef(class_def) => {
                for mut violation in self.check_class(class_def) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
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

    fn check_code_with_limit(code: &str, limit: usize) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = MaxMutableAttributesRule::with_max(limit);
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

    fn check_code(code: &str) -> Vec<Violation> {
        check_code_with_limit(code, 1) // Default limit
    }

    #[test]
    fn test_single_mutable_attribute_allowed() {
        let code = r#"
class Counter:
    def __init__(self):
        self.mut_count = 0
    
    def increment(self):
        self.mut_count += 1
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_multiple_mutable_attributes_violation() {
        let code = r#"
class GameState:
    def __init__(self):
        self.mut_score = 0
        self.mut_level = 1
        self.mut_lives = 3
    
    def update_score(self, points):
        self.mut_score += points
    
    def next_level(self):
        self.mut_level += 1
    
    def lose_life(self):
        self.mut_lives -= 1
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ047");
        assert!(violations[0].message.contains("3 mutable attributes"));
        assert!(violations[0].message.contains("exceeding the limit of 1"));
    }

    #[test]
    fn test_zero_mutable_attributes_allowed() {
        let code = r#"
class ImmutableClass:
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        return self.value
"#;
        let violations = check_code_with_limit(code, 0);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_zero_limit_violation() {
        let code = r#"
class MutableClass:
    def __init__(self):
        self.mut_state = "initial"
    
    def change_state(self):
        self.mut_state = "changed"
"#;
        let violations = check_code_with_limit(code, 0);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutable attributes are not allowed"));
    }

    #[test]
    fn test_custom_limit() {
        let code = r#"
class DataContainer:
    def __init__(self):
        self.mut_a = 0
        self.mut_b = 0
        self.mut_c = 0
    
    def update_all(self):
        self.mut_a += 1
        self.mut_b += 1
        self.mut_c += 1
"#;
        // With limit of 3, should pass
        let violations = check_code_with_limit(code, 3);
        assert_eq!(violations.len(), 0);
        
        // With limit of 2, should fail
        let violations = check_code_with_limit(code, 2);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("exceeding the limit of 2"));
    }

    #[test]
    fn test_init_only_attributes_not_counted() {
        let code = r#"
class Config:
    def __init__(self, data):
        self.host = data['host']
        self.port = data['port']
        self.timeout = data['timeout']
        self.mut_connection_count = 0
    
    def increment_connections(self):
        self.mut_connection_count += 1
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0); // Only 1 mutable attribute
    }

    #[test]
    fn test_attributes_assigned_in_different_methods() {
        let code = r#"
class BadClass:
    def __init__(self):
        self.x = 0
    
    def method1(self):
        self.y = 1  # First mutable
    
    def method2(self):
        self.z = 2  # Second mutable
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("2 mutable attributes"));
        assert!(violations[0].message.contains("y, z"));
    }

    #[test]
    fn test_repeated_assignments_counted_once() {
        let code = r#"
class Counter:
    def __init__(self):
        self.mut_value = 0
    
    def increment(self):
        self.mut_value += 1
    
    def decrement(self):
        self.mut_value -= 1
    
    def reset(self):
        self.mut_value = 0
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0); // Only 1 unique mutable attribute
    }

    #[test]
    fn test_post_init_excluded() {
        let code = r#"
class DataClass:
    def __init__(self):
        self.a = 1
    
    def __post_init__(self):
        self.b = 2
        self.c = 3
    
    def update(self):
        self.mut_d = 4  # Only mutable attribute
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}