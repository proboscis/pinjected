//! PINJ055: No lambda in direct design() function calls
//!
//! This rule forbids passing lambda functions as keyword arguments to design() calls.
//! Lambda functions will be injected as-is rather than being called, which is rarely intended.
//! Use @instance or @injected decorated functions instead.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{is_injected_decorator, is_instance_decorator};
use rustpython_ast::{Expr, ExprCall, Ranged, Stmt};
use std::collections::HashMap;

pub struct NoLambdaInDesignCallRule {
    /// Track decorated functions in the module
    decorated_functions: HashMap<String, bool>,
}

impl NoLambdaInDesignCallRule {
    pub fn new() -> Self {
        Self {
            decorated_functions: HashMap::new(),
        }
    }

    /// Check if a call is a design() call
    fn is_design_call(&self, call: &ExprCall) -> bool {
        match &*call.func {
            Expr::Name(name) => name.id.as_str() == "design",
            Expr::Attribute(attr) => {
                if let Expr::Name(module) = &*attr.value {
                    module.id.as_str() == "pinjected" && attr.attr.as_str() == "design"
                } else {
                    false
                }
            }
            _ => false,
        }
    }

    /// Check design() call keyword arguments for lambdas
    fn check_design_call(&self, call: &ExprCall) -> Vec<Violation> {
        let mut violations = Vec::new();

        if !self.is_design_call(call) {
            return violations;
        }

        // Check keyword arguments for lambdas
        for keyword in &call.keywords {
            if let Some(arg_name) = &keyword.arg {
                match &keyword.value {
                    Expr::Lambda(lambda) => {
                        violations.push(Violation {
                            rule_id: "PINJ055".to_string(),
                            message: format!(
                                "Lambda function cannot be passed as '{}' argument to design(). \
                                 Lambda functions will be injected as the function itself, not its return value. \
                                 Use @instance or @injected decorated functions instead. \
                                 Example: @instance def {}(): return <value>",
                                arg_name, arg_name
                            ),
                            offset: lambda.range.start().to_usize(),
                            file_path: String::new(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }
                    Expr::Name(name) => {
                        // Check if this is a non-decorated function
                        let func_name = name.id.as_str();
                        if let Some(&is_decorated) = self.decorated_functions.get(func_name) {
                            if !is_decorated {
                                violations.push(Violation {
                                    rule_id: "PINJ055".to_string(),
                                    message: format!(
                                        "Function '{}' passed as '{}' argument to design() is not decorated with @injected or @instance. \
                                         Non-decorated functions will be injected as-is rather than being called.",
                                        func_name, arg_name
                                    ),
                                    offset: keyword.value.range().start().to_usize(),
                                    file_path: String::new(),
                                    severity: Severity::Error,
                                    fix: None,
                                });
                            }
                        }
                    }
                    _ => {}
                }
            }
        }

        violations
    }

    /// Pre-scan module to find all decorated functions
    fn scan_module(&mut self, stmts: &[Stmt]) {
        for stmt in stmts {
            match stmt {
                Stmt::FunctionDef(func) => {
                    let is_decorated = func
                        .decorator_list
                        .iter()
                        .any(|d| is_injected_decorator(d) || is_instance_decorator(d));
                    self.decorated_functions
                        .insert(func.name.to_string(), is_decorated);
                }
                Stmt::AsyncFunctionDef(func) => {
                    let is_decorated = func
                        .decorator_list
                        .iter()
                        .any(|d| is_injected_decorator(d) || is_instance_decorator(d));
                    self.decorated_functions
                        .insert(func.name.to_string(), is_decorated);
                }
                Stmt::ClassDef(cls) => {
                    // Scan methods inside classes
                    self.scan_module(&cls.body);
                }
                _ => {}
            }
        }
    }
}

impl LintRule for NoLambdaInDesignCallRule {
    fn rule_id(&self) -> &str {
        "PINJ055"
    }

    fn description(&self) -> &str {
        "Lambda functions cannot be passed as arguments to design() calls"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        // Create a new rule instance and scan the module
        let mut rule = NoLambdaInDesignCallRule::new();
        if let rustpython_ast::Mod::Module(module) = context.ast {
            rule.scan_module(&module.body);
        }

        // Then check the specific statement
        match context.stmt {
            // Check assignments like: my_design = design(...)
            Stmt::Assign(assign) => {
                if let Expr::Call(call) = &*assign.value {
                    let mut call_violations = rule.check_design_call(call);
                    for violation in &mut call_violations {
                        violation.file_path = context.file_path.to_string();
                    }
                    violations.extend(call_violations);
                }
            }
            // Check expression statements like: design(...)
            Stmt::Expr(expr_stmt) => {
                if let Expr::Call(call) = &*expr_stmt.value {
                    let mut call_violations = rule.check_design_call(call);
                    for violation in &mut call_violations {
                        violation.file_path = context.file_path.to_string();
                    }
                    violations.extend(call_violations);
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
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let rule = NoLambdaInDesignCallRule::new();
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
    fn test_lambda_in_design_kwargs() {
        let code = r#"
from pinjected import design

my_design = design(
    config=lambda: {'debug': True},
    logger=lambda: Logger()
)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ055"));
        assert!(violations[0].message.contains("config"));
        assert!(violations[0].message.contains("Lambda function cannot be passed"));
        assert!(violations[1].message.contains("logger"));
    }

    #[test]
    fn test_single_lambda_argument() {
        let code = r#"
from pinjected import design

d = design(service=lambda: Service())
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ055");
        assert!(violations[0].message.contains("service"));
        assert!(violations[0].message.contains("Lambda function"));
    }

    #[test]
    fn test_undecorated_function_in_design_kwargs() {
        let code = r#"
from pinjected import design

def get_config():
    return {'debug': True}

my_design = design(config=get_config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ055");
        assert!(violations[0].message.contains("not decorated"));
        assert!(violations[0].message.contains("get_config"));
    }

    #[test]
    fn test_valid_decorated_function_in_design_kwargs() {
        let code = r#"
from pinjected import design, instance, injected

@instance
def get_config():
    return {'debug': True}

@injected
def get_logger(config, /):
    return Logger(config)

my_design = design(
    config=get_config,
    logger=get_logger
)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_design_call_without_kwargs() {
        let code = r#"
from pinjected import design

my_design = design()
base_design = design()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_pinjected_module_design_call() {
        let code = r#"
import pinjected

my_design = pinjected.design(
    service=lambda: Service(),
    database=lambda: Database()
)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 2);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ055"));
        assert!(violations[0].message.contains("service"));
        assert!(violations[1].message.contains("database"));
    }

    #[test]
    fn test_expression_statement_design() {
        let code = r#"
from pinjected import design

# Design call as expression statement (not assigned)
design(
    config=lambda: {'port': 8080}
)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ055");
        assert!(violations[0].message.contains("config"));
    }

    #[test]
    fn test_mixed_valid_and_invalid() {
        let code = r#"
from pinjected import design, instance

@instance
def get_database():
    return Database()

my_design = design(
    database=get_database,  # Valid
    cache=lambda: Cache(),  # Invalid
    config={'debug': True}  # Valid (not a function)
)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ055");
        assert!(violations[0].message.contains("cache"));
    }

    #[test]
    fn test_nested_lambda() {
        let code = r#"
from pinjected import design

def wrapper():
    return design(
        service=lambda: Service()
    )
"#;
        // Only checks top-level statements
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_non_design_call_with_lambda() {
        let code = r#"
# Other functions with lambda should not trigger
result = map(lambda x: x * 2, [1, 2, 3])
filtered = filter(lambda x: x > 0, [-1, 0, 1])
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_async_functions() {
        let code = r#"
from pinjected import design, instance

@instance
async def get_async_service():
    return await create_service()

async def undecorated_async():
    return Service()

my_design = design(
    service=get_async_service,  # Valid
    other=undecorated_async     # Invalid
)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ055");
        assert!(violations[0].message.contains("undecorated_async"));
    }
}