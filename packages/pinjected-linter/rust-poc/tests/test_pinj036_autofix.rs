use pinjected_linter::rules::base::LintRule;
use pinjected_linter::rules::pinj036_enforce_pyi_stubs::EnforcePyiStubsRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};
use rustpython_parser::text_size::TextRange;
use tempfile::TempDir;
use std::fs;

#[test]
fn test_pinj036_autofix_creates_stub_file() {
    let python_code = r#"
from pinjected import injected, IProxy
from typing import List

@injected
def get_user(db: IProxy[Database], /, user_id: str) -> User:
    return db.get_user(user_id)

@injected
async def a_list_users(db: IProxy[Database], /, filter: dict | None = None) -> List[User]:
    return await db.list_users(filter)

class Repo:
    def foo(self, x: int) -> str:
        return str(x)
"#;

    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("accounts.py");
    let stub_file = temp_dir.path().join("accounts.pyi");

    fs::write(&python_file, python_code).unwrap();

    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();

    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: python_file.to_str().unwrap(),
        source: python_code,
        ast: &ast,
    };

    let rule = EnforcePyiStubsRule::new();
    let violations = rule.check(&context);

    assert_eq!(violations.len(), 1);

    let violation = &violations[0];
    assert_eq!(violation.rule_id, "PINJ036");
    assert!(violation.fix.is_some());

    let fix = violation.fix.as_ref().unwrap();
    assert_eq!(fix.file_path, stub_file);

    let content = &fix.content;
    assert!(content.contains("from typing import overload"));
    assert!(content.contains("from pinjected import IProxy"));
    assert!(content.contains("@overload"));
    assert!(content.contains("def get_user(user_id: str) -> IProxy[User]: ..."));
    assert!(content.contains("async def a_list_users(filter: dict | None = ...) -> IProxy[List[User]]: ..."));
    assert!(content.contains("class Repo:"));
}

#[test]
fn test_pinj036_autofix_updates_incomplete_stub() {
    let python_code = r#"
from pinjected import injected, IProxy

@injected
def process_data(logger: IProxy[Logger], /, data: str) -> Result:
    return Result(data)

def helper(x: int) -> int:
    return x + 1
"#;

    let existing_stub = r#"
from typing import overload

# Existing but incomplete; missing helper and wrong injected signature form
@overload
def process_data(data: str) -> IProxy[Result]: ...
"#;

    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("processor.py");
    let stub_file = temp_dir.path().join("processor.pyi");

    fs::write(&python_file, python_code).unwrap();
    fs::write(&stub_file, existing_stub).unwrap();

    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();

    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: python_file.to_str().unwrap(),
        source: python_code,
        ast: &ast,
    };

    let rule = EnforcePyiStubsRule::new();
    let violations = rule.check(&context);

    assert_eq!(violations.len(), 1);

    let violation = &violations[0];
    assert_eq!(violation.rule_id, "PINJ036");
    assert!(violation.fix.is_some());

    let fix = violation.fix.as_ref().unwrap();
    assert_eq!(fix.file_path, stub_file);
    assert_eq!(fix.description, "Update stub file with missing symbols while preserving existing content");

    let content = &fix.content;
    assert!(content.contains("from typing import overload"));
    assert!(content.contains("from pinjected import IProxy"));
    assert!(content.contains("@overload"));
    assert!(content.contains("def process_data(data: str) -> IProxy[Result]: ..."));
    assert!(content.contains("def helper(x: int) -> int: ..."));
}
