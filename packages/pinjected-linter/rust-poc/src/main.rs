use anyhow::Result;
use clap::{Parser, ValueEnum};
use std::fs;
use std::path::Path;
use std::process;
use std::time::Instant;

use pinjected_linter::config::{find_config_pyproject_toml, load_config, merge_config};
use pinjected_linter::location::LineIndex;
use pinjected_linter::{find_python_files, lint_path, LinterOptions};
use std::collections::HashMap;

mod rule_docs;

#[derive(ValueEnum, Clone, Debug)]
enum OutputFormat {
    Terminal,
    Json,
    Github,
}

#[derive(ValueEnum, Clone, Debug)]
enum SeverityLevel {
    Error,
    Warning,
    Info,
}

/// Exit codes used by the linter
mod exit_codes {
    pub const SUCCESS: i32 = 0; // No violations found
    pub const VIOLATIONS_FOUND: i32 = 1; // Violations found (errors or warnings based on --error-on-warning)
    pub const USAGE_ERROR: i32 = 2; // Invalid arguments or usage
    pub const FILE_ERROR: i32 = 3; // File not found or I/O error
    pub const PARSE_ERROR: i32 = 4; // Failed to parse Python files
    pub const CONFIG_ERROR: i32 = 5; // Configuration file error
}

#[derive(Parser, Debug)]
#[command(
    name = "pinjected-linter",
    author,
    version,
    about = "Pinjected linter - Check your code for Pinjected best practices",
    long_about = "Pinjected linter - Check your code for Pinjected best practices.\n\nIf no paths are provided, the current directory is checked recursively."
)]
struct Args {
    /// Paths to analyze (files or directories)
    ///
    /// Examples: pinjected-lint (current dir), pinjected-lint src/, pinjected-lint file.py
    #[arg(default_value = ".")]
    paths: Vec<String>,

    /// Path to configuration file (.pinjected-lint.toml)
    ///
    /// Example: pinjected-lint --config .pinjected-lint.toml
    #[arg(short = 'c', long = "config")]
    config: Option<String>,

    /// Output format
    ///
    /// Example: -f json (for CI/CD), -f github (for GitHub Actions)
    #[arg(
        short = 'f',
        long = "output-format",
        value_enum,
        default_value = "terminal"
    )]
    output_format: OutputFormat,

    /// Disable specific rules (can be used multiple times)
    ///
    /// Example: -d PINJ001 -d PINJ002
    #[arg(short = 'd', long = "disable")]
    disable: Vec<String>,

    /// Enable only specific rules (can be used multiple times)
    ///
    /// Example: -e PINJ001 -e PINJ002
    #[arg(short = 'e', long = "enable")]
    enable: Vec<String>,

    /// Disable parallel processing
    ///
    /// Example: pinjected-lint --no-parallel
    #[arg(long = "no-parallel")]
    no_parallel: bool,

    /// Show source code in violations
    ///
    /// Example: pinjected-lint --show-source
    #[arg(long = "show-source", default_value = "true")]
    show_source: bool,

    /// Disable source code in violations
    ///
    /// Example: pinjected-lint --no-show-source
    #[arg(long = "no-show-source", conflicts_with = "show_source")]
    no_show_source: bool,

    /// Enable colored output
    ///
    /// Example: pinjected-lint --color
    #[arg(long = "color", default_value = "true")]
    color: bool,

    /// Disable colored output
    ///
    /// Example: pinjected-lint --no-color
    #[arg(long = "no-color", conflicts_with = "color")]
    no_color: bool,

    /// Minimum severity level to report
    ///
    /// Example: -s error (only errors), -s warning (warnings+errors)
    #[arg(
        short = 's',
        long = "severity",
        value_enum,
        conflicts_with = "show_only"
    )]
    severity: Option<SeverityLevel>,

    /// Show only specific severity levels (comma-separated: error,warning,info)
    ///
    /// Example: --show-only error,warning
    #[arg(long = "show-only", value_delimiter = ',', conflicts_with = "severity")]
    show_only: Vec<String>,

    /// Enable verbose logging
    ///
    /// Example: pinjected-lint -v src/
    #[arg(short = 'v', long = "verbose")]
    verbose: bool,

    /// Show documentation for pyproject.toml configuration
    ///
    /// Example: pinjected-lint --show-config-docs
    #[arg(long = "show-config-docs")]
    show_config_docs: bool,

    /// Show detailed documentation for a specific rule
    ///
    /// Example: --show-rule-doc PINJ001
    #[arg(long = "show-rule-doc")]
    show_rule_doc: Option<String>,

    // Additional Rust-specific options for performance
    /// Number of threads to use (0 = auto)
    #[arg(short = 'j', long = "threads", default_value = "0", hide = true)]
    threads: usize,

    /// Skip files matching pattern
    #[arg(long = "skip", hide = true)]
    skip: Vec<String>,

    /// Show timing information
    #[arg(long = "timing", hide = true)]
    timing: bool,

    /// Cache parsed ASTs
    #[arg(long = "cache", hide = true)]
    cache: bool,

    /// Count files only (don't analyze)
    #[arg(long = "count", hide = true)]
    count: bool,

    /// Exit with non-zero code if warnings are found
    ///
    /// Example: pinjected-lint --error-on-warning
    #[arg(long = "error-on-warning")]
    error_on_warning: bool,
}

