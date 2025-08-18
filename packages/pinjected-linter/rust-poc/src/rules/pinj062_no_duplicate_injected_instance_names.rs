use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{Ranged, Stmt};

use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

static SEEN_FUNCTIONS: OnceLock<Mutex<HashMap<String, (String, usize)>>> = OnceLock::new();

fn seen_map() -> &'static Mutex<HashMap<String, (String, usize)>> {
    SEEN_FUNCTIONS.get_or_init(|| Mutex::new(HashMap::new()))
}

pub struct NoDuplicateInjectedInstanceNamesRule;

impl NoDuplicateInjectedInstanceNamesRule {
    pub fn new() -> Self {
        Self
    }

    fn is_injected_or_instance(stmt: &Stmt) -> Option<(String, usize)> {
        match stmt {
            Stmt::FunctionDef(func) => {
                let has_target_decorator = func
                    .decorator_list
                    .iter()
                    .any(|d| matches!(d, rustpython_ast::Expr::Name(n) if n.id.as_str() == "injected" || n.id.as_str() == "instance"));
                if has_target_decorator {
                    let name = func.name.to_string();
                    let offset = func.range().start().to_usize();
                    Some((name, offset))
                } else {
                    None
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                let has_target_decorator = func
                    .decorator_list
                    .iter()
                    .any(|d| matches!(d, rustpython_ast::Expr::Name(n) if n.id.as_str() == "injected" || n.id.as_str() == "instance"));
                if has_target_decorator {
                    let name = func.name.to_string();
                    let offset = func.range().start().to_usize();
                    Some((name, offset))
                } else {
                    None
                }
            }
            _ => None,
        }
    }

    fn message(name: &str, first_file: &str) -> String {
        format!(
"Duplicate provider name '{}' for @injected/@instance detected.

Pinjected uses function names as global DI keys when modules are imported. If multiple providers share the same name, later imports override earlier ones, causing unexpected global DI overrides.

First occurrence: {}

Rename the function to a unique, contextual name. Recommended conventions:
- Feature-specific implementation: store_feature_x_data_to_influxdb
- Generic protocol name:       store_data_y
- Specific protocol impl:      store_data_y__influxdb
- Fully generic (not specific): store_influxdb

For async @injected functions, use the 'a_' prefix (enforced by another rule), e.g.:
- a_store_data_y__influxdb
", name, first_file)
    }
}

impl LintRule for NoDuplicateInjectedInstanceNamesRule {
    fn rule_id(&self) -> &str {
        "PINJ062"
    }

    fn description(&self) -> &str {
        "Disallow duplicate function names among @injected/@instance providers across the codebase."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        if let Some((name, offset)) = Self::is_injected_or_instance(context.stmt) {
            let mut map = seen_map().lock().unwrap();
            if let Some((first_file, _first_off)) = map.get(&name) {
                violations.push(Violation {
                    rule_id: "PINJ062".to_string(),
                    message: Self::message(&name, first_file),
                    offset,
                    file_path: context.file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            } else {
                map.insert(name, (context.file_path.to_string(), offset));
            }
        }

        violations
    }
}
