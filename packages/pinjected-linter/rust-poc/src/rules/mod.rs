//! Pinjected linting rules

pub mod base;

// Individual rule implementations
pub mod pinj001_instance_naming;
pub mod pinj002_instance_defaults;
pub mod pinj003_async_instance_naming;
pub mod pinj004_direct_instance_call;
pub mod pinj005_injected_function_naming;
pub mod pinj006_async_injected_naming;
pub mod pinj007_slash_separator_position;
pub mod pinj009_no_direct_injected_calls;
pub mod pinj010_design_usage;
pub mod pinj011_iproxy_annotations;
pub mod pinj012_dependency_cycles;
pub mod pinj013_builtin_shadowing;
pub mod pinj014_missing_stub_file;
pub mod pinj015_missing_slash;
pub mod pinj016_missing_protocol;
pub mod pinj017_missing_dependency_type_annotation;
pub mod pinj018_double_injected;
// Future rules would be added here:
// ... etc

use base::LintRule;
use std::collections::HashMap;

/// Get all available rules
pub fn get_all_rules() -> Vec<Box<dyn LintRule>> {
    vec![
        Box::new(pinj001_instance_naming::InstanceNamingRule::new()),
        Box::new(pinj002_instance_defaults::InstanceDefaultsRule::new()),
        Box::new(pinj003_async_instance_naming::AsyncInstanceNamingRule::new()),
        Box::new(pinj004_direct_instance_call::DirectInstanceCallRule::new()),
        Box::new(pinj005_injected_function_naming::InjectedFunctionNamingRule::new()),
        Box::new(pinj006_async_injected_naming::AsyncInjectedNamingRule::new()),
        Box::new(pinj007_slash_separator_position::SlashSeparatorPositionRule::new()),
        Box::new(pinj009_no_direct_injected_calls::NoDirectInjectedCallsRule::new()),
        Box::new(pinj010_design_usage::DesignUsageRule::new()),
        Box::new(pinj011_iproxy_annotations::IProxyAnnotationsRule::new()),
        Box::new(pinj012_dependency_cycles::DependencyCyclesRule::new()),
        Box::new(pinj013_builtin_shadowing::BuiltinShadowingRule::new()),
        Box::new(pinj014_missing_stub_file::MissingStubFileRule::new()),
        Box::new(pinj015_missing_slash::MissingSlashRule::new()),
        Box::new(pinj016_missing_protocol::MissingProtocolRule::new()),
        Box::new(
            pinj017_missing_dependency_type_annotation::MissingDependencyTypeAnnotationRule::new(),
        ),
        Box::new(pinj018_double_injected::DoubleInjectedRule::new()),
        // Add more rules here as they're implemented
    ]
}

/// Get rules by ID for quick lookup
pub fn get_rules_by_id() -> HashMap<String, Box<dyn LintRule>> {
    get_all_rules()
        .into_iter()
        .map(|rule| (rule.rule_id().to_string(), rule))
        .collect()
}
