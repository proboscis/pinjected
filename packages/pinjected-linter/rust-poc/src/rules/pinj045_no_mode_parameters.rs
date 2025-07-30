//! PINJ045: No mode/flag parameters
//!
//! Functions should not accept mode, flag, or strategy parameters (str, bool, enum) 
//! that control behavior. This violates the Single Responsibility Principle (SRP).
//! Use the strategy pattern with dependency injection instead.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async,
};
use rustpython_ast::{Arguments, Expr, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct NoModeParametersRule;

impl NoModeParametersRule {
    pub fn new() -> Self {
        Self
    }

    /// Check if a parameter name indicates it's a mode/flag parameter
    fn is_mode_parameter_name(name: &str) -> bool {
        let mode_indicators = [
            "mode", "type", "kind", "variant", "format", "style",
            "method", "approach", "option", "flag", "switch", "toggle",
        ];
        
        // Check exact matches (but not 'strategy' as it's often a legitimate object)
        if mode_indicators.contains(&name) {
            return true;
        }
        
        // Check if name ends with _mode, _type, etc.
        for indicator in &mode_indicators {
            if name.ends_with(&format!("_{}", indicator)) {
                return true;
            }
        }
        
        // Check boolean flag patterns
        if name.starts_with("use_") || name.starts_with("enable_") || 
           name.starts_with("disable_") || name.starts_with("is_") ||
           name.starts_with("should_") || name.starts_with("with_") ||
           name.starts_with("include_") {
            // These are boolean flag prefixes, indicating a flag parameter
            return true;
        }
        
        false
    }

    /// Check if a type annotation indicates a mode parameter
    fn is_mode_type_annotation(annotation: &Expr) -> bool {
        match annotation {
            // Check for bool type
            Expr::Name(name) => {
                name.id.as_str() == "bool"
            }
            // Check for str type when paired with mode-like parameter name
            Expr::Constant(constant) => {
                if let rustpython_ast::Constant::Str(s) = &constant.value {
                    s == "str" || s == "bool"
                } else {
                    false
                }
            }
            // Check for Literal types like Literal['fast', 'slow']
            Expr::Subscript(subscript) => {
                if let Expr::Name(name) = &*subscript.value {
                    if name.id.as_str() == "Literal" {
                        return true;
                    }
                }
                // Also check for Enum types
                if let Expr::Attribute(_attr) = &*subscript.value {
                    // Check if it's something like MyEnum.VALUE
                    return true;
                }
                false
            }
            // Check for Enum attribute access (e.g., ProcessingMode.FAST)
            Expr::Attribute(_) => true,
            _ => false,
        }
    }

    /// Check function arguments for mode parameters
    fn check_args_for_mode_parameters(
        args: &Arguments,
        _func_name: &str,
    ) -> Vec<(String, String)> {
        let mut mode_parameters = Vec::new();

        // Check positional-only args
        for arg in &args.posonlyargs {
            let param_name = arg.def.arg.as_str();
            
            // First check type annotation
            let mut is_bool_type = false;
            if let Some(annotation) = &arg.def.annotation {
                if let Expr::Name(name) = &**annotation {
                    if name.id.as_str() == "bool" {
                        is_bool_type = true;
                    }
                }
            }
            
            // Check by parameter name, but consider type
            if Self::is_mode_parameter_name(param_name) {
                // If it's not a bool type and has include_/with_ prefix, 
                // it might be a legitimate object parameter
                if !is_bool_type && (param_name.starts_with("include_") || param_name.starts_with("with_")) {
                    // Skip - it's likely an object, not a flag
                    continue;
                }
                
                let reason = if is_bool_type || param_name.starts_with("use_") || param_name.starts_with("enable_") {
                    "boolean flag parameter".to_string()
                } else {
                    "mode/strategy parameter".to_string()
                };
                mode_parameters.push((param_name.to_string(), reason));
                continue;
            }
            
            // If not flagged by name, check if it's a bool type
            if is_bool_type {
                mode_parameters.push((
                    param_name.to_string(), 
                    "boolean flag parameter".to_string()
                ));
                continue;
            }
            
            // Check for other mode type annotations (Literal, Enum)
            if let Some(annotation) = &arg.def.annotation {
                if Self::is_mode_type_annotation(annotation) && !is_bool_type {
                    // For other types, only flag if the name also suggests it's a mode
                    // Don't flag "strategy" as it's often a legitimate object
                    if param_name.contains("mode") || param_name.contains("type") || 
                       param_name.contains("format") {
                        mode_parameters.push((
                            param_name.to_string(),
                            "mode parameter with type annotation".to_string()
                        ));
                    }
                }
            }
        }

        // Check all regular args (not just positional-only)
        for arg in &args.args {
            let param_name = arg.def.arg.as_str();
            
            // First check type annotation
            let mut is_bool_type = false;
            if let Some(annotation) = &arg.def.annotation {
                if let Expr::Name(name) = &**annotation {
                    if name.id.as_str() == "bool" {
                        is_bool_type = true;
                    }
                }
            }
            
            // Check by parameter name, but consider type
            if Self::is_mode_parameter_name(param_name) {
                // If it's not a bool type and has include_/with_ prefix, 
                // it might be a legitimate object parameter
                if !is_bool_type && (param_name.starts_with("include_") || param_name.starts_with("with_")) {
                    // Skip - it's likely an object, not a flag
                    continue;
                }
                
                let reason = if is_bool_type || param_name.starts_with("use_") || param_name.starts_with("enable_") {
                    "boolean flag parameter".to_string()
                } else {
                    "mode/strategy parameter".to_string()
                };
                mode_parameters.push((param_name.to_string(), reason));
                continue;
            }
            
            // If not flagged by name, check if it's a bool type
            if is_bool_type {
                mode_parameters.push((
                    param_name.to_string(), 
                    "boolean flag parameter".to_string()
                ));
                continue;
            }
            
            // Check for other mode type annotations (Literal, Enum)
            if let Some(annotation) = &arg.def.annotation {
                if Self::is_mode_type_annotation(annotation) && !is_bool_type {
                    
                    // For other types, only flag if the name also suggests it's a mode
                    // Don't flag "strategy" as it's often a legitimate object
                    if param_name.contains("mode") || param_name.contains("type") || 
                       param_name.contains("format") {
                        mode_parameters.push((
                            param_name.to_string(),
                            "mode parameter with type annotation".to_string()
                        ));
                    }
                }
            }
        }

        // Also check keyword-only args
        for arg in &args.kwonlyargs {
            let param_name = arg.def.arg.as_str();
            
            // First check type annotation
            let mut is_bool_type = false;
            if let Some(annotation) = &arg.def.annotation {
                if let Expr::Name(name) = &**annotation {
                    if name.id.as_str() == "bool" {
                        is_bool_type = true;
                    }
                }
            }
            
            // Check by parameter name, but consider type
            if Self::is_mode_parameter_name(param_name) {
                // If it's not a bool type and has include_/with_ prefix, 
                // it might be a legitimate object parameter
                if !is_bool_type && (param_name.starts_with("include_") || param_name.starts_with("with_")) {
                    // Skip - it's likely an object, not a flag
                    continue;
                }
                
                let reason = if is_bool_type || param_name.starts_with("use_") || param_name.starts_with("enable_") {
                    "boolean flag parameter".to_string()
                } else {
                    "mode/strategy parameter".to_string()
                };
                mode_parameters.push((param_name.to_string(), reason));
            } else if is_bool_type {
                // If not flagged by name but is bool type, still flag it
                mode_parameters.push((
                    param_name.to_string(), 
                    "boolean flag parameter".to_string()
                ));
            }
        }

        mode_parameters
    }

    /// Check a function definition
    fn check_function(&self, func: &StmtFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check @injected functions
        if !has_injected_decorator(func) {
            return violations;
        }

        let mode_params = Self::check_args_for_mode_parameters(&func.args, func.name.as_str());

        for (param_name, reason) in mode_params {
            let message = format!(
                "@injected function '{}' has parameter '{}' which is a {}. \
                This violates the Single Responsibility Principle (SRP). \
                Consider refactoring to avoid mode parameters that change behavior paths.",
                func.name.as_str(),
                param_name,
                reason
            );

            violations.push(Violation {
                rule_id: self.rule_id().to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Error,
                fix: None,
            });
        }

        violations
    }

    /// Check an async function definition
    fn check_async_function(&self, func: &StmtAsyncFunctionDef) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Only check @injected functions
        if !has_injected_decorator_async(func) {
            return violations;
        }

        let mode_params = Self::check_args_for_mode_parameters(&func.args, func.name.as_str());

        for (param_name, reason) in mode_params {
            let message = format!(
                "@injected async function '{}' has parameter '{}' which is a {}. \
                This violates the Single Responsibility Principle (SRP). \
                Consider refactoring to avoid mode parameters that change behavior paths.",
                func.name.as_str(),
                param_name,
                reason
            );

            violations.push(Violation {
                rule_id: self.rule_id().to_string(),
                message,
                offset: func.range.start().to_usize(),
                file_path: String::new(), // Will be filled by caller
                severity: Severity::Error,
                fix: None,
            });
        }

        violations
    }
}

