use crate::rules::base::LintRule;
use crate::models::{RuleContext, Severity, Violation};
use rustpython_ast::{Arguments, ExprAttribute, ExprName, Stmt, StmtFunctionDef, StmtAsyncFunctionDef};

pub struct NoDefaultDependenciesInInjectedRule;

impl NoDefaultDependenciesInInjectedRule {
    pub fn new() -> Self {
        Self
    }
}

impl LintRule for NoDefaultDependenciesInInjectedRule {
    fn rule_id(&self) -> &str {
        "PINJ048"
    }

    fn description(&self) -> &str {
        "@injected function dependencies (parameters before '/') should not have default values. Configuration should be provided through the design() function instead."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func_def) => {
                if is_injected_decorated(func_def) {
                    violations.extend(check_function_defaults(func_def, context));
                }
            }
            Stmt::AsyncFunctionDef(async_func_def) => {
                if is_async_injected_decorated(async_func_def) {
                    violations.extend(check_async_function_defaults(async_func_def, context));
                }
            }
            _ => {}
        }

        violations
    }
}

fn is_injected_decorated(func_def: &StmtFunctionDef) -> bool {
    func_def.decorator_list.iter().any(|decorator| {
        match decorator {
            rustpython_ast::Expr::Name(ExprName { id, .. }) => id == "injected",
            rustpython_ast::Expr::Attribute(ExprAttribute { attr, value, .. }) => {
                attr == "injected" && matches!(value.as_ref(), rustpython_ast::Expr::Name(ExprName { id, .. }) if id == "pinjected")
            },
            _ => false,
        }
    })
}

fn is_async_injected_decorated(async_func_def: &StmtAsyncFunctionDef) -> bool {
    async_func_def.decorator_list.iter().any(|decorator| {
        match decorator {
            rustpython_ast::Expr::Name(ExprName { id, .. }) => id == "injected",
            rustpython_ast::Expr::Attribute(ExprAttribute { attr, value, .. }) => {
                attr == "injected" && matches!(value.as_ref(), rustpython_ast::Expr::Name(ExprName { id, .. }) if id == "pinjected")
            },
            _ => false,
        }
    })
}

