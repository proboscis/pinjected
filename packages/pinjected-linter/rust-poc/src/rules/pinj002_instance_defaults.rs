//! PINJ002: Instance function default arguments
//! 
//! @instance functions should not have default arguments.
//! Use design() for configuration instead.

use rustpython_ast::{Stmt, Expr, Arguments};
use crate::models::{Violation, RuleContext, Severity};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_instance_decorator, has_instance_decorator_async};

pub struct InstanceDefaultsRule;

impl InstanceDefaultsRule {
    pub fn new() -> Self {
        Self
    }
    
    fn default_to_str(expr: &Expr) -> String {
        match expr {
            Expr::Constant(c) => {
                match &c.value {
                    rustpython_ast::Constant::None => "None".to_string(),
                    rustpython_ast::Constant::Bool(b) => b.to_string(),
                    rustpython_ast::Constant::Str(s) => format!("{:?}", s),
                    rustpython_ast::Constant::Int(i) => i.to_string(),
                    rustpython_ast::Constant::Float(f) => f.to_string(),
                    _ => "...".to_string(),
                }
            }
            Expr::Name(name) => name.id.to_string(),
            _ => "...".to_string(),
        }
    }
    
    fn check_arguments(args: &Arguments) -> Vec<(String, String)> {
        let mut args_with_defaults = Vec::new();
        
        // In rustpython-ast, defaults are stored directly in args
        for arg in &args.args {
            if let Some(default) = &arg.default {
                args_with_defaults.push((
                    arg.def.arg.to_string(),
                    Self::default_to_str(default)
                ));
            }
        }
        
        args_with_defaults
    }
    
    fn generate_suggestion(_func_name: &str, args_with_defaults: &[(String, String)]) -> String {
        let design_args: Vec<String> = args_with_defaults
            .iter()
            .map(|(name, value)| format!("    {}={}", name, value))
            .collect();
        
        let args_str = design_args.join(",\n");
        
        format!(
            "Consider using:\nbase_design = design(\n{}\n)\nThen use base_design in your composition.",
            args_str
        )
    }
}

impl LintRule for InstanceDefaultsRule {
    fn rule_id(&self) -> &str {
        "PINJ002"
    }
    
    fn description(&self) -> &str {
        "@instance functions should not have default arguments"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                if has_instance_decorator(func) {
                    let args_with_defaults = Self::check_arguments(&func.args);
                    
                    if !args_with_defaults.is_empty() {
                        let default_strs: Vec<String> = args_with_defaults
                            .iter()
                            .map(|(name, value)| format!("{}={}", name, value))
                            .collect();
                        
                        let message = format!(
                            "@instance function '{}' has default arguments: {}. Use design() for configuration instead.",
                            func.name,
                            default_strs.join(", ")
                        );
                        
                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message,
                            offset: func.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                        });
                    }
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                // Same logic for async functions
                if has_instance_decorator_async(func) {
                    let args_with_defaults = Self::check_arguments(&func.args);
                    
                    if !args_with_defaults.is_empty() {
                        let default_strs: Vec<String> = args_with_defaults
                            .iter()
                            .map(|(name, value)| format!("{}={}", name, value))
                            .collect();
                        
                        let message = format!(
                            "@instance function '{}' has default arguments: {}. Use design() for configuration instead.",
                            func.name,
                            default_strs.join(", ")
                        );
                        
                        violations.push(Violation {
                            rule_id: self.rule_id().to_string(),
                            message,
                            offset: func.range.start().to_usize(),
                            file_path: context.file_path.to_string(),
                            severity: Severity::Error,
                        });
                    }
                }
            }
            _ => {}
        }

        violations
    }
}