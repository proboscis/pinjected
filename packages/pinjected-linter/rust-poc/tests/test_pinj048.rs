use pinjected_linter::rules::pinj048_no_default_dependencies_in_injected::NoDefaultDependenciesInInjectedRule;
use pinjected_linter::rules::base::LintRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};

#[test]
fn test_pinj048_detects_default_dependencies() {
    let python_code = r#"
from pinjected import injected

@injected
def process_data(logger=None, database=None):
    pass

@injected
def good_function(logger, database):
    pass
"#;

    let ast = parse(python_code, Mode::Module, "<test>").unwrap();
    let rule = NoDefaultDependenciesInInjectedRule::new();
    
    let mut total_violations = 0;
    
    // Check all function definitions
    match &ast {
        rustpython_ast::Mod::Module(module) => {
            for stmt in &module.body {
                let context = RuleContext {
                    stmt,
                    file_path: "test.py",
                    source: python_code,
                    ast: &ast,
                };
                let violations = rule.check(&context);
                total_violations += violations.len();
                
                // Check specific violations
                for violation in violations {
                    assert!(violation.message.contains("default value"));
                }
            }
        },
        _ => panic!("Expected Module"),
    }
    
    // Should detect 2 violations for process_data (logger=None and database=None)
    assert_eq!(total_violations, 2);
}

#[test]
fn test_pinj048_no_slash_with_defaults() {
    let python_code = r#"
from pinjected import injected

@injected
def get_config(config_service=None):
    pass
"#;

    let ast = parse(python_code, Mode::Module, "<test>").unwrap();
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
        source: python_code,
        ast: &ast,
    };
    
    let violations = rule.check(&context);
    
    // Should detect 1 violation for config_service=None
    assert_eq!(violations.len(), 1);
    assert!(violations[0].message.contains("config_service"));
}

#[test]
fn test_pinj048_ignores_runtime_defaults() {
    let python_code = r#"
from pinjected import injected

@injected
def search_products(database, logger, /, query: str, limit: int = 10):
    pass
"#;

    let ast = parse(python_code, Mode::Module, "<test>").unwrap();
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
        source: python_code,
        ast: &ast,
    };
    
    let violations = rule.check(&context);
    
    // Should detect no violations - defaults after slash are allowed
    assert_eq!(violations.len(), 0);
}

#[test]
fn test_pinj048_ignores_non_injected() {
    let python_code = r#"
def regular_function(param=None):
    pass

from pinjected import instance

@instance
def database_instance(host="localhost"):
    pass
"#;

    let ast = parse(python_code, Mode::Module, "<test>").unwrap();
    let rule = NoDefaultDependenciesInInjectedRule::new();
    
    let mut total_violations = 0;
    
    match &ast {
        rustpython_ast::Mod::Module(module) => {
            for stmt in &module.body {
                let context = RuleContext {
                    stmt,
                    file_path: "test.py",
                    source: python_code,
                    ast: &ast,
                };
                let violations = rule.check(&context);
                total_violations += violations.len();
            }
        },
        _ => panic!("Expected Module"),
    }
    
    // Should detect no violations - not @injected functions
    assert_eq!(total_violations, 0);
}

#[test]
fn test_pinj048_async_injected() {
    let python_code = r#"
from pinjected import injected

@injected
async def a_fetch_data(client=None, cache=None):
    pass
"#;

    let ast = parse(python_code, Mode::Module, "<test>").unwrap();
    let rule = NoDefaultDependenciesInInjectedRule::new();
    
    let func_stmt = match &ast {
        rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
            matches!(stmt, rustpython_ast::Stmt::FunctionDef(_) | rustpython_ast::Stmt::AsyncFunctionDef(_))
        }).unwrap(),
        _ => panic!("Expected Module"),
    };
    
    let context = RuleContext {
        stmt: func_stmt,
        file_path: "test.py",
        source: python_code,
        ast: &ast,
    };
    
    let violations = rule.check(&context);
    
    // Should detect 2 violations for async function
    assert_eq!(violations.len(), 2);
    assert!(violations[0].message.contains("client"));
    assert!(violations[1].message.contains("cache"));
}

#[test]
fn test_pinj048_pinjected_dot_injected() {
    let python_code = r#"
import pinjected

@pinjected.injected
def process(logger=None):
    pass
"#;

    let ast = parse(python_code, Mode::Module, "<test>").unwrap();
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
        source: python_code,
        ast: &ast,
    };
    
    let violations = rule.check(&context);
    
    // Should detect 1 violation for pinjected.injected decorator
    assert_eq!(violations.len(), 1);
    assert!(violations[0].message.contains("logger"));
}

#[test]
fn test_pinj048_with_slash_no_defaults() {
    let python_code = r#"
from pinjected import injected

@injected
def process_order(logger, database, /, order_id: str):
    pass
"#;

    let ast = parse(python_code, Mode::Module, "<test>").unwrap();
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
        source: python_code,
        ast: &ast,
    };
    
    let violations = rule.check(&context);
    
    // Should detect no violations - no defaults in dependencies
    assert_eq!(violations.len(), 0);
}