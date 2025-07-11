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
                "classes" => Some((
                    func_name.to_string(),
                    self.create_classes_migration(&call),
                )),
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
            return "Use: design()".to_string();
        }

        let args: Vec<String> = call.keywords.iter()
            .filter_map(|kw| {
                kw.arg.as_ref().map(|arg| format!("{}=...", arg))
            })
            .collect();

        if args.is_empty() {
            "Use: design()".to_string()
        } else {
            format!("Use: design({})", args.join(", "))
        }
    }

    /// Create migration suggestion for providers()
    fn create_providers_migration(&self, call: &rustpython_ast::ExprCall) -> String {
        if call.keywords.is_empty() {
            return "Use: design() with @injected decorated functions".to_string();
        }

        let mut migration = String::from("Use:\n");
        
        // Add decorator suggestions
        for kw in &call.keywords {
            if let Some(arg) = &kw.arg {
                migration.push_str(&format!("@injected\ndef {}(...):\n    ...\n\n", arg));
            }
        }
        
        migration.push_str("with design() as d:\n");
        for kw in &call.keywords {
            if let Some(arg) = &kw.arg {
                migration.push_str(&format!("    d.provide({})\n", arg));
            }
        }

        migration
    }

    /// Create migration suggestion for classes()
    fn create_classes_migration(&self, call: &rustpython_ast::ExprCall) -> String {
        if call.keywords.is_empty() {
            return "Use: design() with @instance decorated functions".to_string();
        }

        let mut migration = String::from("Use:\n");
        
        // Add decorator suggestions
        for kw in &call.keywords {
            if let Some(arg) = &kw.arg {
                migration.push_str(&format!("@instance\ndef {}():\n    return {}()\n\n", 
                    arg.to_lowercase(), arg));
            }
        }
        
        migration.push_str("with design() as d:\n");
        for kw in &call.keywords {
            if let Some(arg) = &kw.arg {
                migration.push_str(&format!("    d.provide({})\n", arg.to_lowercase()));
            }
        }

        migration
    }

    /// Create migration suggestion for destructors()
    fn create_destructors_migration(&self, _call: &rustpython_ast::ExprCall) -> String {
        "Use context managers or cleanup in @injected functions:\n\
        @injected\n\
        def resource():\n\
            res = create_resource()\n\
            try:\n\
                yield res\n\
            finally:\n\
                res.cleanup()".to_string()
    }

    /// Create migration suggestion for injecteds()
    fn create_injecteds_migration(&self, call: &rustpython_ast::ExprCall) -> String {
        if call.keywords.is_empty() {
            return "Use: design()".to_string();
        }

        let args: Vec<String> = call.keywords.iter()
            .filter_map(|kw| {
                kw.arg.as_ref().map(|arg| format!("{}=...", arg))
            })
            .collect();

        format!("Use: design({})", args.join(", "))
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
                                "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}",
                                func_name, migration
                            ),
                            offset: call.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
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
                                "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}",
                                func_name, migration
                            ),
                            offset: call.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
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
                                "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}",
                                func_name, migration
                            ),
                            offset: call.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
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
                                    "Function '{}()' is deprecated since pinjected 0.3.0 and will be removed in a future version.\n\n{}",
                                    func_name, migration
                                ),
                                offset: call.range.start().to_usize(),
                                file_path: context.file_path.to_string(),
                                severity: Severity::Error,
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
        assert!(violations[0].message.contains("design(host=..., port=...)"));
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
        assert!(violations[0].message.contains("@injected"));
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
        assert!(violations[0].message.contains("@instance"));
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
        assert!(violations[0].message.contains("context managers"));
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
    }
}