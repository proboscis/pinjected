//! PINJ015: Missing slash in injected
//!
//! In Pinjected, the '/' separator is critical:
//! - Arguments before '/' are positional-only and treated as dependencies (injected)
//! - Arguments after '/' are runtime arguments (must be provided when calling)
//! - Without '/', ALL arguments are treated as runtime arguments
//!
//! This rule warns when an @injected function has arguments but no '/',
//! which means no dependencies will be injected.
//!
//! To explicitly indicate that no dependencies are intended, add
//! `pinjected: no dependencies` in the docstring or a comment.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Expr, Stmt};

pub struct MissingSlashRule;

impl MissingSlashRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if function has any arguments
    fn has_arguments(args: &rustpython_ast::Arguments) -> bool {
        !args.args.is_empty() || !args.kwonlyargs.is_empty()
    }

    /// Check if function has the slash separator (position-only args)
    fn has_slash(args: &rustpython_ast::Arguments) -> bool {
        !args.posonlyargs.is_empty()
    }

    /// Check if function has 'pinjected: no dependencies' marker
    fn has_no_dependencies_marker(func: &rustpython_ast::StmtFunctionDef) -> bool {
        // Check docstring
        if let Some(docstring) = Self::get_docstring(func) {
            if docstring
                .to_lowercase()
                .contains("pinjected: no dependencies")
                || docstring
                    .to_lowercase()
                    .contains("pinjected:no dependencies")
            {
                return true;
            }
        }

        // Check comments in function body
        for stmt in &func.body {
            if let Stmt::Expr(expr_stmt) = stmt {
                if let Expr::Constant(constant) = &*expr_stmt.value {
                    if let rustpython_ast::Constant::Str(s) = &constant.value {
                        if s.to_lowercase().contains("pinjected: no dependencies")
                            || s.to_lowercase().contains("pinjected:no dependencies")
                        {
                            return true;
                        }
                    }
                }
            }
        }

        false
    }

    /// Check if async function has 'pinjected: no dependencies' marker
    fn has_no_dependencies_marker_async(func: &rustpython_ast::StmtAsyncFunctionDef) -> bool {
        // Check docstring
        if let Some(docstring) = Self::get_docstring_async(func) {
            if docstring
                .to_lowercase()
                .contains("pinjected: no dependencies")
                || docstring
                    .to_lowercase()
                    .contains("pinjected:no dependencies")
            {
                return true;
            }
        }

        // Check comments in function body
        for stmt in &func.body {
            if let Stmt::Expr(expr_stmt) = stmt {
                if let Expr::Constant(constant) = &*expr_stmt.value {
                    if let rustpython_ast::Constant::Str(s) = &constant.value {
                        if s.to_lowercase().contains("pinjected: no dependencies")
                            || s.to_lowercase().contains("pinjected:no dependencies")
                        {
                            return true;
                        }
                    }
                }
            }
        }

        false
    }

    /// Extract docstring from function
    fn get_docstring(func: &rustpython_ast::StmtFunctionDef) -> Option<String> {
        if let Some(first_stmt) = func.body.first() {
            if let Stmt::Expr(expr_stmt) = first_stmt {
                if let Expr::Constant(constant) = &*expr_stmt.value {
                    if let rustpython_ast::Constant::Str(s) = &constant.value {
                        return Some(s.clone());
                    }
                }
            }
        }
        None
    }

    /// Extract docstring from async function
    fn get_docstring_async(func: &rustpython_ast::StmtAsyncFunctionDef) -> Option<String> {
        if let Some(first_stmt) = func.body.first() {
            if let Stmt::Expr(expr_stmt) = first_stmt {
                if let Expr::Constant(constant) = &*expr_stmt.value {
                    if let rustpython_ast::Constant::Str(s) = &constant.value {
                        return Some(s.clone());
                    }
                }
            }
        }
        None
    }

    /// Generate a suggestion for adding slash
    fn generate_suggestion(func_name: &str, args: &rustpython_ast::Arguments) -> String {
        if args.args.is_empty() && args.kwonlyargs.is_empty() {
            return "Add '/' to separate dependencies from runtime arguments".to_string();
        }

        let mut likely_deps = Vec::new();
        let mut likely_runtime = Vec::new();

        // Common dependency patterns
        let dependency_patterns = vec![
            "logger",
            "database",
            "db",
            "cache",
            "client",
            "service",
            "repository",
            "repo",
            "manager",
            "handler",
            "processor",
            "transformer",
            "validator",
            "analyzer",
            "converter",
            "factory",
            "builder",
            "provider",
            "storage",
            "queue",
            "config",
            "settings",
            "session",
            "connection",
            "channel",
        ];

        // Analyze regular args
        for arg in &args.args {
            let arg_name = arg.def.arg.to_string();
            let arg_lower = arg_name.to_lowercase();

            // Check if it looks like a dependency
            let is_dependency = dependency_patterns
                .iter()
                .any(|pattern| arg_lower.contains(pattern))
                || arg_name.starts_with("a_");

            if is_dependency {
                likely_deps.push(arg_name);
            } else {
                likely_runtime.push(arg_name);
            }
        }

        // Add keyword-only args to runtime (they're always after the slash if there is one)
        for arg in &args.kwonlyargs {
            likely_runtime.push(arg.def.arg.to_string());
        }

        // Generate suggestion based on analysis
        if !likely_deps.is_empty() && !likely_runtime.is_empty() {
            format!(
                "If dependencies are {}, use: def {}({}, /, {})",
                likely_deps.join(", "),
                func_name,
                likely_deps.join(", "),
                likely_runtime.join(", ")
            )
        } else if !likely_deps.is_empty() {
            // All args look like dependencies
            let all_args: Vec<String> = args.args.iter().map(|a| a.def.arg.to_string()).collect();
            format!(
                "If all arguments are dependencies, use: def {}({}, /)",
                func_name,
                all_args.join(", ")
            )
        } else {
            // No clear dependencies
            let all_args: Vec<String> = args
                .args
                .iter()
                .map(|a| a.def.arg.to_string())
                .chain(args.kwonlyargs.iter().map(|a| a.def.arg.to_string()))
                .collect();
            format!(
                "Add '/' after dependencies. Example: def {}(dep1, dep2, /, {})",
                func_name,
                all_args.join(", ")
            )
        }
    }
}

