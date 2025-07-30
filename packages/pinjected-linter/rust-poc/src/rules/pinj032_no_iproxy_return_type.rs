//! PINJ032: @injected/@instance functions should not have IProxy return type
//!
//! Functions decorated with @injected or @instance never return IProxy types.
//! If they are annotated to return IProxy, it indicates a misunderstanding of
//! how pinjected works. These functions should have ordinary return type annotations.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::{Expr, Stmt};

pub struct NoIProxyReturnTypeRule {}

impl NoIProxyReturnTypeRule {
    pub fn new() -> Self {
        Self {}
    }

    /// Check if an expression represents IProxy type
    fn is_iproxy_type(&self, expr: &Expr) -> bool {
        match expr {
            Expr::Name(name) => name.id.as_str() == "IProxy",
            Expr::Attribute(attr) => {
                if let Expr::Name(name) = &*attr.value {
                    name.id.as_str() == "pinjected" && attr.attr.as_str() == "IProxy"
                } else {
                    false
                }
            }
            // Handle generic types like IProxy[SomeType]
            Expr::Subscript(subscript) => match &*subscript.value {
                Expr::Name(name) => name.id.as_str() == "IProxy",
                Expr::Attribute(attr) => {
                    if let Expr::Name(name) = &*attr.value {
                        name.id.as_str() == "pinjected" && attr.attr.as_str() == "IProxy"
                    } else {
                        false
                    }
                }
                _ => false,
            },
            _ => false,
        }
    }

    /// Check function definition for IProxy return type
    fn check_function(
        &self,
        func: &rustpython_ast::StmtFunctionDef,
        file_path: &str,
        violations: &mut Vec<Violation>,
    ) {
        // Check if function has @injected or @instance decorator
        let has_special_decorator = has_injected_decorator(func) || has_instance_decorator(func);

        if !has_special_decorator {
            return;
        }

        // Check return annotation
        if let Some(returns) = &func.returns {
            if self.is_iproxy_type(returns) {
                violations.push(Violation {
                    rule_id: "PINJ032".to_string(),
                    message: format!(
                        "@injected/@instance function '{}' has IProxy return type annotation. This indicates a misunderstanding of how pinjected works. @injected and @instance functions should have ordinary return type annotations, not IProxy. IProxy is an internal interface used by pinjected. Please read the pinjected documentation to understand the correct usage.",
                        func.name
                    ),
                    offset: func.range.start().to_usize(),
                    file_path: file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
    }

    /// Check async function definition for IProxy return type
    fn check_async_function(
        &self,
        func: &rustpython_ast::StmtAsyncFunctionDef,
        file_path: &str,
        violations: &mut Vec<Violation>,
    ) {
        // Check if function has @injected or @instance decorator
        let has_special_decorator =
            has_injected_decorator_async(func) || has_instance_decorator_async(func);

        if !has_special_decorator {
            return;
        }

        // Check return annotation
        if let Some(returns) = &func.returns {
            if self.is_iproxy_type(returns) {
                violations.push(Violation {
                    rule_id: "PINJ032".to_string(),
                    message: format!(
                        "@injected/@instance function '{}' has IProxy return type annotation. This indicates a misunderstanding of how pinjected works. @injected and @instance functions should have ordinary return type annotations, not IProxy. IProxy is an internal interface used by pinjected. Please read the pinjected documentation to understand the correct usage.",
                        func.name
                    ),
                    offset: func.range.start().to_usize(),
                    file_path: file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
    }

    /// Check statements
    fn check_stmt(&self, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                self.check_function(func, file_path, violations);
                // Check nested functions
                for stmt in &func.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                self.check_async_function(func, file_path, violations);
                // Check nested functions
                for stmt in &func.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            _ => {}
        }
    }
}

impl LintRule for NoIProxyReturnTypeRule {
    fn rule_id(&self) -> &str {
        "PINJ032"
    }

    fn description(&self) -> &str {
        "@injected/@instance functions should not have IProxy return type annotation"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Check the current statement
        self.check_stmt(context.stmt, context.file_path, &mut violations);

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
        let rule = NoIProxyReturnTypeRule::new();
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
    fn test_injected_with_iproxy_return() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def get_service() -> IProxy:
    # ERROR: IProxy return type
    return ServiceImpl()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ032");
        assert!(violations[0].message.contains("get_service"));
        assert!(violations[0].message.contains("misunderstanding"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_instance_with_iproxy_return() {
        let code = r#"
from pinjected import instance, IProxy

@instance
def database_connection() -> IProxy:
    # ERROR: IProxy return type
    return DatabaseConnection()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ032");
        assert!(violations[0].message.contains("database_connection"));
    }

    #[test]
    fn test_iproxy_with_type_parameter() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def get_handler() -> IProxy[Handler]:
    # ERROR: IProxy[T] return type
    return HandlerImpl()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ032");
    }

    #[test]
    fn test_pinjected_iproxy() {
        let code = r#"
import pinjected

@pinjected.injected
def get_processor() -> pinjected.IProxy:
    # ERROR: pinjected.IProxy return type
    return ProcessorImpl()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ032");
    }

    #[test]
    fn test_async_functions() {
        let code = r#"
from pinjected import injected, instance, IProxy

@injected
async def async_service() -> IProxy:
    # ERROR: IProxy return type in async
    return await create_service()

@instance
async def async_handler() -> IProxy[AsyncHandler]:
    # ERROR: IProxy[T] return type in async
    return AsyncHandlerImpl()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ032");
            assert_eq!(v.severity, Severity::Error);
        }
    }

    #[test]
    fn test_correct_return_types() {
        let code = r#"
from pinjected import injected, instance

@injected
def get_service() -> ServiceInterface:
    # OK: Correct return type
    return ServiceImpl()

@instance
def database() -> Database:
    # OK: Correct return type
    return PostgresDatabase()

@injected
async def async_handler() -> AsyncHandler:
    # OK: Correct return type
    return AsyncHandlerImpl()

@instance
def config() -> dict[str, Any]:
    # OK: Correct return type
    return {"key": "value"}
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_return_annotation() {
        let code = r#"
from pinjected import injected, instance

@injected
def get_service():
    # OK: No return annotation
    return ServiceImpl()

@instance
def database():
    # OK: No return annotation
    return Database()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_regular_functions_with_iproxy() {
        let code = r#"
from pinjected import IProxy

def regular_function() -> IProxy:
    # OK: Not decorated with @injected/@instance
    return something

class MyClass:
    def method(self) -> IProxy:
        # OK: Not decorated
        return something
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_class_methods() {
        let code = r#"
from pinjected import injected, instance, IProxy

class ServiceFactory:
    @instance
    def create_service(self) -> IProxy:
        # ERROR: IProxy in instance method
        return Service()
    
    @injected
    def process_data(self) -> IProxy[Result]:
        # ERROR: IProxy[T] in injected method
        return process()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ032");
        }
    }
}
