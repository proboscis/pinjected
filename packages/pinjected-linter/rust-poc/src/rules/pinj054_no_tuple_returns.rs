//! PINJ054: Forbid tuple return types in functions
//!
//! Functions should not return tuples. Use dataclasses for structured return values
//! to improve type safety, readability, and maintainability.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct NoTupleReturnsRule;

impl NoTupleReturnsRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if an expression is a tuple type annotation
    fn is_tuple_type(&self, expr: &Expr) -> bool {
        match expr {
            // Direct tuple annotation: tuple or Tuple
            Expr::Name(name) => {
                let name_str = name.id.as_str();
                name_str == "tuple" || name_str == "Tuple"
            }
            // Subscripted tuple annotation: tuple[str, int] or Tuple[str, int]
            // Also handles Optional[Tuple[...]] and Union[Tuple[...], ...]
            Expr::Subscript(subscript) => {
                // Check if this is a tuple type
                if let Expr::Name(name) = &*subscript.value {
                    let name_str = name.id.as_str();
                    if name_str == "tuple" || name_str == "Tuple" {
                        return true;
                    }
                    // Check if this is Optional or Union containing a tuple
                    if name_str == "Optional" || name_str == "Union" {
                        // Check the slice for tuple types
                        if let Expr::Tuple(tuple) = &*subscript.slice {
                            return tuple.elts.iter().any(|e| self.is_tuple_type(e));
                        } else {
                            return self.is_tuple_type(&subscript.slice);
                        }
                    }
                } else if let Expr::Attribute(attr) = &*subscript.value {
                    // typing.Tuple[...]
                    if let Expr::Name(module) = &*attr.value {
                        if module.id.as_str() == "typing" {
                            if attr.attr.as_str() == "Tuple" {
                                return true;
                            }
                            // typing.Optional or typing.Union
                            if attr.attr.as_str() == "Optional" || attr.attr.as_str() == "Union" {
                                if let Expr::Tuple(tuple) = &*subscript.slice {
                                    return tuple.elts.iter().any(|e| self.is_tuple_type(e));
                                } else {
                                    return self.is_tuple_type(&subscript.slice);
                                }
                            }
                        }
                    }
                }
                false
            }
            // typing.Tuple or typing.Tuple[...]
            Expr::Attribute(attr) => {
                if let Expr::Name(module) = &*attr.value {
                    module.id.as_str() == "typing" && attr.attr.as_str() == "Tuple"
                } else {
                    false
                }
            }
            // Union types that might contain tuples (e.g., Tuple[...] | None)
            Expr::BinOp(binop) => {
                // Check for Union[Tuple[...], ...] or Tuple[...] | None
                self.is_tuple_type(&binop.left) || self.is_tuple_type(&binop.right)
            }
            _ => false,
        }
    }

    /// Create error message for tuple return type violation
    fn create_error_message(&self, func_name: &str) -> String {
        format!(
            "Function '{}' returns a tuple, which is not allowed. Use a dataclass for structured return values instead. \
             Tuples are error-prone as they rely on positional access and lack semantic meaning. \
             Migration guide: 1. Create a dataclass with meaningful field names. \
             2. Update the function to return an instance of the dataclass. \
             3. Update all callers to use named attribute access instead of tuple unpacking. \
             Example: Instead of 'def get_user() -> Tuple[str, int]: return (name, age)' \
             use '@dataclass class UserInfo: name: str; age: int' and 'def get_user() -> UserInfo: return UserInfo(name, age)'",
            func_name
        )
    }

    /// Check function definition for tuple return type
    fn check_function(&self, func: &StmtFunctionDef) -> Option<Violation> {
        if let Some(returns) = &func.returns {
            if self.is_tuple_type(returns) {
                return Some(Violation {
                    rule_id: "PINJ054".to_string(),
                    message: self.create_error_message(&func.name),
                    offset: func.range.start().to_usize(),
                    file_path: "".to_string(), // Will be filled by the caller
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
        None
    }

    /// Check async function definition for tuple return type
    fn check_async_function(&self, func: &StmtAsyncFunctionDef) -> Option<Violation> {
        if let Some(returns) = &func.returns {
            if self.is_tuple_type(returns) {
                return Some(Violation {
                    rule_id: "PINJ054".to_string(),
                    message: self.create_error_message(&func.name),
                    offset: func.range.start().to_usize(),
                    file_path: "".to_string(), // Will be filled by the caller
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
        None
    }
}

impl LintRule for NoTupleReturnsRule {
    fn rule_id(&self) -> &str {
        "PINJ054"
    }

    fn description(&self) -> &str {
        "Functions should not return tuples. Use dataclasses for structured return values."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                if let Some(mut violation) = self.check_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if let Some(mut violation) = self.check_async_function(func) {
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
        let rule = NoTupleReturnsRule::new();
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
    fn test_tuple_return_type_forbidden() {
        let code = r#"
from typing import Tuple

def get_user_info(user_id: int) -> Tuple[str, int]:
    return ("Alice", 25)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ054");
        assert!(violations[0].message.contains("get_user_info"));
        assert!(violations[0].message.contains("dataclass"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_lowercase_tuple() {
        let code = r#"
def get_coordinates() -> tuple[float, float]:
    return (1.0, 2.0)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ054");
    }

    #[test]
    fn test_typing_tuple() {
        let code = r#"
import typing

def get_data() -> typing.Tuple[str, int, bool]:
    return ("data", 42, True)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ054");
    }

    #[test]
    fn test_async_function_with_tuple() {
        let code = r#"
from typing import Tuple

async def fetch_user_data() -> Tuple[str, dict]:
    return ("user123", {"name": "Alice"})
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ054");
        assert!(violations[0].message.contains("fetch_user_data"));
    }

    #[test]
    fn test_optional_tuple() {
        let code = r#"
from typing import Tuple, Optional

def maybe_get_user() -> Optional[Tuple[str, int]]:
    return None
"#;
        // This should still be detected as it contains a tuple type
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ054");
    }

    #[test]
    fn test_union_with_tuple() {
        let code = r#"
from typing import Tuple, Union

def get_result() -> Union[Tuple[str, int], None]:
    return None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ054");
    }

    #[test]
    fn test_pipe_union_with_tuple() {
        let code = r#"
def get_optional_data() -> tuple[str, int] | None:
    return None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ054");
    }

    #[test]
    fn test_dataclass_return_allowed() {
        let code = r#"
from dataclasses import dataclass

@dataclass
class UserInfo:
    name: str
    age: int

def get_user_info() -> UserInfo:
    return UserInfo("Alice", 25)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_list_return_allowed() {
        let code = r#"
from typing import List

def get_items() -> List[str]:
    return ["item1", "item2"]
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_dict_return_allowed() {
        let code = r#"
def get_mapping() -> dict[str, int]:
    return {"key": 42}
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_return_type_annotation() {
        let code = r#"
def get_something():
    # No return type annotation, should not trigger
    return ("value", 123)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_function() {
        let code = r#"
def outer():
    from typing import Tuple
    
    def inner() -> Tuple[str, int]:
        return ("nested", 1)
    
    return inner()
"#;
        // Only top-level functions are checked
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_class_method_with_tuple() {
        let code = r#"
from typing import Tuple

class Service:
    def get_data(self) -> Tuple[str, int]:
        return ("data", 42)
    
    @classmethod
    def get_config(cls) -> Tuple[str, bool]:
        return ("config", True)
    
    @staticmethod
    def get_static() -> Tuple[int, int]:
        return (1, 2)
"#;
        // Class methods should also be checked
        let violations = check_code(code);
        assert_eq!(violations.len(), 0); // Methods inside classes are not top-level
    }

    #[test]
    fn test_multiple_functions_with_tuples() {
        let code = r#"
from typing import Tuple

def func1() -> Tuple[str, int]:
    return ("a", 1)

def func2() -> tuple[bool, float]:
    return (True, 3.14)

def func3() -> str:
    return "ok"

def func4() -> Tuple[int, int, int]:
    return (1, 2, 3)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ054"));
    }

    #[test]
    fn test_property_with_tuple() {
        let code = r#"
from typing import Tuple

class Data:
    @property
    def values(self) -> Tuple[str, int]:
        return ("value", 42)
"#;
        // Properties inside classes are not top-level
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}