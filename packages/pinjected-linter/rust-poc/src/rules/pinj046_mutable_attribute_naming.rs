//! PINJ046: Mutable attribute naming
//!
//! Class attributes that are assigned outside of __init__ or __post_init__
//! are considered mutable and must be prefixed with mut_ (public) or _mut (private).
//! This includes dataclass fields with default values that are mutated later.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::has_dataclass_decorator;
use rustpython_ast::{
    Expr, ExprAttribute, ExprName, Stmt, StmtAssign, StmtAugAssign, StmtClassDef,
    StmtFunctionDef, StmtAnnAssign,
};

pub struct MutableAttributeNamingRule;

impl MutableAttributeNamingRule {
    pub fn new() -> Self {
        Self
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

    /// Check if attribute name follows mutable naming convention
    fn check_mutable_naming(attr_name: &str) -> bool {
        // Private attributes should start with _mut
        if attr_name.starts_with("_") && !attr_name.starts_with("__") {
            attr_name.starts_with("_mut")
        } else if !attr_name.starts_with("_") {
            // Public attributes should start with mut_
            attr_name.starts_with("mut_")
        } else {
            // Dunder attributes are special, we skip them
            true
        }
    }

    /// Collect all attribute assignments in a class
    fn collect_class_attributes(&self, class_def: &StmtClassDef) -> Vec<(String, String, usize, bool)> {
        let mut attributes = Vec::new();
        let is_dataclass = has_dataclass_decorator(class_def);
        
        // First, collect dataclass fields with default values if it's a dataclass
        let mut dataclass_fields_with_defaults = Vec::new();
        if is_dataclass {
            for stmt in &class_def.body {
                if let Stmt::AnnAssign(ann_assign) = stmt {
                    // Check if this is a field with a default value
                    if ann_assign.value.is_some() {
                        if let Expr::Name(name) = &*ann_assign.target {
                            dataclass_fields_with_defaults.push(name.id.as_str().to_string());
                        }
                    }
                }
            }
        }
        
        for stmt in &class_def.body {
            match stmt {
                Stmt::FunctionDef(func) => {
                    let is_init = Self::is_init_method(func.name.as_str());
                    self.collect_function_attributes(func, is_init, &mut attributes);
                }
                Stmt::Assign(assign) => {
                    // Class-level assignments like self.x = 1 (though unusual)
                    self.collect_assign_attributes(assign, false, &mut attributes);
                }
                Stmt::AugAssign(aug_assign) => {
                    self.collect_aug_assign_attributes(aug_assign, false, &mut attributes);
                }
                Stmt::AnnAssign(ann_assign) => {
                    // For dataclasses, don't treat field definitions as assignments
                    if !is_dataclass {
                        self.collect_ann_assign_attributes(ann_assign, false, &mut attributes);
                    }
                }
                _ => {}
            }
        }
        
        // For dataclasses, add fields with defaults that are assigned in methods as mutable
        if is_dataclass {
            // Find which dataclass fields are assigned in methods
            let mut assigned_fields = std::collections::HashSet::new();
            for (attr_name, _, _, is_init) in &attributes {
                if !is_init && dataclass_fields_with_defaults.contains(attr_name) {
                    assigned_fields.insert(attr_name.clone());
                }
            }
            
            // Add entries for dataclass fields with defaults that are mutated
            for field_name in assigned_fields {
                // Find the field declaration to get its offset
                for stmt in &class_def.body {
                    if let Stmt::AnnAssign(ann_assign) = stmt {
                        if let Expr::Name(name) = &*ann_assign.target {
                            if name.id.as_str() == field_name {
                                attributes.push((
                                    field_name.clone(),
                                    "dataclass field with default".to_string(),
                                    ann_assign.range.start().to_usize(),
                                    false, // Not in init
                                ));
                                break;
                            }
                        }
                    }
                }
            }
        }
        
        attributes
    }

    /// Collect attributes from a function
    fn collect_function_attributes(
        &self,
        func: &StmtFunctionDef,
        is_init: bool,
        attributes: &mut Vec<(String, String, usize, bool)>,
    ) {
        for stmt in &func.body {
            self.collect_stmt_attributes(stmt, is_init, func.name.as_str(), attributes);
        }
    }

    /// Recursively collect attributes from statements
    fn collect_stmt_attributes(
        &self,
        stmt: &Stmt,
        is_init: bool,
        func_name: &str,
        attributes: &mut Vec<(String, String, usize, bool)>,
    ) {
        match stmt {
            Stmt::Assign(assign) => {
                self.collect_assign_attributes(assign, is_init, attributes);
            }
            Stmt::AugAssign(aug_assign) => {
                self.collect_aug_assign_attributes(aug_assign, is_init, attributes);
            }
            Stmt::AnnAssign(ann_assign) => {
                self.collect_ann_assign_attributes(ann_assign, is_init, attributes);
            }
            Stmt::If(if_stmt) => {
                for stmt in &if_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
                for stmt in &if_stmt.orelse {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
            }
            Stmt::While(while_stmt) => {
                for stmt in &while_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
            }
            Stmt::For(for_stmt) => {
                for stmt in &for_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
                for stmt in &for_stmt.orelse {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
            }
            Stmt::With(with_stmt) => {
                for stmt in &with_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
                for handler in &try_stmt.handlers {
                    match handler {
                        rustpython_ast::ExceptHandler::ExceptHandler(h) => {
                            for stmt in &h.body {
                                self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                            }
                        }
                    }
                }
                for stmt in &try_stmt.orelse {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
                for stmt in &try_stmt.finalbody {
                    self.collect_stmt_attributes(stmt, is_init, func_name, attributes);
                }
            }
            _ => {}
        }
    }

    /// Collect attributes from assignment
    fn collect_assign_attributes(
        &self,
        assign: &StmtAssign,
        is_init: bool,
        attributes: &mut Vec<(String, String, usize, bool)>,
    ) {
        for target in &assign.targets {
            if let Some(attr_name) = Self::extract_self_attribute(target) {
                attributes.push((
                    attr_name.to_string(),
                    "assignment".to_string(),
                    assign.range.start().to_usize(),
                    is_init,
                ));
            }
        }
    }

    /// Collect attributes from augmented assignment
    fn collect_aug_assign_attributes(
        &self,
        aug_assign: &StmtAugAssign,
        is_init: bool,
        attributes: &mut Vec<(String, String, usize, bool)>,
    ) {
        if let Some(attr_name) = Self::extract_self_attribute(&aug_assign.target) {
            attributes.push((
                attr_name.to_string(),
                "augmented assignment".to_string(),
                aug_assign.range.start().to_usize(),
                is_init,
            ));
        }
    }

    /// Collect attributes from annotated assignment
    fn collect_ann_assign_attributes(
        &self,
        ann_assign: &StmtAnnAssign,
        is_init: bool,
        attributes: &mut Vec<(String, String, usize, bool)>,
    ) {
        if let Some(attr_name) = Self::extract_self_attribute(&ann_assign.target) {
            attributes.push((
                attr_name.to_string(),
                "annotated assignment".to_string(),
                ann_assign.range.start().to_usize(),
                is_init,
            ));
        }
    }

    /// Check a class definition
    fn check_class(&self, class_def: &StmtClassDef) -> Vec<Violation> {
        let mut violations = Vec::new();
        let attributes = self.collect_class_attributes(class_def);
        let is_dataclass = has_dataclass_decorator(class_def);
        
        // For dataclasses, only flag fields that have defaults AND are mutated
        // For non-dataclasses, flag all fields mutated outside __init__/__post_init__
        let mut seen_mutable_attrs = std::collections::HashSet::new();
        let mutable_attrs: Vec<_> = attributes
            .iter()
            .filter(|(attr_name, assign_type, _, is_init)| {
                if *is_init {
                    false
                } else if is_dataclass {
                    // For dataclasses, only include if it's a dataclass field with default
                    assign_type == "dataclass field with default" && seen_mutable_attrs.insert(attr_name.clone())
                } else {
                    // For non-dataclasses, include all mutations outside init
                    seen_mutable_attrs.insert(attr_name.clone())
                }
            })
            .collect();
        
        for (attr_name, assign_type, offset, _) in mutable_attrs {
            if !Self::check_mutable_naming(attr_name) {
                let prefix = if attr_name.starts_with("_") && !attr_name.starts_with("__") {
                    "_mut"
                } else {
                    "mut_"
                };
                
                let message = format!(
                    "Class '{}' has attribute '{}' assigned outside __init__/__post_init__ ({}), making it mutable. Mutable attributes must be prefixed with '{}' to indicate their mutable nature.",
                    class_def.name.as_str(),
                    attr_name,
                    assign_type,
                    prefix
                );
                
                violations.push(Violation {
                    rule_id: self.rule_id().to_string(),
                    message,
                    offset: *offset,
                    file_path: String::new(), // Will be filled by caller
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
        
        violations
    }
}

impl LintRule for MutableAttributeNamingRule {
    fn rule_id(&self) -> &str {
        "PINJ046"
    }

    fn description(&self) -> &str {
        "Mutable attributes must be prefixed with mut_ (public) or _mut (private)"
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

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = MutableAttributeNamingRule::new();
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
    fn test_mutable_attribute_without_prefix() {
        let code = r#"
class MyClass:
    def __init__(self):
        self.value = 0
    
    def update(self):
        self.value = 1  # Mutable, should be mut_value
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ046");
        assert!(violations[0].message.contains("'value'"));
        assert!(violations[0].message.contains("mut_"));
    }

    #[test]
    fn test_private_mutable_attribute_without_prefix() {
        let code = r#"
class MyClass:
    def __init__(self):
        self._value = 0
    
    def update(self):
        self._value = 1  # Mutable, should be _mut_value
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ046");
        assert!(violations[0].message.contains("'_value'"));
        assert!(violations[0].message.contains("_mut"));
    }

    #[test]
    fn test_properly_named_mutable_attributes() {
        let code = r#"
class MyClass:
    def __init__(self):
        self.mut_counter = 0
        self._mut_state = None
    
    def update(self):
        self.mut_counter += 1
        self._mut_state = "updated"
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_immutable_attributes_in_init() {
        let code = r#"
class MyClass:
    def __init__(self):
        self.name = "test"
        self._config = {}
        self.items = []
    
    def __post_init__(self):
        self.processed = True
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_multiple_mutable_attributes() {
        let code = r#"
class MyClass:
    def __init__(self):
        self.x = 0
        self.y = 0
    
    def move(self):
        self.x += 1
        self.y += 1
    
    def reset(self):
        self.x = 0
        self.y = 0
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations.iter().any(|v| v.message.contains("'x'")));
        assert!(violations.iter().any(|v| v.message.contains("'y'")));
    }

    #[test]
    fn test_annotated_assignment() {
        let code = r#"
class MyClass:
    def __init__(self):
        self.value: int = 0
    
    def update(self):
        self.value: int = 1  # Still mutable
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("annotated assignment"));
    }

    #[test]
    fn test_nested_assignments() {
        let code = r#"
class MyClass:
    def __init__(self):
        self.flag = False
    
    def process(self):
        if True:
            self.flag = True  # Mutable
        
        for i in range(3):
            self.counter = i  # Also mutable
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
    }

    #[test]
    fn test_dunder_attributes_ignored() {
        let code = r#"
class MyClass:
    def __init__(self):
        self.__private = 0
    
    def update(self):
        self.__private = 1  # Dunder attributes are special
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_dataclass_fields_with_defaults_mutated() {
        let code = r#"
from dataclasses import dataclass
from typing import Optional

@dataclass
class TradeLifecycle:
    # State tracking fields with defaults
    trade_id: str = ""
    order_status: Optional[str] = None
    close_price: Optional[float] = None
    pnl: Optional[float] = None
    
    def execute_trade(self):
        self.trade_id = "TRADE123"  # Mutating field with default
        self.order_status = "EXECUTED"  # Mutating field with default
    
    def close_trade(self):
        self.close_price = 100.0  # Mutating field with default
        self.pnl = 50.0  # Mutating field with default
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 4);
        assert!(violations.iter().any(|v| v.message.contains("'trade_id'") && v.message.contains("dataclass field with default")));
        assert!(violations.iter().any(|v| v.message.contains("'order_status'") && v.message.contains("dataclass field with default")));
        assert!(violations.iter().any(|v| v.message.contains("'close_price'") && v.message.contains("dataclass field with default")));
        assert!(violations.iter().any(|v| v.message.contains("'pnl'") && v.message.contains("dataclass field with default")));
    }

    #[test]
    fn test_dataclass_fields_without_defaults_ignored() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class MyClass:
    name: str  # No default value
    count: int  # No default value
    
    def update(self):
        self.name = "updated"  # OK - no default value
        self.count = 10  # OK - no default value
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_dataclass_mutable_fields_properly_named() {
        let code = r#"
from dataclasses import dataclass
from typing import Optional

@dataclass
class TradeLifecycle:
    # Properly named mutable fields
    mut_trade_id: str = ""
    mut_order_status: Optional[str] = None
    _mut_internal_state: Optional[str] = None
    
    def execute_trade(self):
        self.mut_trade_id = "TRADE123"  # OK - properly named
        self.mut_order_status = "EXECUTED"  # OK - properly named
        self._mut_internal_state = "active"  # OK - properly named
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_dataclass_fields_in_init_ignored() {
        let code = r#"
from dataclasses import dataclass
from typing import Optional

@dataclass
class MyClass:
    status: Optional[str] = None
    
    def __init__(self):
        self.status = "initialized"  # OK - in __init__
    
    def __post_init__(self):
        self.status = "post_initialized"  # OK - in __post_init__
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}