//! PINJ014: Missing .pyi stub file
//!
//! Modules with @injected functions should have corresponding .pyi stub files
//! for better IDE support and type checking.

pub mod ast_formatter;
pub mod injected_function_analyzer;
pub mod signature_formatter;
pub mod stub_file_generator;
pub mod stub_file_validator;

pub use self::rule::MissingStubFileRule;

mod rule {
    use crate::config::RuleConfig;
    use crate::models::{Fix, RuleContext, Severity, Violation};
    use crate::rules::base::LintRule;
    use rustpython_ast::Stmt;
    use std::path::Path;

    use super::injected_function_analyzer::InjectedFunctionAnalyzer;
    use super::stub_file_generator::StubFileGenerator;
    use super::stub_file_validator::StubFileValidator;

    pub struct MissingStubFileRule {
        min_injected_functions: usize,
        stub_search_paths: Vec<String>,
        ignore_patterns: Vec<String>,
    }

    impl MissingStubFileRule {
        pub fn new() -> Self {
            Self {
                min_injected_functions: 1,
                stub_search_paths: vec!["stubs".to_string(), "typings".to_string()],
                ignore_patterns: vec!["**/tests/**".to_string(), "**/migrations/**".to_string()],
            }
        }

        pub fn with_config(config: Option<&RuleConfig>) -> Self {
            match config {
                Some(cfg) => Self {
                    min_injected_functions: cfg.min_injected_functions.unwrap_or(1),
                    stub_search_paths: cfg
                        .stub_search_paths
                        .clone()
                        .unwrap_or_else(|| vec!["stubs".to_string(), "typings".to_string()]),
                    ignore_patterns: cfg
                        .ignore_patterns
                        .clone()
                        .unwrap_or_else(|| {
                            vec!["**/tests/**".to_string(), "**/migrations/**".to_string()]
                        }),
                },
                None => Self::new(),
            }
        }

        /// Check if the file path matches any ignore patterns
        fn should_ignore(&self, file_path: &str) -> bool {
            // Check ignore patterns
            for pattern in &self.ignore_patterns {
                // Handle directory patterns like "**/test/**" or "**/tests/**"
                if pattern.starts_with("**/") && pattern.ends_with("/**") {
                    let dir_name = &pattern[3..pattern.len() - 3];
                    if file_path.contains(&format!("/{}/", dir_name)) {
                        return true;
                    }
                }

                // Handle file patterns like "**/test_*.py"
                if pattern.starts_with("**/") && pattern.contains('*') {
                    if let Some(file_name) = Path::new(file_path).file_name() {
                        let file_name_str = file_name.to_str().unwrap_or("");

                        // Extract the pattern after "**/"
                        let file_pattern = &pattern[3..];

                        // Simple glob matching for patterns like "test_*.py"
                        if file_pattern.starts_with("test_") && file_pattern.ends_with(".py") {
                            if file_name_str.starts_with("test_") && file_name_str.ends_with(".py")
                            {
                                return true;
                            }
                        }
                        // Handle "*_test.py" pattern
                        else if file_pattern.starts_with("*_test.py") {
                            if file_name_str.ends_with("_test.py") {
                                return true;
                            }
                        }
                    }
                }
            }

            // Always ignore temporary files
            if let Some(file_name) = Path::new(file_path).file_name() {
                let name = file_name.to_str().unwrap_or("");
                if name.starts_with("tmp") && name.len() > 10 {
                    return true;
                }
            }

            if file_path.starts_with("/tmp/") && file_path.contains("tmp") && file_path.len() > 50 {
                return true;
            }

            false
        }

        /// Look for stub file in various locations
        fn find_stub_file(&self, file_path: &str) -> Option<std::path::PathBuf> {
            let path = Path::new(file_path);

            // Check same directory first
            let stub_path = path.with_extension("pyi");
            if stub_path.exists() {
                return Some(stub_path);
            }

            // Check alternative directories
            if let Some(parent) = path.parent() {
                for stub_dir in &self.stub_search_paths {
                    let alt_stub = parent
                        .join(stub_dir)
                        .join(path.file_name().unwrap())
                        .with_extension("pyi");
                    if alt_stub.exists() {
                        return Some(alt_stub);
                    }
                }
            }

            None
        }
    }