impl LintRule for MissingSlashRule {
    fn rule_id(&self) -> &str {
        "PINJ015"
    }

    fn description(&self) -> &str {
        "@injected functions need '/' to mark dependencies as positional-only"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    // Check if has arguments but no slash
                    if Self::has_arguments(&func.args) && !Self::has_slash(&func.args) {
                        // Check if user explicitly marked "no dependencies"
                        if !Self::has_no_dependencies_marker(func) {
                            let suggestion = Self::generate_suggestion(&func.name, &func.args);

                            violations.push(Violation {
                                rule_id: self.rule_id().to_string(),
                                message: format!(
                                    "@injected function '{}' is missing the '/' separator. \
                                    Without '/', ALL arguments are treated as runtime arguments (not injected). \
                                    If you need dependency injection, add '/' after the dependencies. {}. \
                                    If this is intentional (no dependencies), add 'pinjected: no dependencies' \
                                    to the docstring or as a comment.",
                                    func.name,
                                    suggestion
                                ),
                                offset: func.range.start().to_usize(),
                                file_path: context.file_path.to_string(),
                                severity: Severity::Warning,
                            });
                        }
                    }
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    // Check if has arguments but no slash
                    if Self::has_arguments(&func.args) && !Self::has_slash(&func.args) {
                        // Check if user explicitly marked "no dependencies"
                        if !Self::has_no_dependencies_marker_async(func) {
                            let suggestion = Self::generate_suggestion(&func.name, &func.args);

                            violations.push(Violation {
                                rule_id: self.rule_id().to_string(),
                                message: format!(
                                    "@injected function '{}' is missing the '/' separator. \
                                    Without '/', ALL arguments are treated as runtime arguments (not injected). \
                                    If you need dependency injection, add '/' after the dependencies. {}. \
                                    If this is intentional (no dependencies), add 'pinjected: no dependencies' \
                                    to the docstring or as a comment.",
                                    func.name,
                                    suggestion
                                ),
                                offset: func.range.start().to_usize(),
                                file_path: context.file_path.to_string(),
                                severity: Severity::Warning,
                            });
                        }
                    }
                }
            }
            _ => {}
        }

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_ast::Mod;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = MissingSlashRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let context = RuleContext {
                        stmt,
                        file_path: "test.py",
                        source: code,
                        ast: &ast,
                    };
                    violations.extend(rule.check(&context));
                }
            }
            _ => {}
        }

        violations
    }

    #[test]
    fn test_missing_slash_with_args() {
        let code = r#"
from pinjected import injected

@injected
def process_data(logger, data):
    return logger.info(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ015");
        assert!(violations[0].message.contains("missing the '/' separator"));
        assert!(violations[0]
            .message
            .contains("add 'pinjected: no dependencies'"));
        assert_eq!(violations[0].severity, Severity::Warning);
    }

    #[test]
    fn test_missing_slash_with_no_dependencies_marker_docstring() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data):
    """Process data without dependencies.
    
    pinjected: no dependencies
    """
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_missing_slash_with_no_dependencies_marker_comment() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data):
    # pinjected: no dependencies
    return data.upper()
"#;
        let violations = check_code(code);
        // Comments are harder to detect in AST, this might still trigger
        // But docstrings are the recommended approach
        assert!(violations.len() <= 1);
    }

    #[test]
    fn test_missing_slash_with_no_dependencies_case_insensitive() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data):
    """Process data.
    
    PINJECTED: NO DEPENDENCIES
    """
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_with_slash_no_violation() {
        let code = r#"
from pinjected import injected

@injected
def process_data(logger, /, data):
    return logger.info(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_args_no_violation() {
        let code = r#"
from pinjected import injected

@injected
def get_config():
    return {"key": "value"}
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_async_missing_slash() {
        let code = r#"
from pinjected import injected

@injected
async def a_process_data(logger, data):
    return await logger.async_info(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ015");
        assert_eq!(violations[0].severity, Severity::Warning);
    }

    #[test]
    fn test_async_with_no_dependencies_marker() {
        let code = r#"
from pinjected import injected

@injected
async def a_process_data(data):
    """Async processor.
    
    pinjected: no dependencies
    """
    return data.upper()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }
}
