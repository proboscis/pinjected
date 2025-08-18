//! PINJ056: No mutable argument mutations
//!
//! Functions should not mutate dict, list, or set arguments. Instead, they should
//! return new collections. This prevents unexpected side effects and makes the code
//! more predictable and easier to test.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Arguments, Expr, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
use std::collections::HashSet;

pub struct NoMutableArgumentMutationsRule;

impl NoMutableArgumentMutationsRule {
    pub fn new() -> Self {
        Self
    }

    /// Get all parameter names from function arguments
    fn get_parameter_names(args: &Arguments) -> HashSet<String> {
        let mut names = HashSet::new();
        
        // Add positional-only args
        for arg in &args.posonlyargs {
            names.insert(arg.def.arg.to_string());
        }
        
        // Add regular args
        for arg in &args.args {
            names.insert(arg.def.arg.to_string());
        }
        
        // Add keyword-only args
        for arg in &args.kwonlyargs {
            names.insert(arg.def.arg.to_string());
        }
        
        // Add *args if present
        if let Some(arg) = &args.vararg {
            names.insert(arg.arg.to_string());
        }
        
        // Add **kwargs if present
        if let Some(arg) = &args.kwarg {
            names.insert(arg.arg.to_string());
        }
        
        names
    }

    /// Check if an expression is a method call that mutates a collection
    fn is_mutation_method(method_name: &str) -> bool {
        matches!(
            method_name,
            // List mutations
            "append" | "extend" | "insert" | "remove" | "pop" | "clear" | 
            "sort" | "reverse" |
            // Dict mutations
            "update" | "popitem" | "setdefault" |
            // Set mutations
            "add" | "discard" | "intersection_update" | 
            "difference_update" | "symmetric_difference_update"
        )
    }

    /// Check if an expression references a parameter (recursively for nested subscripts)
    fn references_parameter(expr: &Expr, param_names: &HashSet<String>) -> Option<String> {
        match expr {
            Expr::Name(name) => {
                if param_names.contains(name.id.as_str()) {
                    Some(name.id.to_string())
                } else {
                    None
                }
            }
            Expr::Subscript(subscript) => {
                // Recursively check if the subscript's value references a parameter
                Self::references_parameter(&subscript.value, param_names)
            }
            _ => None,
        }
    }