fn show_configuration_docs() {
    let docs = r#"
Pinjected Linter Configuration Documentation
============================================

The pinjected linter can be configured in your pyproject.toml file under the
[tool.pinjected-linter] section.

Example Configuration:
----------------------

[tool.pinjected-linter]
# Enable specific rules (if not specified, all rules are enabled)
enable = [
    "PINJ001",  # Instance naming convention
    "PINJ002",  # Instance defaults
    "PINJ003",  # Async instance naming
    # ... add more rules as needed
]

# Or disable specific rules
disable = ["PINJ001", "PINJ005"]

# Configure specific rules
[tool.pinjected-linter.rules.PINJ014]
min_injected_functions = 3
stub_search_paths = ["stubs", "typings", "types"]
ignore_patterns = ["**/tests/**", "**/test_*.py"]

# Exclude paths from linting
exclude = [".venv", "venv", ".git", "__pycache__", "build", "dist"]

# Additional configuration options
max_line_length = 120
check_docstrings = true

Available Rules:
----------------
- PINJ001: Instance naming convention (@instance functions should be nouns)
- PINJ002: Instance defaults (check default parameter usage)
- PINJ003: Async instance naming (a_ prefix for async @instance)
- PINJ004: Direct instance call (avoid calling @instance functions directly)
- PINJ005: Injected function naming (should be verbs/actions)
- PINJ006: Async injected naming (a_ prefix for async @injected)
- PINJ007: Slash separator position (proper / placement)
- PINJ009: No direct calls to @injected functions (build AST, don't execute)
- PINJ010: Design usage (proper design() function usage)
- PINJ011: IProxy annotations (not for injected dependencies)
- PINJ012: Dependency cycles detection
- PINJ013: Builtin shadowing (avoid shadowing builtins)
- PINJ014: Missing stub file (.pyi for @injected functions)
- PINJ015: Missing slash (require / in @injected functions)
- PINJ016: Missing protocol (require protocol parameter in @injected)
- PINJ017: Missing type annotations (require type annotations for dependencies)

Filtering Options:
------------------
--severity <level>    Minimum severity level to report (error, warning, info)
--show-only <levels>  Show only specific severity levels (comma-separated)
                      Examples:
                      --show-only error
                      --show-only warning
                      --show-only error,warning

Configuration Precedence:
-------------------------
1. Command line options (--enable, --disable) override all
2. Explicit config file specified with --config
3. pyproject.toml [tool.pinjected-linter] section
4. Default configuration (all rules enabled)

For more information, visit: https://github.com/pinjected/pinjected
"#;
    println!("{}", docs);
}

fn show_rule_documentation(rule_id: &str) -> Result<()> {
    // Normalize rule ID to uppercase
    let rule_id = rule_id.trim().to_uppercase();

    // Get embedded documentation
    let docs = rule_docs::get_rule_docs();

    if let Some(content) = docs.get(rule_id.as_str()) {
        println!("{}", content);
        Ok(())
    } else {
        eprintln!("Error: No documentation found for rule {}", rule_id);
        eprintln!("Use --show-config-docs to see available rules.");
        process::exit(exit_codes::USAGE_ERROR);
    }
}

fn main() -> Result<()> {
    let args = Args::parse();
    let start = Instant::now();

    // Track if we encountered any errors during execution
    let mut had_file_errors = false;
    let mut had_parse_errors = false;

    // Show config docs if requested
    if args.show_config_docs {
        show_configuration_docs();
        return Ok(());
    }

    // Show rule documentation if requested
    if let Some(rule_id) = args.show_rule_doc {
        return show_rule_documentation(&rule_id);
    }

    // Resolve show_source and color flags
    let show_source = !args.no_show_source && args.show_source;
    let use_color = !args.no_color && args.color;

    // Load configuration from pyproject.toml early for all modes
    let config = if let Some(config_path) = &args.config {
        load_config(Some(Path::new(config_path)))
    } else {
        // Try to find config starting from the first path argument
        let start_path = Path::new(&args.paths[0]);
        let abs_path = start_path
            .canonicalize()
            .unwrap_or_else(|_| start_path.to_path_buf());
        if args.verbose {
            eprintln!("Searching for pyproject.toml from: {}", abs_path.display());
        }
        if let Some(pyproject) = find_config_pyproject_toml(&abs_path) {
            if args.verbose {
                eprintln!(
                    "Found pyproject.toml with [tool.pinjected-linter] at: {}",
                    pyproject.display()
                );
            }
            load_config(Some(&pyproject))
        } else {
            // Fallback to searching from current directory
            if args.verbose {
                eprintln!("No pyproject.toml with [tool.pinjected-linter] found from path, searching from current directory");
            }
            load_config(None)
        }
    };

    // Merge config with command line arguments
    let (enable_rules, skip_patterns) =
        merge_config(config.as_ref(), &args.enable, &args.disable, &args.skip);

    // Quick count mode
    if args.count {
        let mut total = 0;
        for path_str in &args.paths {
            let path = Path::new(path_str);
            let files = if path.is_file() {
                vec![path.to_path_buf()]
            } else {
                find_python_files(path, &skip_patterns)
            };
            total += files.len();
        }
        println!("Found {} Python files", total);
        return Ok(());
    }

    // Process each path
    let mut all_violations = Vec::new();
    let mut total_files = 0;

    if args.verbose {
        if let Some(ref cfg) = config {
            eprintln!("Loaded config from pyproject.toml");
            if !cfg.exclude.is_empty() {
                eprintln!("  Exclude patterns from config: {:?}", cfg.exclude);
            }
            if !cfg.enable.is_empty() {
                eprintln!("  Enabled rules: {:?}", cfg.enable);
            }
            if !cfg.disable.is_empty() {
                eprintln!("  Disabled rules: {:?}", cfg.disable);
            }
        }
        eprintln!("  Final exclude patterns: {:?}", skip_patterns);
    }

    // Determine which rules to use
    let rule_filter = enable_rules.map(|rules| rules.join(","));

    // Prepare options
    let options = LinterOptions {
        threads: if args.no_parallel { 1 } else { args.threads },
        rule: rule_filter,
        skip_patterns: skip_patterns.clone(),
        cache: args.cache || !args.no_parallel, // Cache by default when parallel
    };

    if args.verbose || args.timing {
        eprintln!("Starting Pinjected linter");
    }

    for path_str in &args.paths {
        let path = Path::new(path_str);

        // Check if path exists
        if !path.exists() {
            eprintln!("Error: Path not found: {}", path.display());
            had_file_errors = true;
            continue;
        }

        if args.verbose {
            let files = if path.is_file() {
                vec![path.to_path_buf()]
            } else {
                find_python_files(path, &skip_patterns)
            };
            eprintln!(
                "Found {} Python files to analyze in {}",
                files.len(),
                path.display()
            );
        }

        // Run linter
        match lint_path(path, options.clone()) {
            Ok(result) => {
                total_files += result.files_analyzed;

                // Track errors
                if result.files_with_errors > 0 {
                    had_file_errors = true;
                }
                if result.parse_errors > 0 {
                    had_parse_errors = true;
                }

                // Collect violations
                for (file, violations) in result.violations {
                    all_violations.push((file, violations));
                }
            }
            Err(e) => {
                eprintln!("Error processing path {}: {}", path.display(), e);
                had_file_errors = true;
            }
        }
    }

    // Check if filter will be applied
    let filter_applied = args.severity.is_some() || !args.show_only.is_empty();

    // Filter by severity if requested
    if let Some(min_severity) = args.severity {
        use pinjected_linter::models::Severity;

        let severity_filter = match min_severity {
            SeverityLevel::Error => Severity::Error,
            SeverityLevel::Warning => Severity::Warning,
            SeverityLevel::Info => Severity::Info,
        };

        all_violations = all_violations
            .into_iter()
            .map(|(file, violations)| {
                let filtered: Vec<_> = violations
                    .into_iter()
                    .filter(|v| match (v.severity, &severity_filter) {
                        (Severity::Error, _) => true,
                        (Severity::Warning, Severity::Warning) => true,
                        (Severity::Warning, Severity::Info) => true,
                        (Severity::Info, Severity::Info) => true,
                        _ => false,
                    })
                    .collect();
                (file, filtered)
            })
            .filter(|(_, violations)| !violations.is_empty())
            .collect();
    } else if !args.show_only.is_empty() {
        use pinjected_linter::models::Severity;
        use std::collections::HashSet;

        // Parse the severity levels to show
        let mut show_levels = HashSet::new();
        for level in &args.show_only {
            match level.to_lowercase().as_str() {
                "error" | "errors" => {
                    show_levels.insert(Severity::Error);
                }
                "warning" | "warnings" => {
                    show_levels.insert(Severity::Warning);
                }
                "info" => {
                    show_levels.insert(Severity::Info);
                }
                _ => {
                    eprintln!("Warning: Unknown severity level '{}', valid values are: error, warning, info", level);
                }
            }
        }

        if !show_levels.is_empty() {
            all_violations = all_violations
                .into_iter()
                .map(|(file, violations)| {
                    let filtered: Vec<_> = violations
                        .into_iter()
                        .filter(|v| show_levels.contains(&v.severity))
                        .collect();
                    (file, filtered)
                })
                .filter(|(_, violations)| !violations.is_empty())
                .collect();
        }
    }

    // Report results based on output format
    match args.output_format {
        OutputFormat::Terminal => {
            report_terminal(&all_violations, show_source, use_color)?;
        }
        OutputFormat::Json => {
            report_json(&all_violations)?;
        }
        OutputFormat::Github => {
            report_github(&all_violations)?;
        }
    }

    // Always show statistics at the end
    let elapsed = start.elapsed();
    show_statistics(
        &all_violations,
        total_files,
        elapsed.as_secs_f64(),
        use_color,
        filter_applied,
    );

    // Determine exit code based on what happened
    let exit_code = if had_parse_errors {
        eprintln!(
            "\nExiting with code {} due to parse errors",
            exit_codes::PARSE_ERROR
        );
        exit_codes::PARSE_ERROR
    } else if had_file_errors {
        eprintln!(
            "\nExiting with code {} due to file errors",
            exit_codes::FILE_ERROR
        );
        exit_codes::FILE_ERROR
    } else {
        // Check for violations
        let has_errors = all_violations.iter().any(|(_, violations)| {
            violations
                .iter()
                .any(|v| matches!(v.severity, pinjected_linter::models::Severity::Error))
        });
        let has_warnings = all_violations.iter().any(|(_, violations)| {
            violations
                .iter()
                .any(|v| matches!(v.severity, pinjected_linter::models::Severity::Warning))
        });

        if has_errors || (has_warnings && args.error_on_warning) {
            exit_codes::VIOLATIONS_FOUND
        } else {
            exit_codes::SUCCESS
        }
    };

    if exit_code != exit_codes::SUCCESS {
        process::exit(exit_code);
    }

    Ok(())
}

fn show_statistics(
    violations: &[(std::path::PathBuf, Vec<pinjected_linter::models::Violation>)],
    total_files: usize,
    elapsed_secs: f64,
    use_color: bool,
    filter_applied: bool,
) {
    use pinjected_linter::models::Severity;

    // Calculate total violations
    let total_violations: usize = violations.iter().map(|(_, v)| v.len()).sum();

    // Count by severity
    let mut errors = 0;
    let mut warnings = 0;
    let mut infos = 0;

    // Count by rule
    let mut rule_counts: HashMap<String, usize> = HashMap::new();

    for (_, file_violations) in violations {
        for violation in file_violations {
            match violation.severity {
                Severity::Error => errors += 1,
                Severity::Warning => warnings += 1,
                Severity::Info => infos += 1,
            }

            *rule_counts.entry(violation.rule_id.clone()).or_insert(0) += 1;
        }
    }

    // Print separator
    eprintln!("\n{}", "=".repeat(60));

    if total_violations == 0 {
        if use_color {
            eprintln!("\x1b[32m✓ No issues found!\x1b[0m");
        } else {
            eprintln!("✓ No issues found!");
        }
    } else {
        eprintln!(
            "Linting Summary{}",
            if filter_applied { " (filtered)" } else { "" }
        );
        eprintln!("{}", "-".repeat(60));

        // Show total violations with breakdown
        eprintln!("Total violations: {}", total_violations);
        if use_color {
            eprintln!("  \x1b[31mErrors: {}\x1b[0m", errors);
            eprintln!("  \x1b[33mWarnings: {}\x1b[0m", warnings);
            eprintln!("  \x1b[34mInfo: {}\x1b[0m", infos);
        } else {
            eprintln!("  Errors: {}", errors);
            eprintln!("  Warnings: {}", warnings);
            eprintln!("  Info: {}", infos);
        }

        // Show violations by rule (top 10)
        if !rule_counts.is_empty() {
            eprintln!("\nViolations by rule:");
            let mut sorted_rules: Vec<_> = rule_counts.iter().collect();
            sorted_rules.sort_by(|a, b| b.1.cmp(a.1));

            for (rule, count) in sorted_rules.iter().take(10) {
                eprintln!("  {}: {}", rule, count);
            }

            if sorted_rules.len() > 10 {
                eprintln!("  ... and {} more rules", sorted_rules.len() - 10);
            }
        }
    }

    eprintln!("\nPerformance:");
    eprintln!("  Files analyzed: {}", total_files);
    eprintln!("  Time: {:.2}s", elapsed_secs);
    eprintln!("  Files/second: {:.2}", total_files as f64 / elapsed_secs);
    eprintln!("{}", "=".repeat(60));

    // Add help message for rule documentation
    if total_violations > 0 {
        eprintln!("\n💡 Use --show-rule-doc <RULE_ID> for detailed rule information and examples");
        eprintln!("   Example: pinjected-linter --show-rule-doc PINJ001");
    }
}

fn report_terminal(
    violations: &[(std::path::PathBuf, Vec<pinjected_linter::models::Violation>)],
    show_source: bool,
    use_color: bool,
) -> Result<()> {
    use pinjected_linter::models::Severity;

    // Sort by file path for consistent output
    let mut sorted_violations = violations.to_vec();
    sorted_violations.sort_by(|a, b| a.0.cmp(&b.0));

    for (file_idx, (file, file_violations)) in sorted_violations.iter().enumerate() {
        // Add spacing between files (but not before the first one)
        if file_idx > 0 {
            println!();
        }

        // Count violations by severity for this file
        let mut file_errors = 0;
        let mut file_warnings = 0;
        let mut file_infos = 0;

        for violation in file_violations {
            match violation.severity {
                Severity::Error => file_errors += 1,
                Severity::Warning => file_warnings += 1,
                Severity::Info => file_infos += 1,
            }
        }

        // Print file header with counts
        if use_color {
            print!("\x1b[1;4m{}\x1b[0m", file.display());
            print!(" (");
            if file_errors > 0 {
                print!(
                    "\x1b[31m{} error{}\x1b[0m",
                    file_errors,
                    if file_errors == 1 { "" } else { "s" }
                );
                if file_warnings > 0 || file_infos > 0 {
                    print!(", ");
                }
            }
            if file_warnings > 0 {
                print!(
                    "\x1b[33m{} warning{}\x1b[0m",
                    file_warnings,
                    if file_warnings == 1 { "" } else { "s" }
                );
                if file_infos > 0 {
                    print!(", ");
                }
            }
            if file_infos > 0 {
                print!("\x1b[34m{} info\x1b[0m", file_infos);
            }
            println!(")");
        } else {
            println!(
                "{} ({} error{}, {} warning{}, {} info)",
                file.display(),
                file_errors,
                if file_errors == 1 { "" } else { "s" },
                file_warnings,
                if file_warnings == 1 { "" } else { "s" },
                file_infos
            );
        }

        // Read file once for line number conversion
        if let Ok(content) = fs::read_to_string(&file) {
            let line_index = LineIndex::new(content.clone());

            // Sort violations by line number for better readability
            let mut sorted_file_violations = file_violations.clone();
            sorted_file_violations.sort_by(|a, b| a.offset.cmp(&b.offset));

            for violation in sorted_file_violations {
                let (line, column) = line_index.get_location(violation.offset);

                // Format: line:column: RULE: message (indented)
                if use_color {
                    print!("  {}:{}: ", line, column);

                    match violation.severity {
                        Severity::Error => print!("\x1b[31m{}\x1b[0m", violation.rule_id),
                        Severity::Warning => print!("\x1b[33m{}\x1b[0m", violation.rule_id),
                        Severity::Info => print!("\x1b[34m{}\x1b[0m", violation.rule_id),
                    }

                    println!(": {}", violation.message);
                } else {
                    println!(
                        "  {}:{}: {}: {}",
                        line, column, violation.rule_id, violation.message
                    );
                }

                // Show source if requested (indented more)
                if show_source && line > 0 {
                    if let Some(source_line) = content.lines().nth(line - 1) {
                        println!("      {}", source_line);
                        if column > 0 {
                            println!("      {}^", " ".repeat(column - 1));
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

fn report_json(
    violations: &[(std::path::PathBuf, Vec<pinjected_linter::models::Violation>)],
) -> Result<()> {
    use serde_json::json;

    let mut all_violations = Vec::new();

    for (file, file_violations) in violations {
        if let Ok(content) = fs::read_to_string(file) {
            let line_index = LineIndex::new(content);

            for violation in file_violations {
                let (line, column) = line_index.get_location(violation.offset);

                all_violations.push(json!({
                    "file": violation.file_path,
                    "line": line,
                    "column": column,
                    "rule": violation.rule_id,
                    "message": violation.message,
                    "severity": format!("{:?}", violation.severity).to_lowercase(),
                }));
            }
        }
    }

    let output = json!({
        "violations": all_violations,
        "count": all_violations.len(),
    });

    println!("{}", serde_json::to_string_pretty(&output)?);
    Ok(())
}

fn report_github(
    violations: &[(std::path::PathBuf, Vec<pinjected_linter::models::Violation>)],
) -> Result<()> {
    // GitHub Actions annotation format
    for (file, file_violations) in violations {
        if let Ok(content) = fs::read_to_string(file) {
            let line_index = LineIndex::new(content);

            for violation in file_violations {
                let (line, column) = line_index.get_location(violation.offset);

                let level = match violation.severity {
                    pinjected_linter::models::Severity::Error => "error",
                    pinjected_linter::models::Severity::Warning => "warning",
                    pinjected_linter::models::Severity::Info => "notice",
                };

                // ::error file=app.js,line=1,col=5,title=RULE::message
                println!(
                    "::{} file={},line={},col={},title={}::{}",
                    level, violation.file_path, line, column, violation.rule_id, violation.message
                );
            }
        }
    }

    Ok(())
}
