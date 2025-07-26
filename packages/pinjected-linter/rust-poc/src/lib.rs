#![warn(clippy::all)]
#![warn(clippy::pedantic)]
#![warn(clippy::cognitive_complexity)]
#![warn(clippy::too_many_lines)]
#![warn(clippy::too_many_arguments)]
// Allow some common patterns that are fine in this codebase
#![allow(clippy::module_name_repetitions)]
#![allow(clippy::must_use_candidate)]

pub mod config;
pub mod location;
pub mod models;
pub mod noqa;
pub mod rule_docs;
pub mod rules;
pub mod utils;

use anyhow::Result;
use rayon::prelude::*;
use rustpython_ast::{text_size::TextRange, Mod};
use rustpython_parser::{parse, Mode};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use crate::location::LineIndex;
use models::{RuleContext, Violation};

/// Options for the linter
#[derive(Clone)]
pub struct LinterOptions {
    pub threads: usize,
    pub rule: Option<String>,
    pub skip_patterns: Vec<String>,
    pub cache: bool,
}

impl Default for LinterOptions {
    fn default() -> Self {
        Self {
            threads: 0,
            rule: None,
            skip_patterns: vec![],
            cache: true,
        }
    }
}

/// Result of linting
pub struct LintResult {
    pub violations: Vec<(PathBuf, Vec<Violation>)>,
    pub files_analyzed: usize,
    pub cached_asts: usize,
    pub files_with_errors: usize,
    pub parse_errors: usize,
}

/// Cache for parsed ASTs to avoid re-parsing
type AstCache = Arc<Mutex<HashMap<PathBuf, Arc<Mod>>>>;

/// Early exit check - some files don't need full analysis
fn should_analyze_file(path: &Path) -> bool {
    // Skip common non-source files
    if let Some(name) = path.file_name() {
        let name_str = name.to_str().unwrap_or("");
        // Don't skip test_ files - we want to analyze them!
        if name_str.starts_with("_") || name_str == "__pycache__" {
            return false;
        }
    }

    // Skip generated files
    if let Some(parent) = path.parent() {
        if parent.ends_with("__pycache__") || parent.ends_with(".git") {
            return false;
        }
    }

    true
}

/// Analyze a single file with caching support
fn analyze_file(
    path: &Path,
    rules: &[Box<dyn rules::base::LintRule>],
    cache: Option<&AstCache>,
) -> Result<Vec<Violation>> {
    // Early exit for files we shouldn't analyze
    if !should_analyze_file(path) {
        return Ok(Vec::new());
    }

    let content = fs::read_to_string(path)?;

    // Quick check: if file doesn't contain "injected" or "instance", skip most rules
    let has_pinjected = content.contains("@injected")
        || content.contains("@instance")
        || content.contains("from pinjected")
        || content.contains("pinjected")
        || content.contains("Injected");

    // Get or parse AST
    let ast = if let Some(cache) = cache {
        let mut cache_guard = cache.lock().unwrap();

        if let Some(cached_ast) = cache_guard.get(path) {
            cached_ast.clone()
        } else {
            let ast = Arc::new(parse(&content, Mode::Module, path.to_str().unwrap())?);
            cache_guard.insert(path.to_path_buf(), ast.clone());
            ast
        }
    } else {
        Arc::new(parse(&content, Mode::Module, path.to_str().unwrap())?)
    };

    let mut violations = Vec::new();

    // Filter rules based on file content
    let active_rules: Vec<_> = if !has_pinjected {
        // Only run rules that don't require decorators
        rules
            .iter()
            .filter(|r| matches!(r.rule_id(), "PINJ013" | "PINJ036")) // Builtin shadowing and pyi enforcement
            .collect()
    } else {
        rules.iter().collect()
    };
    

    if active_rules.is_empty() {
        return Ok(violations);
    }

    // Create a single context for module-level rules
    let module_context = RuleContext {
        stmt: &rustpython_ast::Stmt::Pass(rustpython_ast::StmtPass {
            range: TextRange::default(),
        }),
        file_path: path.to_str().unwrap(),
        source: &content,
        ast: &ast,
    };

    // First pass: module-level rules (PINJ012, PINJ014, PINJ036)
    for rule in &active_rules {
        if matches!(rule.rule_id(), "PINJ012" | "PINJ014" | "PINJ036") {
            violations.extend(rule.check(&module_context));
        }
    }

    // Second pass: statement-level rules
    match &*ast {
        Mod::Module(module) => {
            // Group rules by type for better cache locality
            let mut stmt_rules: Vec<&Box<dyn rules::base::LintRule>> = Vec::new();
            let mut func_rules: Vec<&Box<dyn rules::base::LintRule>> = Vec::new();
            let mut class_rules: Vec<&Box<dyn rules::base::LintRule>> = Vec::new();

            for rule in &active_rules {
                match rule.rule_id() {
                    "PINJ001" | "PINJ002" | "PINJ003" | "PINJ004" => func_rules.push(rule),
                    "PINJ005" | "PINJ006" | "PINJ007" | "PINJ009" | "PINJ015" | "PINJ016"
                    | "PINJ017" | "PINJ026" | "PINJ027" | "PINJ028" | "PINJ031" | "PINJ032"
                    | "PINJ033" | "PINJ040" => func_rules.push(rule),
                    "PINJ010" | "PINJ011" => stmt_rules.push(rule),
                    "PINJ013" | "PINJ018" | "PINJ029" | "PINJ034" | "PINJ035" | "PINJ042" => {
                        stmt_rules.push(rule)
                    }
                    _ => {} // Already handled
                }

                // Also add rules that need to check inside classes
                if matches!(rule.rule_id(), "PINJ033" | "PINJ041") {
                    class_rules.push(rule);
                }
            }

            for stmt in &module.body {
                let context = RuleContext {
                    stmt,
                    file_path: path.to_str().unwrap(),
                    source: &content,
                    ast: &ast,
                };

                // Apply rules based on statement type
                match stmt {
                    rustpython_ast::Stmt::FunctionDef(_)
                    | rustpython_ast::Stmt::AsyncFunctionDef(_) => {
                        for rule in &func_rules {
                            violations.extend(rule.check(&context));
                        }
                    }
                    rustpython_ast::Stmt::ClassDef(_) => {
                        for rule in &class_rules {
                            violations.extend(rule.check(&context));
                        }
                    }
                    _ => {
                        for rule in &stmt_rules {
                            violations.extend(rule.check(&context));
                        }
                    }
                }

                // Apply rules that need to see all statements
                for rule in &active_rules {
                    if matches!(rule.rule_id(), "PINJ019" | "PINJ042") {
                        violations.extend(rule.check(&context));
                    }
                }
            }
        }
        _ => {}
    }

    // Filter out violations suppressed by noqa comments
    let noqa_directives = noqa::parse_noqa_directives(&content);
    if !noqa_directives.is_empty() {
        let line_index = LineIndex::new(content.clone());
        violations.retain(|violation| {
            let (line, _) = line_index.get_location(violation.offset);
            !noqa::is_violation_suppressed(line, &violation.rule_id, &noqa_directives)
        });
    }

    Ok(violations)
}

