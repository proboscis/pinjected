use pinjected_linter::{lint_path, LinterOptions};
use std::fs;
use tempfile::TempDir;

#[test]
fn test_noqa_suppresses_all_violations() {
    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join("test.py");
    
    let content = r#"
from pinjected import instance

@instance
def get_data():  # noqa
    pass
"#;
    fs::write(&file_path, content).unwrap();
    
    let options = LinterOptions {
        rule: Some("PINJ001".to_string()),
        ..Default::default()
    };
    
    let result = lint_path(&file_path, options).unwrap();
    assert_eq!(result.violations.len(), 0, "Generic noqa should suppress all violations");
}

#[test]
fn test_noqa_suppresses_specific_rule() {
    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join("test.py");
    
    let content = r#"
from pinjected import instance

@instance
def get_data():  # noqa: PINJ001
    return None
"#;
    fs::write(&file_path, content).unwrap();
    
    let options = LinterOptions::default();
    
    let result = lint_path(&file_path, options).unwrap();
    
    // Should not have PINJ001 violations
    let has_pinj001 = result.violations.iter()
        .any(|(_, violations)| violations.iter().any(|v| v.rule_id == "PINJ001"));
    assert!(!has_pinj001, "PINJ001 should be suppressed by noqa");
    
    // But might have other violations like PINJ002
    // (depending on if default return is considered a violation)
}

#[test]
fn test_noqa_multiple_rules() {
    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join("test.py");
    
    let content = r#"
from pinjected import injected

@injected
def worker(logger,/, data):  # noqa: PINJ005, PINJ015
    pass

@injected
async def runner(db,/, task):  # noqa: PINJ006
    pass
"#;
    fs::write(&file_path, content).unwrap();
    
    let options = LinterOptions::default();
    
    let result = lint_path(&file_path, options).unwrap();
    
    // Check specific violations are suppressed
    for (_, violations) in &result.violations {
        for violation in violations {
            // PINJ005 should be suppressed on "worker" function
            if violation.rule_id == "PINJ005" && violation.message.contains("worker") {
                panic!("PINJ005 should be suppressed for 'worker' function but was reported");
            }
            // PINJ006 should be suppressed on "runner" function  
            if violation.rule_id == "PINJ006" && violation.message.contains("runner") {
                panic!("PINJ006 should be suppressed for 'runner' function but was reported");
            }
        }
    }
}

#[test]
fn test_noqa_does_not_suppress_other_lines() {
    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join("test.py");
    
    let content = r#"
from pinjected import instance

@instance
def get_data():  # noqa: PINJ001
    pass

@instance
def fetch_info():  # This should still be reported
    pass
"#;
    fs::write(&file_path, content).unwrap();
    
    let options = LinterOptions {
        rule: Some("PINJ001".to_string()),
        ..Default::default()
    };
    
    let result = lint_path(&file_path, options).unwrap();
    
    // Should have exactly one PINJ001 violation (for fetch_info)
    let violation_count = result.violations.iter()
        .map(|(_, violations)| violations.len())
        .sum::<usize>();
    assert_eq!(violation_count, 1, "Should have one PINJ001 violation for fetch_info");
}

#[test]
fn test_noqa_case_insensitive() {
    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join("test.py");
    
    let content = r#"
def list():  # NOQA: PINJ013
    pass

def dict():  # NoQa
    pass
"#;
    fs::write(&file_path, content).unwrap();
    
    let options = LinterOptions {
        rule: Some("PINJ013".to_string()),
        ..Default::default()
    };
    
    let result = lint_path(&file_path, options).unwrap();
    assert_eq!(result.violations.len(), 0, "Case-insensitive noqa should work");
}

#[test]
fn test_noqa_with_trailing_comment() {
    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join("test.py");
    
    let content = r#"
from pinjected import instance

@instance
def get_config():  # noqa: PINJ001 - this is intentionally a verb
    pass
"#;
    fs::write(&file_path, content).unwrap();
    
    let options = LinterOptions {
        rule: Some("PINJ001".to_string()),
        ..Default::default()
    };
    
    let result = lint_path(&file_path, options).unwrap();
    assert_eq!(result.violations.len(), 0, "Noqa with trailing comment should work");
}