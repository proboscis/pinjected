use rustpython_ast::{Mod, Stmt};

#[derive(Debug, Clone)]
pub struct Violation {
    pub rule_id: String,
    pub message: String,
    pub offset: usize,
    pub file_path: String,
    pub severity: Severity,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Severity {
    Error,
    Warning,
    Info,
}

/// Context passed to each rule for checking
pub struct RuleContext<'a> {
    pub stmt: &'a Stmt,
    pub file_path: &'a str,
    pub source: &'a str,
    pub ast: &'a Mod,
}
