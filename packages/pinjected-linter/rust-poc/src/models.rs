use rustpython_ast::{Mod, Stmt};
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct Violation {
    pub rule_id: String,
    pub message: String,
    pub offset: usize,
    pub file_path: String,
    pub severity: Severity,
    pub fix: Option<Fix>,
}

#[derive(Debug, Clone)]
pub struct Fix {
    pub description: String,
    pub file_path: PathBuf,
    pub content: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Severity {
    Error,
    Warning,
    Info,
}

impl Violation {
    /// Create a new violation without a fix
    pub fn new(rule_id: String, message: String, offset: usize, file_path: String, severity: Severity) -> Self {
        Self {
            rule_id,
            message,
            offset,
            file_path,
            severity,
            fix: None,
        }
    }

    /// Create a new violation with a fix
    pub fn with_fix(rule_id: String, message: String, offset: usize, file_path: String, severity: Severity, fix: Fix) -> Self {
        Self {
            rule_id,
            message,
            offset,
            file_path,
            severity,
            fix: Some(fix),
        }
    }
}

/// Context passed to each rule for checking
pub struct RuleContext<'a> {
    pub stmt: &'a Stmt,
    pub file_path: &'a str,
    pub source: &'a str,
    pub ast: &'a Mod,
}
