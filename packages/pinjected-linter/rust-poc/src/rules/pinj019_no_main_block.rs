//! PINJ019: No __main__ block with pinjected functions
//!
//! Files containing @injected or @instance functions should not use __main__ blocks

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::{CmpOp, Expr, Mod, Stmt};

pub struct NoMainBlockRule;

impl NoMainBlockRule {
    pub fn new() -> Self {
        Self
    }

    fn is_main_block_condition(expr: &Expr) -> bool {
        match expr {
            Expr::Compare(compare) => {
                // Check for __name__ == "__main__"
                if compare.ops.len() == 1 && matches!(compare.ops[0], CmpOp::Eq) {
                    if let Expr::Name(left) = &*compare.left {
                        if left.id.as_str() == "__name__" && compare.comparators.len() == 1 {
                            if let Expr::Constant(right) = &compare.comparators[0] {
                                if let rustpython_ast::Constant::Str(s) = &right.value {
                                    return s.as_str() == "__main__";
                                }
                            }
                        }
                    }
                }
                // Also check for "__main__" == __name__
                if compare.ops.len() == 1 && matches!(compare.ops[0], CmpOp::Eq) {
                    if let Expr::Constant(left) = &*compare.left {
                        if let rustpython_ast::Constant::Str(s) = &left.value {
                            if s.as_str() == "__main__" && compare.comparators.len() == 1 {
                                if let Expr::Name(right) = &compare.comparators[0] {
                                    return right.id.as_str() == "__name__";
                                }
                            }
                        }
                    }
                }
            }
            _ => {}
        }
        false
    }

    fn check_has_pinjected_functions(stmt: &Stmt) -> bool {
        match stmt {
            Stmt::FunctionDef(func) => has_injected_decorator(func) || has_instance_decorator(func),
            Stmt::AsyncFunctionDef(func) => {
                has_injected_decorator_async(func) || has_instance_decorator_async(func)
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    if Self::check_has_pinjected_functions(stmt) {
                        return true;
                    }
                }
                false
            }
            _ => false,
        }
    }

    fn find_main_block(stmt: &Stmt) -> Option<usize> {
        if let Stmt::If(if_stmt) = stmt {
            if Self::is_main_block_condition(&if_stmt.test) {
                return Some(if_stmt.range.start().to_usize());
            }
        }
        None
    }
}

impl LintRule for NoMainBlockRule {
    fn rule_id(&self) -> &str {
        "PINJ019"
    }

    fn description(&self) -> &str {
        "No __main__ block with pinjected functions"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check when we encounter a main block
        if let Some(main_block_offset) = Self::find_main_block(context.stmt) {
            // Check if the file has any pinjected functions
            let mut has_pinjected = false;

            match context.ast {
                Mod::Module(module) => {
                    for stmt in &module.body {
                        if Self::check_has_pinjected_functions(stmt) {
                            has_pinjected = true;
                            break;
                        }
                    }
                }
                _ => {}
            }

            if has_pinjected {
                violations.push(Violation {
                    rule_id: self.rule_id().to_string(),
                    message: format!(
                        "Files with @injected/@instance functions should not use __main__ blocks. \
                         Pinjected is designed to be run using: python -m pinjected run <module.function>. \
                         See https://pinjected.readthedocs.io/en/latest/ for more information."
                    ),
                    offset: main_block_offset,
                    file_path: context.file_path.to_string(),
                    severity: Severity::Error,
                            fix: None,});
            }
        }

        violations
    }
}
