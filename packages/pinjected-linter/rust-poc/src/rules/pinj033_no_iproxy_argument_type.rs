//! PINJ033: @injected/@instance functions should not have IProxy argument type annotations
//!
//! Function arguments in @injected or @instance decorated functions should not have IProxy
//! as their type annotation. This indicates a misunderstanding of how pinjected works.
//! These function arguments should have ordinary type annotations.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::{ArgWithDefault, Expr, Stmt};

pub struct NoIProxyArgumentTypeRule {}

impl NoIProxyArgumentTypeRule {
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

    /// Check function arguments for IProxy type annotations
    fn check_arguments(
        &self,
        args: &[ArgWithDefault],
        func_name: &str,
        file_path: &str,
        _func_offset: usize,
        violations: &mut Vec<Violation>,
    ) {
        for arg in args {
            // Skip 'self' parameter in methods
            if arg.def.arg.as_str() == "self" {
                continue;
            }

            if let Some(annotation) = &arg.def.annotation {
                if self.is_iproxy_type(annotation) {
                    violations.push(Violation {
                        rule_id: "PINJ033".to_string(),
                        message: format!(
                            "@injected/@instance function '{}' has argument '{}' with IProxy type annotation. \
                            This indicates a misunderstanding of how pinjected works. \
                            Function arguments in @injected and @instance functions should have ordinary type annotations, not IProxy. \
                            IProxy is an internal interface used by pinjected. \
                            Dependencies are resolved automatically and passed as actual instances, not proxies.",
                            func_name, arg.def.arg
                        ),
                        offset: arg.def.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                    });
                }
            }
        }
    }

    /// Check function definition for IProxy argument types
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

        // Check all arguments
        self.check_arguments(
            &func.args.args,
            &func.name,
            file_path,
            func.range.start().to_usize(),
            violations,
        );

        // Check positional-only arguments
        self.check_arguments(
            &func.args.posonlyargs,
            &func.name,
            file_path,
            func.range.start().to_usize(),
            violations,
        );

        // Check keyword-only arguments
        self.check_arguments(
            &func.args.kwonlyargs,
            &func.name,
            file_path,
            func.range.start().to_usize(),
            violations,
        );

        // Check vararg
        if let Some(vararg) = &func.args.vararg {
            if let Some(annotation) = &vararg.annotation {
                if self.is_iproxy_type(annotation) {
                    violations.push(Violation {
                        rule_id: "PINJ033".to_string(),
                        message: format!(
                            "@injected/@instance function '{}' has *args with IProxy type annotation. \
                            This indicates a misunderstanding of how pinjected works.",
                            func.name
                        ),
                        offset: vararg.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                    });
                }
            }
        }

