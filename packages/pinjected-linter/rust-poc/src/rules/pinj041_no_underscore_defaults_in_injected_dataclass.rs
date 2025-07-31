//! PINJ041: No default values or Optional types for underscore-prefixed attributes in @injected @dataclass
//!
//! Attributes starting with '_' in @injected @dataclass are meant to be injected via pinjected,
//! so they should not have default values or be Optional.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::has_injected_dataclass_decorators;
use rustpython_ast::{Expr, Stmt};

pub struct NoUnderscoreDefaultsInInjectedDataclassRule;

impl NoUnderscoreDefaultsInInjectedDataclassRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a type annotation indicates Optional type
    fn is_optional_type(expr: &Expr) -> bool {
        match expr {
            // Check for Optional[T], typing.Optional[T], Union[T, None], or typing.Union[T, None]
            Expr::Subscript(subscript) => {
                match &*subscript.value {
                    Expr::Name(name) => {
                        let name_str = name.id.as_str();
                        if name_str == "Optional" {
                            true
                        } else if name_str == "Union" {
                            // Check if the slice contains None
                            if let Expr::Tuple(tuple) = &*subscript.slice {
                                tuple.elts.iter().any(|elt| {
                                    if let Expr::Constant(constant) = elt {
                                        matches!(&constant.value, rustpython_ast::Constant::None)
                                    } else {
                                        false
                                    }
                                })
                            } else {
                                false
                            }
                        } else {
                            false
                        }
                    }
                    Expr::Attribute(attr) => {
                        if let Expr::Name(name) = &*attr.value {
                            if name.id.as_str() == "typing" {
                                let attr_str = attr.attr.as_str();
                                if attr_str == "Optional" {
                                    true
                                } else if attr_str == "Union" {
                                    // Check if the slice contains None
                                    if let Expr::Tuple(tuple) = &*subscript.slice {
                                        tuple.elts.iter().any(|elt| {
                                            if let Expr::Constant(constant) = elt {
                                                matches!(&constant.value, rustpython_ast::Constant::None)
                                            } else {
                                                false
                                            }
                                        })
                                    } else {
                                        false
                                    }
                                } else {
                                    false
                                }
                            } else {
                                false
                            }
                        } else {
                            false
                        }
                    }
                    _ => false,
                }
            }
            // Check for T | None pattern
            Expr::BinOp(binop) => {
                if let rustpython_ast::Operator::BitOr = binop.op {
                    if let Expr::Constant(constant) = &*binop.right {
                        matches!(&constant.value, rustpython_ast::Constant::None)
                    } else {
                        false
                    }
                } else {
                    false
                }
            }
            _ => false,
        }
    }

    fn check_class_body(&self, class_name: &str, body: &[Stmt], file_path: &str) -> Vec<Violation> {
        let mut violations = Vec::new();

        for stmt in body {
            if let Stmt::AnnAssign(ann_assign) = stmt {
                if let Expr::Name(name) = &*ann_assign.target {
                    if name.id.starts_with('_') {
                        let mut violation_messages = Vec::new();

                        // Check for default value
                        if ann_assign.value.is_some() {
                            violation_messages.push("has a default value");
                        }

                        // Check for Optional type
                        if Self::is_optional_type(&ann_assign.annotation) {
                            violation_messages.push("is typed as Optional");
                        }

                        if !violation_messages.is_empty() {
                            let message = format!(
                                "Attribute '{}' in @injected @dataclass '{}' {}. Underscore-prefixed attributes are injected by pinjected, so defaults/Optional types are ignored. Use design() to configure injected values instead.",
                                name.id,
                                class_name,
                                violation_messages.join(" and ")
                            );

                            violations.push(Violation {
                                rule_id: self.rule_id().to_string(),
                                message,
                                offset: ann_assign.range.start().to_usize(),
                                file_path: file_path.to_string(),
                                severity: Severity::Error,
                                fix: None,
                            });
                        }
                    }
                }
            }
        }

        violations
    }
}

impl LintRule for NoUnderscoreDefaultsInInjectedDataclassRule {
    fn rule_id(&self) -> &str {
        "PINJ041"
    }

    fn description(&self) -> &str {
        "Underscore-prefixed attributes in @injected @dataclass should not have default values or be Optional"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        match context.stmt {
            Stmt::ClassDef(class_def) => {
                if has_injected_dataclass_decorators(class_def) {
                    self.check_class_body(&class_def.name, &class_def.body, context.file_path)
                } else {
                    Vec::new()
                }
            }
            _ => Vec::new(),
        }
    }
}