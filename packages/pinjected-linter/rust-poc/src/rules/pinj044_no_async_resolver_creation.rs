//! PINJ044: Direct AsyncResolver creation not allowed
//!
//! Direct instantiation of AsyncResolver is not allowed. The CLI approach (`python -m pinjected run`)
//! is the required method for running pinjected applications.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Ranged, Stmt};
use std::path::Path;

pub struct NoAsyncResolverCreationRule;

impl NoAsyncResolverCreationRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if the current file is part of the pinjected package
    fn is_pinjected_internal(file_path: &str) -> bool {
        let path = Path::new(file_path);
        
        // Check if file is inside pinjected package (not packages/pinjected-*)
        path.components().any(|component| {
            component.as_os_str() == "pinjected"
        }) && !path.components().any(|component| {
            component.as_os_str().to_string_lossy().starts_with("pinjected-")
        })
    }

    /// Check if an expression is AsyncResolver instantiation
    fn is_async_resolver_call(expr: &Expr) -> bool {
        match expr {
            Expr::Call(call) => {
                match &*call.func {
                    // Direct call: AsyncResolver(...)
                    Expr::Name(name) => name.id.as_str() == "AsyncResolver",
                    // Module call: pinjected.AsyncResolver(...)
                    Expr::Attribute(attr) => {
                        if attr.attr.as_str() == "AsyncResolver" {
                            if let Expr::Name(module) = &*attr.value {
                                return module.id.as_str() == "pinjected";
                            }
                        }
                        false
                    }
                    // Nested module call: pinjected.v2.async_resolver.AsyncResolver(...)
                    _ => false,
                }
            }
            _ => false,
        }
    }

    /// Check if the expression has a special marker comment
    fn has_intended_use_marker(source: &str, offset: usize) -> bool {
        // Look for a comment marker on the same line or the line before
        let lines: Vec<&str> = source.lines().collect();
        let mut current_offset = 0;
        
        for (line_idx, line) in lines.iter().enumerate() {
            let line_end = current_offset + line.len() + 1; // +1 for newline
            
            if offset >= current_offset && offset < line_end {
                // Check current line and previous line for marker
                let check_lines = if line_idx > 0 {
                    vec![lines[line_idx - 1], lines[line_idx]]
                } else {
                    vec![lines[line_idx]]
                };
                
                for check_line in check_lines {
                    if check_line.contains("# pinjected: allow-async-resolver") ||
                       check_line.contains("# noqa: PINJ044") {
                        return true;
                    }
                }
                break;
            }
            current_offset = line_end;
        }
        
        false
    }

    /// Recursively check an expression for AsyncResolver calls
    fn check_expr(&self, expr: &Expr, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        if Self::is_async_resolver_call(expr) {
            // Skip if in pinjected internal code
            if !Self::is_pinjected_internal(context.file_path) &&
               !Self::has_intended_use_marker(context.source, expr.range().start().to_usize()) {
                violations.push(Violation {
                    rule_id: "PINJ044".to_string(),
                    message: format!(
                        "Direct AsyncResolver instantiation is not allowed.\n\n\
                        Use the proper pinjected API instead:\n\
                        - For running applications: use 'python -m pinjected run <module.path>'\n\
                        - For testing: use register_fixtures_from_design() with pytest\n\
                        - For dependency inspection: use design inspection methods\n\n\
                        Direct usage increases code volume and reduces flexibility.\n\n\
                        If you must use AsyncResolver directly (rare), explicitly mark with:\n\
                        # pinjected: allow-async-resolver"
                    ),
                    offset: expr.range().start().to_usize(),
                    file_path: context.file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }

        // Recursively check sub-expressions
        match expr {
            Expr::Call(call) => {
                violations.extend(self.check_expr(&call.func, context));
                for arg in &call.args {
                    violations.extend(self.check_expr(arg, context));
                }
                for keyword in &call.keywords {
                    violations.extend(self.check_expr(&keyword.value, context));
                }
            }
            Expr::List(list) => {
                for elem in &list.elts {
                    violations.extend(self.check_expr(elem, context));
                }
            }
            Expr::Tuple(tuple) => {
                for elem in &tuple.elts {
                    violations.extend(self.check_expr(elem, context));
                }
            }
            Expr::Dict(dict) => {
                for key in dict.keys.iter().flatten() {
                    violations.extend(self.check_expr(key, context));
                }
                for value in &dict.values {
                    violations.extend(self.check_expr(value, context));
                }
            }
            _ => {}
        }

        violations
    }

    /// Check a statement for AsyncResolver usage
    fn check_stmt(&self, stmt: &Stmt, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match stmt {
            Stmt::Expr(expr_stmt) => {
                violations.extend(self.check_expr(&expr_stmt.value, context));
            }
            Stmt::Assign(assign) => {
                violations.extend(self.check_expr(&assign.value, context));
            }
            Stmt::AnnAssign(ann_assign) => {
                if let Some(value) = &ann_assign.value {
                    violations.extend(self.check_expr(value, context));
                }
            }
            Stmt::AugAssign(aug_assign) => {
                violations.extend(self.check_expr(&aug_assign.value, context));
            }
            Stmt::Return(return_stmt) => {
                if let Some(value) = &return_stmt.value {
                    violations.extend(self.check_expr(value, context));
                }
            }
            Stmt::FunctionDef(func) => {
                for stmt in &func.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                for stmt in &func.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::ClassDef(cls) => {
                for stmt in &cls.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::If(if_stmt) => {
                for stmt in &if_stmt.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
                for stmt in &if_stmt.orelse {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::While(while_stmt) => {
                for stmt in &while_stmt.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
                for stmt in &while_stmt.orelse {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::For(for_stmt) => {
                for stmt in &for_stmt.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
                for stmt in &for_stmt.orelse {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::With(with_stmt) => {
                for item in &with_stmt.items {
                    violations.extend(self.check_expr(&item.context_expr, context));
                }
                for stmt in &with_stmt.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::AsyncWith(with_stmt) => {
                for item in &with_stmt.items {
                    violations.extend(self.check_expr(&item.context_expr, context));
                }
                for stmt in &with_stmt.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    violations.extend(self.check_stmt(stmt, context));
                }
                for handler in &try_stmt.handlers {
                    let rustpython_ast::ExceptHandler::ExceptHandler(h) = handler;
                    for stmt in &h.body {
                        violations.extend(self.check_stmt(stmt, context));
                    }
                }
                for stmt in &try_stmt.orelse {
                    violations.extend(self.check_stmt(stmt, context));
                }
                for stmt in &try_stmt.finalbody {
                    violations.extend(self.check_stmt(stmt, context));
                }
            }
            _ => {}
        }

        violations
    }
}

impl LintRule for NoAsyncResolverCreationRule {
    fn rule_id(&self) -> &str {
        "PINJ044"
    }

    fn description(&self) -> &str {
        "AsyncResolver should not be instantiated directly by users"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        self.check_stmt(context.stmt, context)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_ast::Mod;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str, file_path: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, file_path).unwrap();
        let rule = NoAsyncResolverCreationRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let context = RuleContext {
                        stmt,
                        file_path,
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
    fn test_direct_async_resolver_creation() {
        let code = r#"
from pinjected import AsyncResolver, design

d = design(value=42)
resolver = AsyncResolver(d)  # VIOLATION
result = await resolver.provide("value")
"#;
        let violations = check_code(code, "test_app.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ044");
        assert!(violations[0].message.contains("not allowed"));
    }

    #[test]
    fn test_module_async_resolver_creation() {
        let code = r#"
import pinjected

d = pinjected.design()
resolver = pinjected.AsyncResolver(d)  # VIOLATION
"#;
        let violations = check_code(code, "app/main.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ044");
    }

    #[test]
    fn test_allowed_with_marker() {
        let code = r#"
from pinjected import AsyncResolver, design

d = design()
# pinjected: allow-async-resolver
resolver = AsyncResolver(d)  # OK - has marker
"#;
        let violations = check_code(code, "test_special.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_allowed_with_noqa() {
        let code = r#"
from pinjected import AsyncResolver, design

d = design()
resolver = AsyncResolver(d)  # noqa: PINJ044
"#;
        let violations = check_code(code, "test_noqa.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_allowed_in_pinjected_package() {
        let code = r#"
from pinjected.v2.async_resolver import AsyncResolver
from pinjected import design

d = design()
resolver = AsyncResolver(d)  # OK - inside pinjected package
"#;
        let violations = check_code(code, "pinjected/test/test_internal.py");
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_not_allowed_in_pinjected_linter() {
        let code = r#"
from pinjected import AsyncResolver, design

d = design()
resolver = AsyncResolver(d)  # VIOLATION - pinjected-linter is not pinjected
"#;
        let violations = check_code(code, "packages/pinjected-linter/test.py");
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ044");
    }

    #[test]
    fn test_nested_usage() {
        let code = r#"
from pinjected import AsyncResolver, design

def create_resolver():
    d = design()
    return AsyncResolver(d)  # VIOLATION

class TestClass:
    def setup(self):
        self.resolver = AsyncResolver(design())  # VIOLATION
"#;
        let violations = check_code(code, "app/test.py");
        assert_eq!(violations.len(), 2);
        assert!(violations.iter().all(|v| v.rule_id == "PINJ044"));
    }

    #[test]
    fn test_in_expression() {
        let code = r#"
from pinjected import AsyncResolver, design

resolvers = [
    AsyncResolver(design()),  # VIOLATION
    AsyncResolver(design())   # VIOLATION
]
"#;
        let violations = check_code(code, "test.py");
        assert_eq!(violations.len(), 2);
    }

    #[test]
    fn test_proper_api_usage() {
        let code = r#"
from pinjected import design, injected
from pinjected.test import register_fixtures_from_design

# Proper usage - no violations
@injected
def my_service(database, logger, /):
    logger.info("Service initialized")
    return Service(database)

# For application - define design and run via CLI
app_design = design(
    database="production_db",
    logger=lambda: logging.getLogger(__name__)
)

# For testing - register as fixtures
test_design = design(
    database="test_db",
    logger=lambda: logging.getLogger("test")
)
register_fixtures_from_design(test_design)

# No direct AsyncResolver usage
"#;
        let violations = check_code(code, "app.py");
        assert_eq!(violations.len(), 0);
    }
}