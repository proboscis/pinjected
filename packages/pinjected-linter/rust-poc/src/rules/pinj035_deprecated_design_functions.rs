//! PINJ035: No deprecated design functions
//!
//! This rule detects usage of deprecated functions: instances(), providers(),
//! classes(), destructors(), and injecteds() which should be replaced with design().

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Expr, Ranged, Stmt};

pub struct DeprecatedDesignFunctionsRule;

impl DeprecatedDesignFunctionsRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a function call is one of the deprecated design functions
    fn check_call(&self, call: &rustpython_ast::ExprCall) -> Option<(String, String)> {
        if let Expr::Name(name) = &*call.func {
            let func_name = name.id.as_str();
            match func_name {
                "instances" => Some((
                    func_name.to_string(),
                    self.create_instances_migration(&call),
                )),
                "providers" => Some((
                    func_name.to_string(),
                    self.create_providers_migration(&call),
                )),
                "classes" => Some((func_name.to_string(), self.create_classes_migration(&call))),
                "destructors" => Some((
                    func_name.to_string(),
                    self.create_destructors_migration(&call),
                )),
                "injecteds" => Some((
                    func_name.to_string(),
                    self.create_injecteds_migration(&call),
                )),
                _ => None,
            }
        } else {
            None
        }
    }

    /// Create migration suggestion for instances()
    fn create_instances_migration(&self, call: &rustpython_ast::ExprCall) -> String {
        if call.keywords.is_empty() {
            return "Replace with: design()".to_string();
        }

        let args: Vec<String> = call
            .keywords
            .iter()
            .filter_map(|kw| kw.arg.as_ref().map(|arg| format!("{}=...", arg)))
            .collect();

        if args.is_empty() {
            "Replace with: design()".to_string()
        } else {
            format!("Replace with: design({})", args.join(", "))
        }
    }

    /// Create migration suggestion for providers()
    fn create_providers_migration(&self, call: &rustpython_ast::ExprCall) -> String {
        if call.keywords.is_empty() {
            return "Replace with: design() with @injected decorated functions".to_string();
        }

        let funcs: Vec<String> = call
            .keywords
            .iter()
            .filter_map(|kw| kw.arg.as_ref().map(|arg| arg.to_string()))
            .collect();

        if funcs.len() == 1 {
            format!(
                "Replace with: @injected decorator on {} and design({}={})",
                funcs[0], funcs[0], funcs[0]
            )
        } else {
            "Replace with: @injected decorators on functions and design(key=function, ...)"
                .to_string()
        }
    }

    /// Create migration suggestion for classes()
    fn create_classes_migration(&self, call: &rustpython_ast::ExprCall) -> String {
        if call.keywords.is_empty() {
            return "Replace with: design() with @instance decorated factory functions".to_string();
        }

        let classes: Vec<String> = call
            .keywords
            .iter()
            .filter_map(|kw| kw.arg.as_ref().map(|arg| arg.to_string()))
            .collect();

        if classes.len() == 1 {
            let class_name = &classes[0];
            let factory_name = class_name.to_lowercase();
            format!(
                "Replace with: @instance decorated factory '{}' and design({}={})",
                factory_name, factory_name, factory_name
            )
        } else {
            "Replace with: @instance decorated factory functions and design(key=factory, ...)"
                .to_string()
        }
    }

    /// Create migration suggestion for destructors()
    fn create_destructors_migration(&self, _call: &rustpython_ast::ExprCall) -> String {
        "Replace with: context managers or cleanup in @injected functions".to_string()
    }

    /// Create migration suggestion for injecteds()
    fn create_injecteds_migration(&self, call: &rustpython_ast::ExprCall) -> String {
        if call.keywords.is_empty() {
            return "Replace with: design()".to_string();
        }

        let args: Vec<String> = call
            .keywords
            .iter()
            .filter_map(|kw| kw.arg.as_ref().map(|arg| format!("{}=...", arg)))
            .collect();

        format!("Replace with: design({})", args.join(", "))
    }
}

impl LintRule for DeprecatedDesignFunctionsRule {
    fn rule_id(&self) -> &str {
        "PINJ035"
    }