    impl LintRule for MissingStubFileRule {
        fn rule_id(&self) -> &str {
            "PINJ014"
        }

        fn description(&self) -> &str {
            "Modules with @injected functions should have corresponding .pyi stub files"
        }

        fn check(&self, context: &RuleContext) -> Vec<Violation> {
            let mut violations = Vec::new();

            // This is a module-level rule - check if we're in the module-level context
            // (identified by a Pass statement used as a placeholder)
            match context.stmt {
                Stmt::Pass(_) => {
                    // This is the module-level check, proceed
                }
                _ => {
                    // This is a statement-level check, skip since we handle this at module level
                    return violations;
                }
            }

            // Load configuration for this file
            let config_path = Path::new(context.file_path);
            let config = crate::config::find_config_pyproject_toml(config_path);
            let config_data = config.and_then(|p| crate::config::load_config(Some(&p)));
            let rule_config = config_data
                .as_ref()
                .and_then(|c| c.rules.get("PINJ014"));

            let configured_rule = Self::with_config(rule_config);

            // Skip if file is in ignore list
            if configured_rule.should_ignore(context.file_path) {
                return violations;
            }

            let analyzer = InjectedFunctionAnalyzer::new();

            // Count injected functions
            let count = analyzer.count_injected_functions(context.ast);

            // Skip if not enough injected functions
            if count < configured_rule.min_injected_functions {
                return violations;
            }

            // Look for stub file
            let stub_path = configured_rule.find_stub_file(context.file_path);

            // Collect injected functions for potential fix
            let injected_functions = analyzer.collect_injected_functions(context.ast);

            match stub_path {
                Some(path) => {
                    // Stub file exists, validate it
                    let validator = StubFileValidator::new();
                    let errors = validator.validate_stub_signatures(&path, &injected_functions);

                    if !errors.is_empty() {
                        let fix = if let Ok(existing_content) = std::fs::read_to_string(&path) {
                            let generator = StubFileGenerator::new();
                            let merged_content = generator
                                .merge_stub_content(&existing_content, &injected_functions);
                            Some(Fix {
                                description:
                                    "Update stub file with correct signatures while preserving existing content"
                                        .to_string(),
                                file_path: path.to_path_buf(),
                                content: merged_content,
                            })
                        } else {
                            let generator = StubFileGenerator::new();
                            let stub_content = generator.generate_stub_content(&injected_functions);
                            Some(Fix {
                                description: "Create stub file with proper signatures".to_string(),
                                file_path: path.to_path_buf(),
                                content: stub_content,
                            })
                        };

                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            severity: Severity::Warning,
                            message: format!(
                                "Stub file {} has incorrect signatures:\n\n{}",
                                path.display(),
                                errors.join("\n")
                            ),
                            offset: 0,
                            file_path: context.file_path.to_string(),
                            fix,
                        });
                    }
                }
                None => {
                    // Stub file doesn't exist, create one
                    let stub_path = Path::new(context.file_path).with_extension("pyi");
                    let generator = StubFileGenerator::new();
                    let stub_content = generator.generate_stub_content(&injected_functions);

                    violations.push(Violation {
                        rule_id: self.rule_id().to_string(),
                        severity: Severity::Warning,
                        message: format!(
                            "Module has {} @injected function{} but no .pyi stub file",
                            count,
                            if count > 1 { "s" } else { "" }
                        ),
                        offset: 0,
                        file_path: context.file_path.to_string(),
                        fix: Some(Fix {
                            description: "Create stub file with proper signatures".to_string(),
                            file_path: stub_path,
                            content: stub_content,
                        }),
                    });
                }
            }

            violations
        }
    }
}
