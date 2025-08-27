use pinjected_linter::rules::pinj014::MissingStubFileRule;
use pinjected_linter::rules::base::LintRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};
use rustpython_parser::text_size::TextRange;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_pinj014_autofix_creates_stub_file() {
    let python_code = r#"
from pinjected import injected, IProxy
from typing import List

@injected
def get_user(db: IProxy[Database], /, user_id: str) -> User:
    return db.get_user(user_id)

@injected
async def a_list_users(db: IProxy[Database], /, filter: dict | None = None) -> List[User]:
    return await db.list_users(filter)
"#;

    // Create a temp directory for testing
    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("test_module.py");
    let stub_file = temp_dir.path().join("test_module.pyi");
    
    // Write the Python file
    fs::write(&python_file, python_code).unwrap();
    
    let test_file_path = "/home/test_module.py";

    // Parse the code
    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();
    
    // Create context
    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: test_file_path,
        source: python_code,
        ast: &ast,
    };

    // Run the rule
    let rule = MissingStubFileRule::new();
    let violations = rule.check(&context);

    // Should have one violation
    assert_eq!(violations.len(), 1);
    
    // Should have a fix
    let violation = &violations[0];
    assert!(violation.fix.is_some());
    
    let fix = violation.fix.as_ref().unwrap();
    
    // The fix should be for the stub file
    let expected_stub_path = std::path::Path::new(test_file_path).with_extension("pyi");
    assert_eq!(fix.file_path, expected_stub_path);
    
    // Check the fix content
    println!("Fix content:\n{}", fix.content);
    assert!(fix.content.contains("from typing import overload"));
    assert!(fix.content.contains("from pinjected import IProxy"));
    assert!(fix.content.contains("@overload"));
    assert!(fix.content.contains("def get_user(user_id: str) -> IProxy[User]: ..."));
    assert!(fix.content.contains("async def a_list_users(filter: dict | None = ...) -> IProxy[List[User]]: ..."));
}

#[test]
fn test_pinj014_autofix_updates_incorrect_stub() {
    let python_code = r#"
from pinjected import injected, IProxy

@injected
def process_data(logger: IProxy[Logger], /, data: str) -> Result:
    return Result(data)
"#;

    let incorrect_stub = r#"
from typing import overload

# Incorrect - shows injected dependencies and wrong return type
@overload
def process_data(logger: IProxy[Logger], data: str) -> Result: ...
"#;

    // Create a temp directory for testing
    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("processor.py");
    let stub_file = temp_dir.path().join("processor.pyi");
    
    // Write files
    fs::write(&python_file, python_code).unwrap();
    
    let test_file_path = python_file.to_str().unwrap();
    
    // Write the stub file to the temp directory for the rule to find
    fs::write(&stub_file, incorrect_stub).unwrap();

    // Parse the code
    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();
    
    // Create context
    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: test_file_path,
        source: python_code,
        ast: &ast,
    };

    // Run the rule
    let rule = MissingStubFileRule::new();
    let violations = rule.check(&context);

    // Should have one violation
    assert_eq!(violations.len(), 1);
    
    // Should have a fix
    let violation = &violations[0];
    assert!(violation.fix.is_some());
    
    let fix = violation.fix.as_ref().unwrap();
    
    // The fix should update the existing stub file  
    assert_eq!(fix.file_path, stub_file);
    assert_eq!(fix.description, "Update stub file with correct signatures while preserving existing content");
    
    // Check the fix content has correct signature
    assert!(fix.content.contains("def process_data(data: str) -> IProxy[Result]: ..."));
    assert!(!fix.content.contains("logger: IProxy[Logger]"));
}
