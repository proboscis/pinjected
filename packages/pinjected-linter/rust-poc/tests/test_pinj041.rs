use pinjected_linter::rules::pinj041_no_underscore_defaults_in_injected_dataclass::NoUnderscoreDefaultsInInjectedDataclassRule;
use pinjected_linter::rules::base::LintRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};

#[test]
fn test_pinj041_detects_default_values() {
    let python_code = r#"
from dataclasses import dataclass
from pinjected import injected

@injected
@dataclass
class ServiceWithDefaults:
    _logger: object = None
    _cache: object = "default"
    name: str = "ok"
"#;

    let ast = parse(python_code, Mode::Module, "test.py").unwrap();
    
    // Find the class definition
    let class_stmt = match &ast {
        rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
            matches!(stmt, rustpython_ast::Stmt::ClassDef(_))
        }).unwrap(),
        _ => panic!("Expected Module"),
    };
    
    let context = RuleContext {
        stmt: class_stmt,
        file_path: "test.py",
        source: python_code,
        ast: &ast,
    };

    let rule = NoUnderscoreDefaultsInInjectedDataclassRule::new();
    let violations = rule.check(&context);

    // Should have 2 violations for _logger and _cache
    assert_eq!(violations.len(), 2);
    
    // Check violation messages contain helpful information
    for violation in &violations {
        assert!(violation.message.contains("has a default value"));
        assert!(violation.message.contains("Use design() to configure"));
    }
}

#[test]
fn test_pinj041_detects_optional_types() {
    let python_code = r#"
from dataclasses import dataclass
from typing import Optional, Union
from pinjected import injected

@injected
@dataclass
class ServiceWithOptional:
    _logger: Optional[object]
    _cache: object | None
    _database: Union[object, None]
    name: Optional[str]
"#;

    let ast = parse(python_code, Mode::Module, "test.py").unwrap();
    
    let class_stmt = match &ast {
        rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
            matches!(stmt, rustpython_ast::Stmt::ClassDef(_))
        }).unwrap(),
        _ => panic!("Expected Module"),
    };
    
    let context = RuleContext {
        stmt: class_stmt,
        file_path: "test.py",
        source: python_code,
        ast: &ast,
    };

    let rule = NoUnderscoreDefaultsInInjectedDataclassRule::new();
    let violations = rule.check(&context);

    // Should have 3 violations for underscore-prefixed attributes
    assert_eq!(violations.len(), 3);
    
    for violation in &violations {
        assert!(violation.message.contains("is typed as Optional"));
        assert!(violation.message.contains("Use design() to configure"));
    }
}

#[test]
fn test_pinj041_ignores_non_injected_dataclass() {
    let python_code = r#"
from dataclasses import dataclass

@dataclass
class RegularDataclass:
    _private: object = None
    _optional: Optional[object]
"#;

    let ast = parse(python_code, Mode::Module, "test.py").unwrap();
    
    let class_stmt = match &ast {
        rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
            matches!(stmt, rustpython_ast::Stmt::ClassDef(_))
        }).unwrap(),
        _ => panic!("Expected Module"),
    };
    
    let context = RuleContext {
        stmt: class_stmt,
        file_path: "test.py",
        source: python_code,
        ast: &ast,
    };

    let rule = NoUnderscoreDefaultsInInjectedDataclassRule::new();
    let violations = rule.check(&context);

    // Should have no violations
    assert_eq!(violations.len(), 0);
}

#[test]
fn test_pinj041_handles_both_default_and_optional() {
    let python_code = r#"
from dataclasses import dataclass
from typing import Optional
from pinjected import injected

@injected
@dataclass
class ServiceWithBoth:
    _logger: Optional[object] = None
"#;

    let ast = parse(python_code, Mode::Module, "test.py").unwrap();
    
    let class_stmt = match &ast {
        rustpython_ast::Mod::Module(module) => module.body.iter().find(|stmt| {
            matches!(stmt, rustpython_ast::Stmt::ClassDef(_))
        }).unwrap(),
        _ => panic!("Expected Module"),
    };
    
    let context = RuleContext {
        stmt: class_stmt,
        file_path: "test.py",
        source: python_code,
        ast: &ast,
    };

    let rule = NoUnderscoreDefaultsInInjectedDataclassRule::new();
    let violations = rule.check(&context);

    // Should have 1 violation mentioning both issues
    assert_eq!(violations.len(), 1);
    assert!(violations[0].message.contains("has a default value and is typed as Optional"));
}