    /// Check if a statement contains a mutation of a parameter
    fn check_statement_for_mutations(
        stmt: &Stmt,
        param_names: &HashSet<String>,
        func_name: &str,
    ) -> Vec<Violation> {
        let mut violations = Vec::new();

        match stmt {
            // Check for method calls like param.append(x)
            Stmt::Expr(expr_stmt) => {
                if let Expr::Call(call) = &*expr_stmt.value {
                    if let Expr::Attribute(attr) = &*call.func {
                        if let Expr::Name(name) = &*attr.value {
                            if param_names.contains(name.id.as_str()) {
                                if Self::is_mutation_method(attr.attr.as_str()) {
                                    let message = format!(
                                        "Function '{}' mutates its argument '{}' by calling '{}()'. \
                                        Mutating function arguments is forbidden. Instead, create and return \
                                        a new collection. For example, instead of 'items.append(x)', use \
                                        'return items + [x]' or 'return [*items, x]'.",
                                        func_name,
                                        name.id.as_str(),
                                        attr.attr.as_str()
                                    );

                                    violations.push(Violation {
                                        rule_id: "PINJ056".to_string(),
                                        message,
                                        offset: expr_stmt.range.start().to_usize(),
                                        file_path: String::new(),
                                        severity: Severity::Error,
                                        fix: None,
                                    });
                                }
                            }
                        }
                    }
                }
            }
            // Check for assignments like param[key] = value or param['key'] = value
            Stmt::Assign(assign_stmt) => {
                for target in &assign_stmt.targets {
                    if let Expr::Subscript(subscript) = target {
                        if let Some(param_name) = Self::references_parameter(&subscript.value, param_names) {
                                let message = format!(
                                    "Function '{}' mutates its argument '{}' by assigning to an index/key. \
                                    Mutating function arguments is forbidden. Instead, create and return \
                                    a new collection. For example, instead of 'data[key] = value', use \
                                    'return {{**data, key: value}}' or create a copy first.",
                                    func_name,
                                    param_name
                                );

                                violations.push(Violation {
                                    rule_id: "PINJ056".to_string(),
                                    message,
                                    offset: assign_stmt.range.start().to_usize(),
                                    file_path: String::new(),
                                    severity: Severity::Error,
                                    fix: None,
                                });
                        }
                    }
                }
            }
            // Check for augmented assignments like param[key] += value
            Stmt::AugAssign(aug_assign_stmt) => {
                if let Expr::Subscript(subscript) = &*aug_assign_stmt.target {
                    if let Some(param_name) = Self::references_parameter(&subscript.value, param_names) {
                            let message = format!(
                                "Function '{}' mutates its argument '{}' through augmented assignment. \
                                Mutating function arguments is forbidden. Instead, create and return \
                                a new collection.",
                                func_name,
                                param_name
                            );

                            violations.push(Violation {
                                rule_id: "PINJ056".to_string(),
                                message,
                                offset: aug_assign_stmt.range.start().to_usize(),
                                file_path: String::new(),
                                severity: Severity::Error,
                                fix: None,
                            });
                    }
                }
            }
            // Check for del param[key]
            Stmt::Delete(delete_stmt) => {
                for target in &delete_stmt.targets {
                    if let Expr::Subscript(subscript) = target {
                        if let Some(param_name) = Self::references_parameter(&subscript.value, param_names) {
                                let message = format!(
                                    "Function '{}' mutates its argument '{}' by deleting an element. \
                                    Mutating function arguments is forbidden. Instead, create and return \
                                    a new collection without the element.",
                                    func_name,
                                    param_name
                                );

                                violations.push(Violation {
                                    rule_id: "PINJ056".to_string(),
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
            // Recursively check nested statements
            Stmt::If(if_stmt) => {
                for stmt in &if_stmt.body {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
                for stmt in &if_stmt.orelse {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
            }
            Stmt::While(while_stmt) => {
                for stmt in &while_stmt.body {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
                for stmt in &while_stmt.orelse {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
            }
            Stmt::For(for_stmt) => {
                for stmt in &for_stmt.body {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
                for stmt in &for_stmt.orelse {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
            }
            Stmt::With(with_stmt) => {
                for stmt in &with_stmt.body {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
                for handler in &try_stmt.handlers {
                    if let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler {
                        for stmt in &h.body {
                            violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                        }
                    }
                }
                for stmt in &try_stmt.orelse {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
                for stmt in &try_stmt.finalbody {
                    violations.extend(Self::check_statement_for_mutations(stmt, param_names, func_name));
                }
            }
            _ => {}
        }

        violations
    }

    /// Check a function definition for mutations of its parameters
    fn check_function(&self, func: &StmtFunctionDef) -> Vec<Violation> {
        let param_names = Self::get_parameter_names(&func.args);
        let mut violations = Vec::new();

        for stmt in &func.body {
            violations.extend(Self::check_statement_for_mutations(
                stmt,
                &param_names,
                func.name.as_str(),
            ));
        }

        violations
    }

    /// Check an async function definition for mutations of its parameters
    fn check_async_function(&self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        let param_names = Self::get_parameter_names(&func.args);
        let mut violations = Vec::new();

        for stmt in &func.body {
            violations.extend(Self::check_statement_for_mutations(
                stmt,
                &param_names,
                func.name.as_str(),
            ));
        }

        violations
    }
}

impl LintRule for NoMutableArgumentMutationsRule {
    fn rule_id(&self) -> &str {
        "PINJ056"
    }

    fn description(&self) -> &str {
        "Functions should not mutate dict/list/set arguments. Return new collections instead."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        match context.stmt {
            Stmt::FunctionDef(func) => self.check_function(func),
            Stmt::AsyncFunctionDef(func) => self.check_async_function(func),
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
        let rule = NoMutableArgumentMutationsRule::new();
        let mut violations = Vec::new();

        match &ast {
            rustpython_ast::Mod::Module(module) => {
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
    fn test_list_append_mutation() {
        let code = r#"
def process_items(items):
    items.append("new_item")
    return items
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'items' by calling 'append()'"));
    }

    #[test]
    fn test_dict_update_mutation() {
        let code = r#"
def update_config(config):
    config.update({"key": "value"})
    return config
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'config' by calling 'update()'"));
    }

    #[test]
    fn test_set_add_mutation() {
        let code = r#"
def add_to_set(my_set):
    my_set.add("element")
    return my_set
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'my_set' by calling 'add()'"));
    }

    #[test]
    fn test_subscript_assignment() {
        let code = r#"
def update_dict(data):
    data["key"] = "value"
    return data
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'data' by assigning to an index/key"));
    }

    #[test]
    fn test_del_statement() {
        let code = r#"
def remove_key(data):
    del data["key"]
    return data
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'data' by deleting an element"));
    }

    #[test]
    fn test_no_mutation_new_list() {
        let code = r#"
def process_items(items):
    new_items = items + ["new_item"]
    return new_items
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_mutation_dict_copy() {
        let code = r#"
def update_config(config):
    new_config = {**config, "key": "value"}
    return new_config
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_mutation_in_if() {
        let code = r#"
def conditional_append(items, condition):
    if condition:
        items.append("new_item")
    return items
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'items' by calling 'append()'"));
    }

    #[test]
    fn test_multiple_mutations() {
        let code = r#"
def process_data(items, config):
    items.append("item1")
    items.extend(["item2", "item3"])
    config["key"] = "value"
    return items, config
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
    }

    #[test]
    fn test_async_function_mutation() {
        let code = r#"
async def async_process(data):
    data.pop("key")
    return data
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'data' by calling 'pop()'"));
    }

    #[test]
    fn test_list_index_assignment() {
        let code = r#"
def modify_list(items):
    items[0] = "first"
    items[-1] = "last"
    items[1:3] = ["a", "b"]
    return items
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
        for v in &violations {
            assert!(v.message.contains("mutates its argument 'items' by assigning to an index/key"));
        }
    }

    #[test]
    fn test_augmented_assignment() {
        let code = r#"
def increment_values(items, data):
    items[0] += 1
    data["count"] += 1
    return items, data
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations[0].message.contains("mutates its argument 'items' through augmented assignment"));
        assert!(violations[1].message.contains("mutates its argument 'data' through augmented assignment"));
    }

    #[test]
    fn test_nested_list_access_mutation() {
        let code = r#"
def modify_nested(matrix):
    matrix[0][0] = 99
    return matrix
"#;
        let violations = check_code(code);
        // This catches the outer subscript access on matrix
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'matrix'"));
    }

    #[test]
    fn test_mutation_in_loop() {
        let code = r#"
def uppercase_all(items):
    for i in range(len(items)):
        items[i] = items[i].upper()
    return items
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("mutates its argument 'items' by assigning to an index/key"));
    }

    #[test]
    fn test_no_mutation_on_local_copy() {
        let code = r#"
def process_safely(items, data):
    local_items = items.copy()
    local_items.append("safe")
    local_items[0] = "modified"
    
    local_data = data.copy()
    local_data["key"] = "value"
    local_data.update({"new": "data"})
    
    return local_items, local_data
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0, "Mutations on local copies should not be flagged");
    }

    #[test]
    fn test_slice_deletion() {
        let code = r#"
def remove_elements(items):
    del items[0:2]
    del items[-1]
    return items
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        for v in &violations {
            assert!(v.message.contains("mutates its argument 'items' by deleting an element"));
        }
    }

    #[test]
    fn test_varargs_and_kwargs_mutation() {
        let code = r#"
def process_varargs(*args, **kwargs):
    # args is a tuple, can't be mutated in-place
    # but if someone passes a mutable object in args, that can be mutated
    if len(args) > 0:
        args[0].append("item")  # This would be a mutation if args[0] is a list
    
    # kwargs can be treated like a dict parameter
    kwargs["new_key"] = "value"
    kwargs.pop("old_key", None)
    return args, kwargs
"#;
        let violations = check_code(code);
        // Should catch kwargs mutations
        assert!(violations.len() >= 2);
        assert!(violations.iter().any(|v| v.message.contains("'kwargs'")));
    }
}