use pinjected_linter::rules::base::LintRule;
use pinjected_linter::rules::pinj064_no_optional_dependencies::NoOptionalDependenciesRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};

fn run_violations(code: &str) -> Vec<pinjected_linter::models::Violation> {
    let ast = parse(code, Mode::Module, "<test>").unwrap();
    let rule = NoOptionalDependenciesRule::new();
    let mut violations = Vec::new();

    if let rustpython_ast::Mod::Module(module) = &ast {
        for stmt in &module.body {
            let context = RuleContext {
                stmt,
                file_path: "test.py",
                source: code,
                ast: &ast,
            };
            let mut v = rule.check(&context);
            violations.append(&mut v);
        }
    }
    violations
}

#[test]
fn injected_dep_optional_flagged() {
    let code = r#"
from typing import Optional
from pinjected import injected
@injected
def f(x: Optional[int], /):
    pass
"#;
    let v = run_violations(code);
    assert_eq!(v.len(), 1);
    assert!(v[0].rule_id == "PINJ064");
}

#[test]
fn instance_dep_union_none_flagged() {
    let code = r#"
from typing import Union
from pinjected import instance
@instance
def g(x: Union[str, None], /):
    pass
"#;
    let v = run_violations(code);
    assert_eq!(v.len(), 1);
    assert!(v[0].rule_id == "PINJ064");
}

#[test]
fn async_injected_optional_flagged() {
    let code = r#"
from typing import Optional
from pinjected import injected
@injected
async def h(x: Optional[str], /):
    pass
"#;
    let v = run_violations(code);
    assert_eq!(v.len(), 1);
}

#[test]
fn no_slash_all_params_are_deps() {
    let code = r#"
from typing import Optional
from pinjected import injected
@injected
def k(x: Optional[int]):
    pass
"#;
    let v = run_violations(code);
    assert_eq!(v.len(), 1);
}

#[test]
fn non_dependency_after_slash_not_flagged() {
    let code = r#"
from typing import Optional
from pinjected import injected
@injected
def ok(x, /, y: Optional[int] = None):
    pass
"#;
    let v = run_violations(code);
    assert!(v.is_empty());
}

#[test]
fn string_annotation_optional_flagged() {
    let code = r#"
from pinjected import instance
@instance
def s(x: "Optional[int]", /):
    pass
"#;
    let v = run_violations(code);
    assert_eq!(v.len(), 1);
}

#[test]
fn good_non_optional_dep_ok() {
    let code = r#"
from pinjected import injected
@injected
def good(x: int, /):
    pass
"#;
    let v = run_violations(code);
    assert!(v.is_empty());
}