        // Check kwarg
        if let Some(kwarg) = &func.args.kwarg {
            if let Some(annotation) = &kwarg.annotation {
                if self.is_iproxy_type(annotation) {
                    violations.push(Violation {
                        rule_id: "PINJ033".to_string(),
                        message: format!(
                            "@injected/@instance function '{}' has **kwargs with IProxy type annotation. \
                            This indicates a misunderstanding of how pinjected works.",
                            func.name
                        ),
                        offset: kwarg.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                    });
                }
            }
        }
    }

    /// Check async function definition for IProxy argument types
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

        // Check all arguments
        self.check_arguments(
            &func.args.args,
            &func.name,
            file_path,
            func.range.start().to_usize(),
            violations,
        );

        // Check positional-only arguments
        self.check_arguments(
            &func.args.posonlyargs,
            &func.name,
            file_path,
            func.range.start().to_usize(),
            violations,
        );

        // Check keyword-only arguments
        self.check_arguments(
            &func.args.kwonlyargs,
            &func.name,
            file_path,
            func.range.start().to_usize(),
            violations,
        );

        // Check vararg
        if let Some(vararg) = &func.args.vararg {
            if let Some(annotation) = &vararg.annotation {
                if self.is_iproxy_type(annotation) {
                    violations.push(Violation {
                        rule_id: "PINJ033".to_string(),
                        message: format!(
                            "@injected/@instance function '{}' has *args with IProxy type annotation. \
                            This indicates a misunderstanding of how pinjected works.",
                            func.name
                        ),
                        offset: vararg.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                    });
                }
            }
        }

        // Check kwarg
        if let Some(kwarg) = &func.args.kwarg {
            if let Some(annotation) = &kwarg.annotation {
                if self.is_iproxy_type(annotation) {
                    violations.push(Violation {
                        rule_id: "PINJ033".to_string(),
                        message: format!(
                            "@injected/@instance function '{}' has **kwargs with IProxy type annotation. \
                            This indicates a misunderstanding of how pinjected works.",
                            func.name
                        ),
                        offset: kwarg.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                    });
                }
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

impl LintRule for NoIProxyArgumentTypeRule {
    fn rule_id(&self) -> &str {
        "PINJ033"
    }

    fn description(&self) -> &str {
        "@injected/@instance functions should not have IProxy argument type annotations"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            rustpython_ast::Stmt::FunctionDef(func) => {
                self.check_function(func, context.file_path, &mut violations);
            }
            rustpython_ast::Stmt::AsyncFunctionDef(func) => {
                self.check_async_function(func, context.file_path, &mut violations);
            }
            rustpython_ast::Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.check_stmt(stmt, context.file_path, &mut violations);
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
        let rule = NoIProxyArgumentTypeRule::new();
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
    fn test_injected_with_iproxy_argument() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def get_service(db: IProxy[Database], logger,/):
    # ERROR: IProxy argument type
    return ServiceImpl(db, logger)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ033");
        assert!(violations[0].message.contains("get_service"));
        assert!(violations[0].message.contains("db"));
        assert!(violations[0].message.contains("misunderstanding"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_instance_with_iproxy_argument() {
        let code = r#"
from pinjected import instance, IProxy

@instance
def api_client(config: IProxy,/):
    # ERROR: IProxy argument type
    return APIClient(config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ033");
        assert!(violations[0].message.contains("api_client"));
        assert!(violations[0].message.contains("config"));
    }

    #[test]
    fn test_multiple_iproxy_arguments() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def complex_service(
    db: IProxy[Database],
    cache: Cache,
    config: IProxy,
    logger,
    /
):
    # ERROR: Multiple IProxy arguments
    return ComplexService(db, cache, config, logger)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ033");
            assert!(v.message.contains("complex_service"));
        }
    }

    #[test]
    fn test_pinjected_iproxy() {
        let code = r#"
import pinjected

@pinjected.injected
def get_processor(queue: pinjected.IProxy,/):
    # ERROR: pinjected.IProxy argument type
    return ProcessorImpl(queue)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ033");
        assert!(violations[0].message.contains("queue"));
    }

    #[test]
    fn test_async_functions() {
        let code = r#"
from pinjected import injected, instance, IProxy

@injected
async def async_service(cache: IProxy[Cache], db: IProxy,/):
    # ERROR: IProxy argument types in async
    return await create_service(cache, db)

@instance
async def async_handler(logger: Logger, queue: IProxy,/):
    # ERROR: IProxy argument in async instance
    return AsyncHandlerImpl(logger, queue)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ033");
            assert_eq!(v.severity, Severity::Error);
        }
    }

    #[test]
    fn test_correct_argument_types() {
        let code = r#"
from pinjected import injected, instance

@injected
def get_service(db: Database, logger: Logger,/):
    # OK: Correct argument types
    return ServiceImpl(db, logger)

@instance
def api_client(config: dict[str, Any],/):
    # OK: Correct argument type
    return APIClient(config)

@injected
async def async_handler(cache: Cache, db: Database,/):
    # OK: Correct argument types
    return AsyncHandlerImpl(cache, db)

@instance
def factory(settings: Settings, logger: Logger,/):
    # OK: All arguments have proper types
    return Factory(settings, logger)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_annotation() {
        let code = r#"
from pinjected import injected, instance

@injected
def get_service(db, logger,/):
    # OK: No annotation
    return ServiceImpl(db, logger)

@instance
def api_client(config,/):
    # OK: No annotation
    return APIClient(config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_regular_functions_with_iproxy() {
        let code = r#"
from pinjected import IProxy

def regular_function(proxy: IProxy):
    # OK: Not decorated with @injected/@instance
    return something

class MyClass:
    def method(self, proxy: IProxy):
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
    def create_service(self, db: IProxy[Database], logger,/):
        # ERROR: IProxy in instance method argument
        return Service(db, logger)
    
    @injected
    def process_data(self, data: Data, processor: IProxy,/):
        # ERROR: IProxy in injected method argument
        return process(data, processor)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ033");
        }
    }

    #[test]
    fn test_self_parameter_exempt() {
        let code = r#"
from pinjected import instance

class ServiceFactory:
    @instance
    def create_service(self, db: Database,/):
        # OK: self is exempt, db is properly typed
        return Service(db)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_vararg_and_kwarg() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def service(*args: IProxy, **kwargs: IProxy):
    # ERROR: IProxy in *args and **kwargs
    return Service(*args, **kwargs)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ033");
            assert!(v.message.contains("IProxy type annotation"));
        }
    }
}