    fn description(&self) -> &str {
        "Deprecated design functions (instances, providers, classes, destructors, injecteds) should not be used"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            // Check standalone function calls
            Stmt::Expr(expr_stmt) => {
                if let Expr::Call(call) = &*expr_stmt.value {
                    if let Some((func_name, migration)) = self.check_call(call) {
                        violations.push(Violation {
                            rule_id: "PINJ035".to_string(),
                            message: format!(
                                "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}\n\nFor detailed migration guide run: pinjected-linter --show-rule-doc PINJ035",
                                func_name, migration
                            ),
                            offset: call.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }
                }
            }
            // Check assignments like d = instances(...)
            Stmt::Assign(assign) => {
                if let Expr::Call(call) = &*assign.value {
                    if let Some((func_name, migration)) = self.check_call(call) {
                        violations.push(Violation {
                            rule_id: "PINJ035".to_string(),
                            message: format!(
                                "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}\n\nFor detailed migration guide run: pinjected-linter --show-rule-doc PINJ035",
                                func_name, migration
                            ),
                            offset: call.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }
                }
            }
            // Check augmented assignments like d += instances(...)
            Stmt::AugAssign(aug_assign) => {
                if let Expr::Call(call) = &*aug_assign.value {
                    if let Some((func_name, migration)) = self.check_call(call) {
                        violations.push(Violation {
                            rule_id: "PINJ035".to_string(),
                            message: format!(
                                "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}\n\nFor detailed migration guide run: pinjected-linter --show-rule-doc PINJ035",
                                func_name, migration
                            ),
                            offset: call.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                            fix: None,
                        });
                    }
                }
            }
            // Check annotated assignments like d: Design = instances(...)
            Stmt::AnnAssign(ann_assign) => {
                if let Some(value) = &ann_assign.value {
                    if let Expr::Call(call) = &**value {
                        if let Some((func_name, migration)) = self.check_call(call) {
                            violations.push(Violation {
                                rule_id: "PINJ035".to_string(),
                                message: format!(
                                    "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}\n\nFor detailed migration guide run: pinjected-linter --show-rule-doc PINJ035",
                                    func_name, migration
                                ),
                                offset: call.range.start().to_usize(),
                                file_path: context.file_path.to_string(),
                                severity: Severity::Error,
                                fix: None,
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
        let rule = DeprecatedDesignFunctionsRule::new();
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
    fn test_instances_deprecated() {
        let code = r#"
from pinjected import instances

config = instances(host="localhost", port=5432)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ035");
        assert!(violations[0].message.contains("instances()"));
        assert!(violations[0].message.contains("deprecated"));
        assert!(violations[0]
            .message
            .contains("Replace with: design(host=..., port=...)"));
        assert!(violations[0]
            .message
            .contains("pinjected-linter --show-rule-doc PINJ035"));
    }

    #[test]
    fn test_providers_deprecated() {
        let code = r#"
from pinjected import providers

def get_db():
    return DB()

services = providers(database=get_db)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ035");
        assert!(violations[0].message.contains("providers()"));
        assert!(violations[0].message.contains(
            "Replace with: @injected decorator on database and design(database=database)"
        ));
        assert!(violations[0]
            .message
            .contains("pinjected-linter --show-rule-doc PINJ035"));
    }

    #[test]
    fn test_classes_deprecated() {
        let code = r#"
from pinjected import classes

bindings = classes(UserService=UserService, AuthService=AuthService)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ035");
        assert!(violations[0].message.contains("classes()"));
        assert!(violations[0]
            .message
            .contains("Replace with: @instance decorated factory functions"));
        assert!(violations[0]
            .message
            .contains("pinjected-linter --show-rule-doc PINJ035"));
    }

    #[test]
    fn test_destructors_deprecated() {
        let code = r#"
from pinjected import destructors

def cleanup_db(db):
    db.close()

cleanups = destructors(database=cleanup_db)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ035");
        assert!(violations[0].message.contains("destructors()"));
        assert!(violations[0]
            .message
            .contains("Replace with: context managers"));
        assert!(violations[0]
            .message
            .contains("pinjected-linter --show-rule-doc PINJ035"));
    }

    #[test]
    fn test_injecteds_deprecated() {
        let code = r#"
from pinjected import injecteds, Injected

bindings = injecteds(service=Injected.bind(lambda: Service()))
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ035");
        assert!(violations[0].message.contains("injecteds()"));
        assert!(violations[0]
            .message
            .contains("Replace with: design(service=...)"));
        assert!(violations[0]
            .message
            .contains("pinjected-linter --show-rule-doc PINJ035"));
    }

    #[test]
    fn test_design_not_flagged() {
        let code = r#"
from pinjected import design

config = design(host="localhost", port=5432)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_augmented_assignment() {
        let code = r#"
from pinjected import instances

d = design()
d += instances(extra="value")
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("instances()"));
        assert!(violations[0]
            .message
            .contains("Replace with: design(extra=...)"));
        assert!(violations[0]
            .message
            .contains("pinjected-linter --show-rule-doc PINJ035"));
    }

    #[test]
    fn test_expression_statement() {
        let code = r#"
from pinjected import providers

providers(service=lambda: Service())
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("providers()"));
        assert!(violations[0]
            .message
            .contains("Replace with: @injected decorator on service and design(service=service)"));
        assert!(violations[0]
            .message
            .contains("pinjected-linter --show-rule-doc PINJ035"));
    }
}