impl LintRule for NoModeParametersRule {
    fn rule_id(&self) -> &str {
        "PINJ045"
    }

    fn description(&self) -> &str {
        "Functions should not accept mode/flag parameters that control behavior"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            rustpython_ast::Stmt::FunctionDef(func) => {
                for mut violation in self.check_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
                }
            }
            rustpython_ast::Stmt::AsyncFunctionDef(func) => {
                for mut violation in self.check_async_function(func) {
                    violation.file_path = context.file_path.to_string();
                    violations.push(violation);
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
        let rule = NoModeParametersRule::new();
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
    fn test_mode_parameter_string() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data: list, mode: str):
    if mode == "fast":
        return quick_process(data)
    else:
        return slow_process(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ045");
        assert!(violations[0].message.contains("'mode'"));
        assert!(violations[0].message.contains("mode/strategy parameter"));
    }

    #[test]
    fn test_boolean_flag_parameter() {
        let code = r#"
from pinjected import injected

@injected
def fetch_data(endpoint: str, use_cache: bool):
    if use_cache:
        return get_from_cache(endpoint)
    return fetch_from_api(endpoint)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ045");
        assert!(violations[0].message.contains("'use_cache'"));
        assert!(violations[0].message.contains("boolean flag parameter"));
    }

    #[test]
    fn test_literal_type_parameter() {
        let code = r#"
from pinjected import injected
from typing import Literal

@injected
def format_output(data: dict, format: Literal['json', 'xml', 'yaml']):
    if format == 'json':
        return to_json(data)
    elif format == 'xml':
        return to_xml(data)
    else:
        return to_yaml(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ045");
        assert!(violations[0].message.contains("'format'"));
    }

    #[test]
    fn test_no_violation_with_dependency_injection() {
        let code = r#"
from pinjected import injected
from typing import Protocol

class DataProcessor(Protocol):
    def process(self, data: list) -> list:
        ...

@injected
def process_data(data: list, processor: DataProcessor):
    return processor.process(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_no_violation_regular_function() {
        let code = r#"
def regular_function(data: list, mode: str):
    # Not @injected, so no violation
    if mode == "fast":
        return quick_process(data)
    return slow_process(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_async_function_with_mode() {
        let code = r#"
from pinjected import injected

@injected
async def a_fetch_data(url: str, enable_retry: bool):
    if enable_retry:
        return await fetch_with_retry(url)
    return await fetch_once(url)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ045");
        assert!(violations[0].message.contains("'enable_retry'"));
        assert!(violations[0].message.contains("boolean flag parameter"));
    }

    #[test]
    fn test_multiple_mode_parameters() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data: list, mode: str, use_cache: bool, format_type: str):
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3);
        // Should catch mode, use_cache, and format_type
    }

    #[test]
    fn test_legitimate_strategy_parameter() {
        let code = r#"
from pinjected import injected

@injected
async def a_run_market_backtest(
    logger,
    /,
    a_ee_signal_based_trading_strategy: TradingStrategy,
    market_data: MarketData,
    config: BacktestConfig
):
    return await a_ee_signal_based_trading_strategy.backtest(market_data, config)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0, "Strategy objects should not be flagged");
    }

    #[test]
    fn test_include_with_bool_is_flagged() {
        let code = r#"
from pinjected import injected

@injected
def analyze_market(
    analyzer,
    /,
    market_data: MarketData,
    include_llm_strategy: bool
):
    # include_llm_strategy is a boolean flag, should be flagged
    return analyzer.analyze(market_data, include_llm_strategy)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1, "include_ prefix with bool type should be flagged");
        assert!(violations[0].message.contains("include_llm_strategy"));
    }
    
    #[test]
    fn test_include_strategy_object_not_flagged() {
        let code = r#"
from pinjected import injected

@injected
def analyze_market(
    analyzer,
    /,
    market_data: MarketData,
    include_llm_strategy: LLMStrategy
):
    # include_llm_strategy is a strategy object, not a boolean flag
    return analyzer.analyze(market_data, include_llm_strategy)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0, "Strategy objects with include_ prefix should not be flagged");
    }

    #[test] 
    fn test_all_boolean_flags_are_flagged() {
        let code = r#"
from pinjected import injected

@injected
def process_request(
    logger,
    /,
    request: Request,
    use_custom_handler: bool,  # Should be flagged - boolean flag
    enable_result_processor: bool,  # Should be flagged - boolean flag
    with_auth_provider: bool  # Should be flagged - boolean flag
):
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 3, "All boolean parameters should be flagged");
    }

    #[test]
    fn test_include_mode_is_flagged() {
        let code = r#"
from pinjected import injected

@injected
def process_data(
    processor,
    /,
    data: Data,
    include_debug_mode: bool  # Should be flagged - contains 'mode'
):
    pass
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("include_debug_mode"));
    }
}