fn check_function_defaults(func_def: &StmtFunctionDef, context: &RuleContext) -> Vec<Violation> {
    let mut violations = Vec::new();
    let args = &func_def.args;
    
    // Find the position of the positional-only separator (/)
    let slash_position = find_slash_position(args);
    
    // First check positional-only args (they can't have defaults in valid Python)
    for arg in &args.posonlyargs {
        // Positional-only args can't have defaults in Python, so this is just defensive
        if arg.default.is_some() {
            violations.push(Violation {
                rule_id: "PINJ048".to_string(),
                message: format!(
                    "Dependency '{}' in @injected function '{}' has a default value. Dependencies should not have defaults.",
                    &arg.def.arg,
                    &func_def.name
                ),
                file_path: context.file_path.to_string(),
                offset: func_def.range.start().to_usize(),
                severity: Severity::Error,
                fix: None,
            });
        }
    }
    
    // Then check regular args up to slash position if no positional-only args
    if args.posonlyargs.is_empty() && slash_position.is_none() {
        // No slash, check all args as dependencies
        for arg in &args.args {
            if arg.default.is_some() {
                violations.push(Violation {
                    rule_id: "PINJ048".to_string(),
                    message: format!(
                        "Dependency '{}' in @injected function '{}' has a default value. Dependencies should not have defaults.",
                        &arg.def.arg,
                        &func_def.name
                    ),
                    file_path: context.file_path.to_string(),
                    offset: func_def.range.start().to_usize(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
    }
    
    violations
}

fn check_async_function_defaults(async_func_def: &StmtAsyncFunctionDef, context: &RuleContext) -> Vec<Violation> {
    let mut violations = Vec::new();
    let args = &async_func_def.args;
    
    // Find the position of the positional-only separator (/)
    let slash_position = find_slash_position(args);
    
    // First check positional-only args (they can't have defaults in valid Python)
    for arg in &args.posonlyargs {
        // Positional-only args can't have defaults in Python, so this is just defensive
        if arg.default.is_some() {
            violations.push(Violation {
                rule_id: "PINJ048".to_string(),
                message: format!(
                    "Dependency '{}' in @injected async function '{}' has a default value. Dependencies should not have defaults.",
                    &arg.def.arg,
                    &async_func_def.name
                ),
                file_path: context.file_path.to_string(),
                offset: async_func_def.range.start().to_usize(),
                severity: Severity::Error,
                fix: None,
            });
        }
    }
    
    // Then check regular args up to slash position if no positional-only args
    if args.posonlyargs.is_empty() && slash_position.is_none() {
        // No slash, check all args as dependencies
        for arg in &args.args {
            if arg.default.is_some() {
                violations.push(Violation {
                    rule_id: "PINJ048".to_string(),
                    message: format!(
                        "Dependency '{}' in @injected async function '{}' has a default value. Dependencies should not have defaults.",
                        &arg.def.arg,
                        &async_func_def.name
                    ),
                    file_path: context.file_path.to_string(),
                    offset: async_func_def.range.start().to_usize(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }
    }
    
    violations
}

fn find_slash_position(args: &Arguments) -> Option<usize> {
    // In Python AST, posonlyargs represents parameters before '/'
    if !args.posonlyargs.is_empty() {
        Some(args.posonlyargs.len())
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_parser::{parse, Mode};

    #[test]
    fn test_injected_with_defaults_and_slash() {
        let code = r#"
@injected
def process_data(logger, database, /, config=None, data=None):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let rule = NoDefaultDependenciesInInjectedRule::new();
        
        // Find the function definition
        let func_stmt = match &ast {
            rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
                matches!(stmt, rustpython_ast::Stmt::FunctionDef(_))
            }).unwrap(),
            _ => panic!("Expected Module"),
        };
        
        let context = RuleContext {
            stmt: func_stmt,
            file_path: "test.py",
            source: code,
            ast: &ast,
        };
        
        let violations = rule.check(&context);
        
        // Should have 0 violations because dependencies (logger, database) before slash have no defaults
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_without_defaults() {
        let code = r#"
@injected
def process_data(logger, database, /, data=None):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let rule = NoDefaultDependenciesInInjectedRule::new();
        
        let func_stmt = match &ast {
            rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
                matches!(stmt, rustpython_ast::Stmt::FunctionDef(_))
            }).unwrap(),
            _ => panic!("Expected Module"),
        };
        
        let context = RuleContext {
            stmt: func_stmt,
            file_path: "test.py",
            source: code,
            ast: &ast,
        };
        
        let violations = rule.check(&context);
        
        // Should have 0 violations - dependencies before slash have no defaults
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_injected_no_slash_with_defaults() {
        let code = r#"
@injected
def get_config(config_service=None):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let rule = NoDefaultDependenciesInInjectedRule::new();
        
        let func_stmt = match &ast {
            rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
                matches!(stmt, rustpython_ast::Stmt::FunctionDef(_))
            }).unwrap(),
            _ => panic!("Expected Module"),
        };
        
        let context = RuleContext {
            stmt: func_stmt,
            file_path: "test.py",
            source: code,
            ast: &ast,
        };
        
        let violations = rule.check(&context);
        
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("config_service"));
    }

    #[test]
    fn test_non_injected_function() {
        let code = r#"
def regular_function(param=None):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let rule = NoDefaultDependenciesInInjectedRule::new();
        
        let func_stmt = match &ast {
            rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
                matches!(stmt, rustpython_ast::Stmt::FunctionDef(_))
            }).unwrap(),
            _ => panic!("Expected Module"),
        };
        
        let context = RuleContext {
            stmt: func_stmt,
            file_path: "test.py",
            source: code,
            ast: &ast,
        };
        
        let violations = rule.check(&context);
        
        assert_eq!(violations.len(), 0);
    }
    
    #[test]
    fn test_injected_mixed_defaults() {
        let code = r#"
@injected
def process_data(logger, database=None, config=None):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let rule = NoDefaultDependenciesInInjectedRule::new();
        
        let func_stmt = match &ast {
            rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
                matches!(stmt, rustpython_ast::Stmt::FunctionDef(_))
            }).unwrap(),
            _ => panic!("Expected Module"),
        };
        
        let context = RuleContext {
            stmt: func_stmt,
            file_path: "test.py",
            source: code,
            ast: &ast,
        };
        
        let violations = rule.check(&context);
        
        // Should have 2 violations for database and config having defaults
        assert_eq!(violations.len(), 2);
        assert!(violations.iter().any(|v| v.message.contains("database")));
        assert!(violations.iter().any(|v| v.message.contains("config")));
    }
}