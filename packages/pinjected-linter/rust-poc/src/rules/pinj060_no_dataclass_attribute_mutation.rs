//! PINJ060: No dataclass attribute mutation
//!
//! Dataclass instances should be treated as immutable. Instead of mutating
//! attributes directly, use dataclasses.replace() to create a new instance
//! with the updated values. This ensures immutability and prevents unexpected
//! side effects.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Stmt, StmtClassDef};
use std::collections::{HashMap, HashSet};

pub struct NoDataclassAttributeMutationRule;

impl NoDataclassAttributeMutationRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a class definition is a dataclass
    fn is_dataclass(class_def: &StmtClassDef) -> bool {
        for decorator in &class_def.decorator_list {
            match decorator {
                // Check for @dataclass decorator
                Expr::Name(name) if name.id.as_str() == "dataclass" => return true,
                // Check for @dataclass() with arguments
                Expr::Call(call) => {
                    if let Expr::Name(name) = &*call.func {
                        if name.id.as_str() == "dataclass" {
                            return true;
                        }
                    }
                }
                // Check for dataclasses.dataclass
                Expr::Attribute(attr) => {
                    if attr.attr.as_str() == "dataclass" {
                        if let Expr::Name(name) = &*attr.value {
                            if name.id.as_str() == "dataclasses" {
                                return true;
                            }
                        }
                    }
                }
                _ => {}
            }
        }
        false
    }

    /// Collect all dataclass names in the module
    fn collect_dataclass_names(stmts: &[Stmt]) -> HashSet<String> {
        let mut dataclass_names = HashSet::new();
        
        for stmt in stmts {
            if let Stmt::ClassDef(class_def) = stmt {
                if Self::is_dataclass(class_def) {
                    dataclass_names.insert(class_def.name.to_string());
                }
            }
        }
        
        dataclass_names
    }

    /// Check if a class name looks like it could be a dataclass
    fn looks_like_dataclass_name(name: &str) -> bool {
        // Common patterns for dataclass names
        name.ends_with("State") ||
        name.ends_with("Data") ||
        name.ends_with("Config") ||
        name.ends_with("Model") ||
        name.ends_with("Params") ||
        name.ends_with("Settings") ||
        name.ends_with("Info") ||
        name.ends_with("Record") ||
        name.ends_with("Entry") ||
        name.ends_with("Item") ||
        name.ends_with("Details") ||
        name.ends_with("Metadata") ||
        name.contains("Dataclass") ||
        name.contains("DataClass")
    }

    /// Track variables that are instances of dataclasses
    fn track_dataclass_instances(
        stmts: &[Stmt],
        dataclass_names: &HashSet<String>,
    ) -> HashMap<String, String> {
        let mut instances: HashMap<String, String> = HashMap::new();
        
        for stmt in stmts {
            match stmt {
                // Handle: instance = DataClass()
                Stmt::Assign(assign) => {
                    if let Some(target) = assign.targets.first() {
                        if let Expr::Name(target_name) = target {
                            // Check if the value is a dataclass instantiation
                            if let Expr::Call(call) = &*assign.value {
                                if let Expr::Name(class_name) = &*call.func {
                                    let class_name_str = class_name.id.as_str();
                                    // Check if it's a known dataclass OR looks like one
                                    if dataclass_names.contains(class_name_str) || 
                                       Self::looks_like_dataclass_name(class_name_str) {
                                        instances.insert(
                                            target_name.id.to_string(),
                                            class_name.id.to_string(),
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
                // Handle: instance: DataClass = DataClass()
                Stmt::AnnAssign(ann_assign) => {
                    if let Expr::Name(target_name) = &*ann_assign.target {
                        if let Some(value) = &ann_assign.value {
                            if let Expr::Call(call) = &**value {
                                if let Expr::Name(class_name) = &*call.func {
                                    let class_name_str = class_name.id.as_str();
                                    // Check if it's a known dataclass OR looks like one
                                    if dataclass_names.contains(class_name_str) || 
                                       Self::looks_like_dataclass_name(class_name_str) {
                                        instances.insert(
                                            target_name.id.to_string(),
                                            class_name.id.to_string(),
                                        );
                                    }
                                }
                            }
                        }
                        // Also check the annotation
                        if let Expr::Name(ann_name) = &*ann_assign.annotation {
                            let ann_name_str = ann_name.id.as_str();
                            // Check if it's a known dataclass OR looks like one
                            if dataclass_names.contains(ann_name_str) || 
                               Self::looks_like_dataclass_name(ann_name_str) {
                                instances.insert(
                                    target_name.id.to_string(),
                                    ann_name.id.to_string(),
                                );
                            }
                        }
                    }
                }
                // Recursively track inside function definitions
                Stmt::FunctionDef(func_def) => {
                    let func_instances = Self::track_dataclass_instances(&func_def.body, dataclass_names);
                    instances.extend(func_instances);
                }
                Stmt::AsyncFunctionDef(async_func_def) => {
                    let func_instances = Self::track_dataclass_instances(&async_func_def.body, dataclass_names);
                    instances.extend(func_instances);
                }
                Stmt::ClassDef(class_def) => {
                    let class_instances = Self::track_dataclass_instances(&class_def.body, dataclass_names);
                    instances.extend(class_instances);
                }
                // Track in nested blocks
                Stmt::If(if_stmt) => {
                    instances.extend(Self::track_dataclass_instances(&if_stmt.body, dataclass_names));
                    instances.extend(Self::track_dataclass_instances(&if_stmt.orelse, dataclass_names));
                }
                Stmt::While(while_stmt) => {
                    instances.extend(Self::track_dataclass_instances(&while_stmt.body, dataclass_names));
                    instances.extend(Self::track_dataclass_instances(&while_stmt.orelse, dataclass_names));
                }
                Stmt::For(for_stmt) => {
                    instances.extend(Self::track_dataclass_instances(&for_stmt.body, dataclass_names));
                    instances.extend(Self::track_dataclass_instances(&for_stmt.orelse, dataclass_names));
                }
                Stmt::With(with_stmt) => {
                    instances.extend(Self::track_dataclass_instances(&with_stmt.body, dataclass_names));
                }
                Stmt::Try(try_stmt) => {
                    instances.extend(Self::track_dataclass_instances(&try_stmt.body, dataclass_names));
                    for handler in &try_stmt.handlers {
                        if let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler {
                            instances.extend(Self::track_dataclass_instances(&h.body, dataclass_names));
                        }
                    }
                    instances.extend(Self::track_dataclass_instances(&try_stmt.orelse, dataclass_names));
                    instances.extend(Self::track_dataclass_instances(&try_stmt.finalbody, dataclass_names));
                }
                _ => {}
            }
        }
        
        instances
    }

    /// Check for attribute mutations on dataclass instances
    fn check_for_mutations(
        stmts: &[Stmt],
        dataclass_instances: &HashMap<String, String>,
    ) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        for stmt in stmts {
            match stmt {
                // Check for: instance.attr = value
                Stmt::Assign(assign) => {
                    for target in &assign.targets {
                        if let Expr::Attribute(attr) = target {
                            if let Expr::Name(name) = &*attr.value {
                                if let Some(class_name) = dataclass_instances.get(name.id.as_str()) {
                                    let message = format!(
                                        "Mutating attribute '{}' of dataclass instance '{}' (type: {}). \
                                        Dataclasses should be immutable. Use 'dataclasses.replace({}, {}=new_value)' \
                                        to create a new instance with updated values.",
                                        attr.attr.as_str(),
                                        name.id.as_str(),
                                        class_name,
                                        name.id.as_str(),
                                        attr.attr.as_str()
                                    );
                                    
                                    violations.push(Violation {
                                        rule_id: "PINJ060".to_string(),
                                        message,
                                        offset: assign.range.start().to_usize(),
                                        file_path: String::new(),
                                        severity: Severity::Error,
                                        fix: None,
                                    });
                                }
                            }
                        }
                    }
                }
                // Check for: instance.attr += value, instance.attr -= value, etc.
                Stmt::AugAssign(aug_assign) => {
                    if let Expr::Attribute(attr) = &*aug_assign.target {
                        if let Expr::Name(name) = &*attr.value {
                            if let Some(class_name) = dataclass_instances.get(name.id.as_str()) {
                                let message = format!(
                                    "Mutating attribute '{}' of dataclass instance '{}' (type: {}) using augmented assignment. \
                                    Dataclasses should be immutable. Use 'dataclasses.replace({}, {}=<computed_value>)' \
                                    to create a new instance with updated values.",
                                    attr.attr.as_str(),
                                    name.id.as_str(),
                                    class_name,
                                    name.id.as_str(),
                                    attr.attr.as_str()
                                );
                                
                                violations.push(Violation {
                                    rule_id: "PINJ060".to_string(),
                                    message,
                                    offset: aug_assign.range.start().to_usize(),
                                    file_path: String::new(),
                                    severity: Severity::Error,
                                    fix: None,
                                });
                            }
                        }
                    }
                }
                // Check for del instance.attr
                Stmt::Delete(delete_stmt) => {
                    for target in &delete_stmt.targets {
                        if let Expr::Attribute(attr) = target {
                            if let Expr::Name(name) = &*attr.value {
                                if let Some(class_name) = dataclass_instances.get(name.id.as_str()) {
                                    let message = format!(
                                        "Deleting attribute '{}' of dataclass instance '{}' (type: {}). \
                                        Dataclasses should be immutable. Consider creating a new instance \
                                        without the attribute or using a different data structure.",
                                        attr.attr.as_str(),
                                        name.id.as_str(),
                                        class_name
                                    );
                                    
                                    violations.push(Violation {
                                        rule_id: "PINJ060".to_string(),
                                        message,
                                        offset: delete_stmt.range.start().to_usize(),
                                        file_path: String::new(),
                                        severity: Severity::Error,
                                        fix: None,
                                    });
                                }
                            }
                        }
                    }
                }
                // Recursively check nested blocks
                Stmt::If(if_stmt) => {
                    violations.extend(Self::check_for_mutations(&if_stmt.body, dataclass_instances));
                    violations.extend(Self::check_for_mutations(&if_stmt.orelse, dataclass_instances));
                }
                Stmt::While(while_stmt) => {
                    violations.extend(Self::check_for_mutations(&while_stmt.body, dataclass_instances));
                    violations.extend(Self::check_for_mutations(&while_stmt.orelse, dataclass_instances));
                }
                Stmt::For(for_stmt) => {
                    violations.extend(Self::check_for_mutations(&for_stmt.body, dataclass_instances));
                    violations.extend(Self::check_for_mutations(&for_stmt.orelse, dataclass_instances));
                }
                Stmt::With(with_stmt) => {
                    violations.extend(Self::check_for_mutations(&with_stmt.body, dataclass_instances));
                }
                Stmt::Try(try_stmt) => {
                    violations.extend(Self::check_for_mutations(&try_stmt.body, dataclass_instances));
                    for handler in &try_stmt.handlers {
                        if let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler {
                            violations.extend(Self::check_for_mutations(&h.body, dataclass_instances));
                        }
                    }
                    violations.extend(Self::check_for_mutations(&try_stmt.orelse, dataclass_instances));
                    violations.extend(Self::check_for_mutations(&try_stmt.finalbody, dataclass_instances));
                }
                Stmt::FunctionDef(func_def) => {
                    // Check inside function definitions as well
                    violations.extend(Self::check_for_mutations(&func_def.body, dataclass_instances));
                }
                Stmt::AsyncFunctionDef(async_func_def) => {
                    violations.extend(Self::check_for_mutations(&async_func_def.body, dataclass_instances));
                }
                Stmt::ClassDef(class_def) => {
                    // Check inside class definitions
                    violations.extend(Self::check_for_mutations(&class_def.body, dataclass_instances));
                }
                _ => {}
            }
        }
        
        violations
    }
}

impl LintRule for NoDataclassAttributeMutationRule {
    fn rule_id(&self) -> &str {
        "PINJ060"
    }

    fn description(&self) -> &str {
        "Dataclass instances should be immutable. Use dataclasses.replace() instead of direct attribute mutation."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        // We need to check the entire module to track dataclass definitions and instances
        match context.ast {
            rustpython_ast::Mod::Module(module) => {
                // First, collect all dataclass names
                let dataclass_names = Self::collect_dataclass_names(&module.body);
                
                // Then, track dataclass instances
                let dataclass_instances = Self::track_dataclass_instances(&module.body, &dataclass_names);
                
                // Finally, check for mutations
                Self::check_for_mutations(&module.body, &dataclass_instances)
            }
            _ => vec![],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = NoDataclassAttributeMutationRule::new();
        let mut violations = Vec::new();

        match &ast {
            rustpython_ast::Mod::Module(module) => {
                // Use the first statement if available, otherwise we can't test
                if let Some(stmt) = module.body.first() {
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
    fn test_direct_attribute_assignment() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int

person = Person("Alice", 30)
person.name = "Bob"  # This should be flagged
person.age = 31  # This should be flagged
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("Mutating attribute 'name'"));
        assert!(violations[0].message.contains("dataclasses.replace"));
        assert!(violations[1].message.contains("Mutating attribute 'age'"));
    }

    #[test]
    fn test_augmented_assignment() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class Counter:
    count: int

counter = Counter(0)
counter.count += 1  # This should be flagged
counter.count -= 1  # This should be flagged
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("using augmented assignment"));
        assert!(violations[1].message.contains("using augmented assignment"));
    }

    #[test]
    fn test_dataclass_decorator_variations() {
        let code = r#"
from dataclasses import dataclass
import dataclasses

@dataclass
class A:
    x: int

@dataclass()
class B:
    y: int

@dataclasses.dataclass
class C:
    z: int

a = A(1)
b = B(2)
c = C(3)

a.x = 10  # Should be flagged
b.y = 20  # Should be flagged
c.z = 30  # Should be flagged
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
    }

    #[test]
    fn test_no_violation_with_replace() {
        let code = r#"
from dataclasses import dataclass, replace

@dataclass
class Person:
    name: str
    age: int

person = Person("Alice", 30)
new_person = replace(person, name="Bob", age=31)  # This is the correct way
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_blocks() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class Config:
    value: int

config = Config(10)

if True:
    config.value = 20  # Should be flagged

for i in range(3):
    config.value += i  # Should be flagged

while config.value < 100:
    config.value *= 2  # Should be flagged
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
    }

    #[test]
    fn test_regular_class_not_flagged() {
        let code = r#"
class RegularClass:
    def __init__(self):
        self.value = 0

obj = RegularClass()
obj.value = 10  # Should NOT be flagged (not a dataclass)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_delete_attribute() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class Data:
    x: int
    y: int

data = Data(1, 2)
del data.x  # Should be flagged
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("Deleting attribute"));
    }

    #[test]
    fn test_multiple_instances() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

p1 = Point(0, 0)
p2 = Point(10, 10)

p1.x = 5  # Should be flagged
p2.y = 15  # Should be flagged
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
    }

    #[test]
    fn test_annotated_assignment() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class Value:
    data: int

val: Value = Value(42)
val.data = 100  # Should be flagged
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn test_mutation_in_function() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class State:
    value: int

def update_state():
    state = State(0)
    state.value = 10  # Should be flagged
    return state
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn test_imported_dataclass_by_naming_heuristic() {
        let code = r#"
from some_module import ServiceState, ConfigData

def process():
    state = ServiceState(instance_id="test", count=0)
    config = ConfigData(key="value")
    
    # These should be flagged based on naming heuristic
    state.count += 1
    config.key = "new_value"
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2, "Should detect mutations on classes that look like dataclasses");
        assert!(violations[0].message.contains("ServiceState"));
        assert!(violations[1].message.contains("ConfigData"));
    }
    
    #[test]
    fn test_imported_class_not_looking_like_dataclass() {
        let code = r#"
from some_module import HttpClient, DatabaseConnection

def process():
    client = HttpClient()
    db = DatabaseConnection()
    
    # These should NOT be flagged as they don't look like dataclasses
    client.timeout = 30
    db.retries = 3
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0, "Should not flag mutations on regular-looking classes");
    }
}