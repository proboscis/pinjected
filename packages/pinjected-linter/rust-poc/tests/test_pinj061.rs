use pinjected_linter::rules::pinj061_enforce_module_design_in_pytests::EnforceModuleDesignInPytestsRule;
use pinjected_linter::rules::base::LintRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};
use rustpython_ast::text_size::TextRange;
use rustpython_ast::Stmt;

#[test]
fn test_pinj061_flags_missing_design_in_test_module() {
    let code = r#"
from pinjected.test import injected_pytest

@injected_pytest
def test_something(logger):
    assert logger is not None
"#;
    let ast = parse(code, Mode::Module, "test_example.py").unwrap();
    let rule = EnforceModuleDesignInPytestsRule::new();

    let dummy_stmt = Box::leak(Box::new(Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() })));
    let context = RuleContext {
        stmt: dummy_stmt,
        file_path: "test_example.py",
        source: code,
        ast: &ast,
    };
    let violations = rule.check(&context);

    assert_eq!(violations.len(), 1);
    assert_eq!(violations[0].rule_id, "PINJ061");
    assert!(violations[0].message.contains("__design__"));
}

#[test]
fn test_pinj061_ok_when_design_present() {
    let code = r#"
from pinjected import design
from pinjected.test import injected_pytest

__design__ = design()

@injected_pytest
def test_ok(dep):
    assert dep is not None
"#;
    let ast = parse(code, Mode::Module, "test_example.py").unwrap();
    let rule = EnforceModuleDesignInPytestsRule::new();

    let dummy_stmt = Box::leak(Box::new(Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() })));
    let context = RuleContext {
        stmt: dummy_stmt,
        file_path: "test_example.py",
        source: code,
        ast: &ast,
    };
    let violations = rule.check(&context);

    assert_eq!(violations.len(), 0);
}

#[test]
fn test_pinj061_ignored_for_non_test_module() {
    let code = r#"
from pinjected import design
__design__ = design()
"#;
    let ast = parse(code, Mode::Module, "helpers.py").unwrap();
    let rule = EnforceModuleDesignInPytestsRule::new();

    let dummy_stmt = Box::leak(Box::new(Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() })));
    let context = RuleContext {
        stmt: dummy_stmt,
        file_path: "helpers.py",
        source: code,
        ast: &ast,
    };
    let violations = rule.check(&context);

    assert_eq!(violations.len(), 0);
}