/// Find all Python files in a directory
pub fn find_python_files(path: &Path, skip_patterns: &[String]) -> Vec<PathBuf> {
    use walkdir::{DirEntry, WalkDir};

    let mut files = Vec::new();

    // Create a filter function to skip directories
    let is_excluded = |entry: &DirEntry| -> bool {
        let path_str = entry.path().to_str().unwrap_or("");

        // Check each component of the path
        for component in entry.path().components() {
            if let Some(name) = component.as_os_str().to_str() {
                if skip_patterns
                    .iter()
                    .any(|pattern| name == pattern || path_str.contains(pattern))
                {
                    return true;
                }
            }
        }
        false
    };

    let walker = WalkDir::new(path)
        .follow_links(false)
        .into_iter()
        .filter_entry(|e| !is_excluded(e));

    for entry in walker.filter_map(|e| e.ok()) {
        let path = entry.path();

        // Check if Python file
        if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("py") {
            files.push(path.to_path_buf());
        }
    }

    files
}

/// Main linting function
pub fn lint_path(path: &Path, options: LinterOptions) -> Result<LintResult> {
    // Set thread pool size
    if options.threads > 0 {
        rayon::ThreadPoolBuilder::new()
            .num_threads(options.threads)
            .build_global()?;
    }

    // Get list of files to analyze
    let files = if path.is_file() {
        vec![path.to_path_buf()]
    } else {
        find_python_files(path, &options.skip_patterns)
    };

    let files_analyzed = files.len();

    // Load rules once
    let all_rules = rules::get_all_rules();
    let rules: Vec<_> = if let Some(rule_filter) = &options.rule {
        // Parse comma-separated rule IDs
        let rule_ids: Vec<&str> = rule_filter.split(',').map(|s| s.trim()).collect();
        all_rules
            .into_iter()
            .filter(|r| rule_ids.contains(&r.rule_id()))
            .collect()
    } else {
        all_rules
    };
    

    // Create cache if requested
    let cache = if options.cache {
        Some(Arc::new(Mutex::new(HashMap::new())))
    } else {
        None
    };

    // Process files in parallel, tracking errors
    let mut files_with_errors = 0;
    let mut parse_errors = 0;

    let results: Vec<_> = files
        .par_iter()
        .map(|file| match analyze_file(file, &rules, cache.as_ref()) {
            Ok(violations) => (file.clone(), Ok(violations)),
            Err(e) => {
                eprintln!("Error analyzing {}: {}", file.display(), e);
                (file.clone(), Err(e))
            }
        })
        .collect();

    let mut violations = Vec::new();
    for (file, result) in results {
        match result {
            Ok(file_violations) => {
                if !file_violations.is_empty() {
                    violations.push((file, file_violations));
                }
            }
            Err(e) => {
                files_with_errors += 1;
                // Check if it's a parse error
                if e.to_string().contains("invalid syntax")
                    || e.to_string().contains("unexpected token")
                {
                    parse_errors += 1;
                }
            }
        }
    }

    let cached_asts = if let Some(cache) = cache {
        cache.lock().unwrap().len()
    } else {
        0
    };

    Ok(LintResult {
        violations,
        files_analyzed,
        cached_asts,
        files_with_errors,
        parse_errors,
    })
}
