use std::fs;

use pinjected_linter::{lint_path, LinterOptions};

fn write_file(dir: &std::path::Path, rel: &str, content: &str) {
    let p = dir.join(rel);
    if let Some(parent) = p.parent() {
        fs::create_dir_all(parent).unwrap();
    }
    fs::write(p, content).unwrap();
}

#[test]
fn test_duplicate_names_across_files_flagged() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();

    write_file(
        root,
        "a.py",
        r#"
from pinjected import injected

@injected
def store_data():
    return 1
"#,
    );

    write_file(
        root,
        "b.py",
        r#"
from pinjected import instance, injected

@instance
def store_data():
    return 2
"#,
    );

    let result = lint_path(root, LinterOptions::default()).unwrap();

    let mut found = false;
    for (_path, violations) in result.violations {
        for v in violations {
            if v.rule_id == "PINJ062" {
                found = true;
            }
        }
    }

    assert!(found, "Expected PINJ062 violation for duplicate provider names");
}

#[test]
fn test_unique_names_ok_including_async_with_a_prefix() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();

    write_file(
        root,
        "a.py",
        r#"
from pinjected import injected

@injected
def store_data_y():
    return 1
"#,
    );

    write_file(
        root,
        "b.py",
        r#"
from pinjected import instance

@instance
def store_data_y__influxdb():
    return 2
"#,
    );

    write_file(
        root,
        "c.py",
        r#"
from pinjected import injected

@injected
async def a_store_data_y__influxdb():
    return 3
"#,
    );

    let result = lint_path(root, LinterOptions::default()).unwrap();

    for (_path, violations) in result.violations {
        for v in violations {
            assert_ne!(v.rule_id, "PINJ062", "Did not expect PINJ062 for unique names");
        }
    }
}
