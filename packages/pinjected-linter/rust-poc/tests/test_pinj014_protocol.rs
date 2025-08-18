use pinjected_linter::rules::pinj014::MissingStubFileRule;
use pinjected_linter::rules::base::LintRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};
use rustpython_parser::text_size::TextRange;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_pinj014_recognizes_injected_with_protocol() {
    let python_code = r#"
from pinjected import injected, IProxy
from typing import Protocol

class UserFetcherProtocol(Protocol):
    def __call__(self, user_id: str) -> 'User': ...

class AsyncUserCreatorProtocol(Protocol):
    async def __call__(self, user_data: dict) -> 'User': ...

@injected(protocol=UserFetcherProtocol)
def get_user(db: 'Database', cache: 'Cache', /, user_id: str) -> 'User':
    return db.get_user(user_id)

@injected(protocol=AsyncUserCreatorProtocol)
async def a_create_user(db: 'Database', validator: 'Validator', /, user_data: dict) -> 'User':
    if not validator.validate(user_data):
        raise ValueError("Invalid user data")
    return await db.create_user(user_data)
"#;

    // Create a temp directory for testing
    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("test_module.py");
    
    // Write the Python file
    fs::write(&python_file, python_code).unwrap();

    // Parse the code
    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();
    
    // Create context
    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: python_file.to_str().unwrap(),
        source: python_code,
        ast: &ast,
    };

    // Run the rule
    let rule = MissingStubFileRule::new();
    let violations = rule.check(&context);

    // Should have one violation for missing stub file
    assert_eq!(violations.len(), 1);
    assert!(violations[0].message.contains("2 @injected functions"));
    
    // Should have a fix with the correct signatures
    let violation = &violations[0];
    assert!(violation.fix.is_some());
    
    let fix = violation.fix.as_ref().unwrap();
    
    // Check the fix content
    println!("Fix content:\n{}", fix.content);
    assert!(fix.content.contains("from typing import overload"));
    assert!(fix.content.contains("from pinjected import IProxy"));
    assert!(fix.content.contains("@overload"));
    assert!(fix.content.contains("def get_user(user_id: str) -> IProxy['User']: ..."));
    assert!(fix.content.contains("async def a_create_user(user_data: dict) -> IProxy['User']: ..."));
}

#[test]
fn test_pinj014_validates_stub_with_protocol_functions() {
    let python_code = r#"
from pinjected import injected, IProxy
from typing import Protocol

class WriteProtocol(Protocol):
    def __call__(self, db: str, records: list) -> None: ...

class AsyncReadProtocol(Protocol):
    async def __call__(self, bucket: str, query: str) -> list: ...

@injected(protocol=WriteProtocol)
def influxdb_write(client: 'InfluxDBClient', logger: 'Logger', /, db: str, records: list) -> None:
    logger.info(f"Writing {len(records)} records to {db}")
    client.write_points(database=db, points=records)

@injected(protocol=AsyncReadProtocol)
async def a_influxdb_read(client: 'InfluxDBClient', logger: 'Logger', /, bucket: str, query: str) -> list:
    return await client.query(bucket, query)
"#;

    let stub_code = r#"
from typing import overload
from pinjected import IProxy

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
def influxdb_write(db: str, records: list) -> IProxy[None]: ...

@overload
async def a_influxdb_read(bucket: str, query: str) -> IProxy[list]: ...
"#;

    // Create a temp directory for testing
    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("influx_test.py");
    let stub_file = temp_dir.path().join("influx_test.pyi");
    
    // Write files
    fs::write(&python_file, python_code).unwrap();
    fs::write(&stub_file, stub_code).unwrap();

    // Parse the code
    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();
    
    // Create context
    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: python_file.to_str().unwrap(),
        source: python_code,
        ast: &ast,
    };

    // Run the rule
    let rule = MissingStubFileRule::new();
    let violations = rule.check(&context);

    // Should have no violations - stub file is correct
    assert_eq!(violations.len(), 0, "Expected no violations but got: {:?}", violations);
}

#[test]
fn test_pinj014_detects_extra_functions_in_stub() {
    let python_code = r#"
from pinjected import injected, IProxy
from typing import Protocol

class ReadProtocol(Protocol):
    def __call__(self, key: str) -> str: ...

@injected(protocol=ReadProtocol)
def read_value(cache: 'Cache', /, key: str) -> str:
    return cache.get(key)
"#;

    let stub_code = r#"
from typing import overload
from pinjected import IProxy

@overload
def read_value(key: str) -> IProxy[str]: ...

# These functions don't exist in the .py file
@overload
def write_value(key: str, value: str) -> IProxy[None]: ...

@overload
async def a_delete_value(key: str) -> IProxy[bool]: ...
"#;

    // Create a temp directory for testing
    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("cache_ops.py");
    let stub_file = temp_dir.path().join("cache_ops.pyi");
    
    // Write files
    fs::write(&python_file, python_code).unwrap();
    fs::write(&stub_file, stub_code).unwrap();

    // Parse the code
    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();
    
    // Create context
    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: python_file.to_str().unwrap(),
        source: python_code,
        ast: &ast,
    };

    // Run the rule
    let rule = MissingStubFileRule::new();
    let violations = rule.check(&context);

    // Should have one violation
    assert_eq!(violations.len(), 1);
    
    let violation = &violations[0];
    
    // Check error messages for extra functions
    assert!(violation.message.contains("Function 'a_delete_value' exists in stub file but not in Python file"));
    assert!(violation.message.contains("Function 'write_value' exists in stub file but not in Python file"));
    assert!(violation.message.contains("Remove this function from the .pyi file or add the corresponding @injected function to the .py file"));
}

#[test]
fn test_pinj014_mixed_injected_styles() {
    let python_code = r#"
from pinjected import injected, IProxy
from typing import Protocol

# Simple @injected without protocol
@injected
def simple_func(dep: 'Dependency', /, arg: str) -> str:
    return dep.process(arg)

# @injected with protocol
class ProcessorProtocol(Protocol):
    def __call__(self, data: dict) -> dict: ...

@injected(protocol=ProcessorProtocol)
def process_data(processor: 'DataProcessor', /, data: dict) -> dict:
    return processor.process(data)

# Async with protocol
class AsyncFetcherProtocol(Protocol):
    async def __call__(self, id: int) -> str: ...

@injected(protocol=AsyncFetcherProtocol)
async def a_fetch_item(db: 'Database', /, id: int) -> str:
    return await db.fetch(id)
"#;

    // Create a temp directory for testing
    let temp_dir = TempDir::new().unwrap();
    let python_file = temp_dir.path().join("mixed_styles.py");
    
    // Write the Python file
    fs::write(&python_file, python_code).unwrap();

    // Parse the code
    let ast = parse(python_code, Mode::Module, python_file.to_str().unwrap()).unwrap();
    
    // Create context
    let context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() }),
        file_path: python_file.to_str().unwrap(),
        source: python_code,
        ast: &ast,
    };

    // Run the rule
    let rule = MissingStubFileRule::new();
    let violations = rule.check(&context);

    // Should have one violation for missing stub file
    assert_eq!(violations.len(), 1);
    assert!(violations[0].message.contains("3 @injected functions"));
    
    // Check the fix content includes all functions
    let fix = violations[0].fix.as_ref().unwrap();
    assert!(fix.content.contains("def simple_func(arg: str) -> IProxy[str]: ..."));
    assert!(fix.content.contains("def process_data(data: dict) -> IProxy[dict]: ..."));
    assert!(fix.content.contains("async def a_fetch_item(id: int) -> IProxy[str]: ..."));
}