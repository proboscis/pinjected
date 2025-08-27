//! PINJ051: No setter methods
//!
//! Classes should not have setter methods by default to minimize mutable state.
//! Setter methods should be replaced with constructor parameters or immutable
//! patterns. Setter methods are only allowed with explicit `# noqa: PINJ051` comment.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{StmtClassDef, StmtFunctionDef, StmtAsyncFunctionDef, Stmt};

pub struct NoSetterMethodsRule;

impl NoSetterMethodsRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a method name indicates it's a setter method
    fn is_setter_method_name(name: &str) -> bool {
        // Check if the method name starts with 'set_'
        name.starts_with("set_")
    }

    /// Check if the method returns None (typical for setters)
    fn returns_none(func: &StmtFunctionDef) -> bool {
        // Check if there's a return annotation of None
        if let Some(returns) = &func.returns {
            if let rustpython_ast::Expr::Constant(constant) = &**returns {
                if let rustpython_ast::Constant::None = &constant.value {
                    return true;
                }
            }
            if let rustpython_ast::Expr::Name(name) = &**returns {
                if name.id.as_str() == "None" {
                    return true;
                }
            }
            // If there's a return annotation that's not None, it's not a typical setter
            return false;
        }
        
        // If no return annotation, assume it returns None (typical for setters)
        true
    }

    /// Check if the async method returns None (typical for setters)
    fn async_returns_none(func: &StmtAsyncFunctionDef) -> bool {
        // Check if there's a return annotation of None
        if let Some(returns) = &func.returns {
            if let rustpython_ast::Expr::Constant(constant) = &**returns {
                if let rustpython_ast::Constant::None = &constant.value {
                    return true;
                }
            }
            if let rustpython_ast::Expr::Name(name) = &**returns {
                if name.id.as_str() == "None" {
                    return true;
                }
            }
            // If there's a return annotation that's not None, it's not a typical setter
            return false;
        }
        
        // If no return annotation, assume it returns None (typical for setters)
        true
    }

    /// Check a method definition within a class
    fn check_method(&self, func: &StmtFunctionDef, class_name: &str) -> Option<Violation> {
        // Check if it's a setter method
        if Self::is_setter_method_name(&func.name) && Self::returns_none(func) {
            let message = format!(
                "Method '{}' in class '{}' is a setter method. Setter methods are forbidden by default to minimize mutable state. Consider setting values in the constructor or using immutable patterns. If a setter is truly necessary, add '# noqa: PINJ051' to allow it.",
                func.name.as_str(),
                class_name
            );

            return Some(Violation {
                rule_id: self.rule_id().to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Error,
                fix: None,
            });
        }

        None
    }

    /// Check an async method definition within a class
    fn check_async_method(&self, func: &StmtAsyncFunctionDef, class_name: &str) -> Option<Violation> {
        // Check if it's a setter method
        if Self::is_setter_method_name(&func.name) && Self::async_returns_none(func) {
            let message = format!(
                "Async method '{}' in class '{}' is a setter method. Setter methods are forbidden by default to minimize mutable state. Consider setting values in the constructor or using immutable patterns. If a setter is truly necessary, add '# noqa: PINJ051' to allow it.",
                func.name.as_str(),
                class_name
            );

            return Some(Violation {
                rule_id: self.rule_id().to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Error,
                fix: None,
            });
        }

        None
    }

    /// Check all methods in a class
    fn check_class(&self, class: &StmtClassDef) -> Vec<Violation> {
        let mut violations = Vec::new();
        let class_name = class.name.as_str();

        // Check all statements in the class body
        for stmt in &class.body {
            match stmt {
                Stmt::FunctionDef(func) => {
                    if let Some(violation) = self.check_method(func, class_name) {
                        violations.push(violation);
                    }
                }
                Stmt::AsyncFunctionDef(func) => {
                    if let Some(violation) = self.check_async_method(func, class_name) {
                        violations.push(violation);
                    }
                }
                Stmt::ClassDef(nested_class) => {
                    // Recursively check nested classes
                    violations.extend(self.check_class(nested_class));
                }
                _ => {}
            }
        }

        violations
    }
}

impl LintRule for NoSetterMethodsRule {
    fn rule_id(&self) -> &str {
        "PINJ051"
    }

    fn description(&self) -> &str {
        "Classes should not have setter methods to minimize mutable state"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::ClassDef(class) => {
                for mut violation in self.check_class(class) {
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
        let rule = NoSetterMethodsRule::new();
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
    fn test_basic_setter_method() {
        let code = r#"
class MarketTracker:
    def __init__(self):
        self._market = "US"
    
    def set_market(self, market: str) -> None:
        """Set which market to track."""
        self._market = market
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ051");
        assert!(violations[0].message.contains("set_market"));
        assert!(violations[0].message.contains("setter method"));
    }

    #[test]
    fn test_setter_without_return_annotation() {
        let code = r#"
class Config:
    def __init__(self):
        self._value = None
    
    def set_value(self, value):
        self._value = value
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ051");
    }

    #[test]
    fn test_async_setter_method() {
        let code = r#"
class AsyncManager:
    def __init__(self):
        self._state = None
    
    async def set_state(self, state: str) -> None:
        """Set the state asynchronously."""
        self._state = state
        await self._notify_listeners()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ051");
        assert!(violations[0].message.contains("Async method"));
    }

    #[test]
    fn test_not_setter_method() {
        let code = r#"
class Calculator:
    def get_result(self) -> int:
        return 42
    
    def setup_environment(self) -> None:
        """Not a setter - different prefix."""
        pass
    
    def reset_state(self) -> None:
        """Not a setter - different prefix."""
        self._state = None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_setter_with_return_value() {
        let code = r#"
class Builder:
    def set_option(self, option: str) -> 'Builder':
        """Fluent setter that returns self - still a setter pattern."""
        self._option = option
        return self
"#;
        let violations = check_code(code);
        // This should NOT be flagged since it returns something other than None
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_multiple_setters_in_class() {
        let code = r#"
class Configuration:
    def __init__(self):
        self._host = None
        self._port = None
    
    def set_host(self, host: str) -> None:
        self._host = host
    
    def set_port(self, port: int) -> None:
        self._port = port
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        // Should catch both set_host and set_port
    }

    #[test]
    fn test_setter_in_nested_class() {
        let code = r#"
class Outer:
    class Inner:
        def set_value(self, value: str) -> None:
            self._value = value
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("Inner"));
    }

    #[test]
    fn test_setter_outside_class() {
        let code = r#"
def set_global_config(config: dict) -> None:
    """This is not a method, so it shouldn't be flagged."""
    global _config
    _config = config
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_mutable_attribute_setter() {
        let code = r#"
class MarketStatusTracker:
    def __init__(self):
        self._mut_market = "US"
    
    def set_market(self, market: str) -> None:
        """Set which market to track (e.g., 'US', 'EU', 'ASIA').
        
        Args:
            market: Market identifier to track.
        """
        self._mut_market = market
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ051");
        assert!(violations[0].message.contains("set_market"));
    }
}