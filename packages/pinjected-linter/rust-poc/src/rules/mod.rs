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
pub mod pinj014;
pub mod pinj015_missing_slash;
pub mod pinj016_missing_protocol;
pub mod pinj017_missing_dependency_type_annotation;
pub mod pinj018_double_injected;
pub mod pinj019_no_main_block;
pub mod pinj026_a_prefix_dependency_any_type;
pub mod pinj027_no_nested_injected;
pub mod pinj028_no_design_in_injected;
pub mod pinj029_no_injected_pure_instantiation;
pub mod pinj031_no_injected_calls_in_decorators;
pub mod pinj032_no_iproxy_return_type;
pub mod pinj033_no_iproxy_argument_type;
pub mod pinj034_no_lambda_in_design;
pub mod pinj035_deprecated_design_functions;
pub mod pinj036_enforce_pyi_stubs;
pub mod pinj040_enforce_injected_pytest;
pub mod pinj041_no_underscore_defaults_in_injected_dataclass;
pub mod pinj042_no_unmarked_injected_calls;
pub mod pinj043_no_design_in_test_functions;
pub mod pinj044_no_async_resolver_creation;
pub mod pinj045_no_mode_parameters;
pub mod pinj046_mutable_attribute_naming;
pub mod pinj047_max_mutable_attributes;
pub mod pinj048_no_default_dependencies_in_injected;
pub mod pinj049_enforce_protocol_type_annotations;
pub mod pinj050_no_os_environ;
pub mod pinj051_no_setter_methods;
pub mod pinj052_deprecated_register_fixtures;
pub mod pinj053_no_test_classes;
pub mod pinj054_no_tuple_returns;
pub mod pinj055_no_lambda_in_design_call;
pub mod pinj056_no_mutable_argument_mutations;
pub mod pinj057_no_callable_type_annotation;
pub mod pinj058_missing_return_type_annotation;
pub mod pinj059_test_file_placement;
pub mod pinj060_no_dataclass_attribute_mutation;
// Future rules would be added here:
pub mod pinj061_enforce_module_design_in_pytests;
pub mod pinj062_no_duplicate_injected_instance_names;

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
        Box::new(pinj014::MissingStubFileRule::new()),
        Box::new(pinj015_missing_slash::MissingSlashRule::new()),
        Box::new(pinj016_missing_protocol::MissingProtocolRule::new()),
        Box::new(
            pinj017_missing_dependency_type_annotation::MissingDependencyTypeAnnotationRule::new(),
        ),
        Box::new(pinj018_double_injected::DoubleInjectedRule::new()),
        Box::new(pinj019_no_main_block::NoMainBlockRule::new()),
        Box::new(pinj026_a_prefix_dependency_any_type::APrefixDependencyAnyTypeRule::new()),
        Box::new(pinj027_no_nested_injected::NoNestedInjectedRule::new()),
        Box::new(pinj028_no_design_in_injected::NoDesignInInjectedRule::new()),
        Box::new(pinj029_no_injected_pure_instantiation::NoInjectedPureInstantiationRule::new()),
        Box::new(pinj031_no_injected_calls_in_decorators::NoInjectedCallsInDecoratorsRule::new()),
        Box::new(pinj032_no_iproxy_return_type::NoIProxyReturnTypeRule::new()),
        Box::new(pinj033_no_iproxy_argument_type::NoIProxyArgumentTypeRule::new()),
        Box::new(pinj034_no_lambda_in_design::NoLambdaInDesignRule::new()),
        Box::new(pinj035_deprecated_design_functions::DeprecatedDesignFunctionsRule::new()),
        Box::new(pinj036_enforce_pyi_stubs::EnforcePyiStubsRule::new()),
        Box::new(pinj040_enforce_injected_pytest::EnforceInjectedPytestRule::new()),
        Box::new(pinj041_no_underscore_defaults_in_injected_dataclass::NoUnderscoreDefaultsInInjectedDataclassRule::new()),
        Box::new(pinj042_no_unmarked_injected_calls::NoUnmarkedInjectedCallsRule::new()),
        Box::new(pinj043_no_design_in_test_functions::NoDesignInTestFunctionsRule::new()),
        Box::new(pinj044_no_async_resolver_creation::NoAsyncResolverCreationRule::new()),
        Box::new(pinj045_no_mode_parameters::NoModeParametersRule::new()),
        Box::new(pinj046_mutable_attribute_naming::MutableAttributeNamingRule::new()),
        Box::new(pinj047_max_mutable_attributes::MaxMutableAttributesRule::new()),
        Box::new(pinj048_no_default_dependencies_in_injected::NoDefaultDependenciesInInjectedRule::new()),
        Box::new(pinj049_enforce_protocol_type_annotations::EnforceProtocolTypeAnnotationsRule::new()),
        Box::new(pinj050_no_os_environ::NoOsEnvironRule::new()),
        Box::new(pinj051_no_setter_methods::NoSetterMethodsRule::new()),
        Box::new(pinj052_deprecated_register_fixtures::DeprecatedRegisterFixturesRule::new()),
        Box::new(pinj053_no_test_classes::NoTestClassesRule::new()),
        Box::new(pinj054_no_tuple_returns::NoTupleReturnsRule::new()),
        Box::new(pinj055_no_lambda_in_design_call::NoLambdaInDesignCallRule::new()),
        Box::new(pinj056_no_mutable_argument_mutations::NoMutableArgumentMutationsRule::new()),
        Box::new(pinj057_no_callable_type_annotation::NoCallableTypeAnnotationRule::new()),
        Box::new(pinj058_missing_return_type_annotation::MissingReturnTypeAnnotationRule::new()),
        Box::new(pinj059_test_file_placement::TestFilePlacementRule::new()),
        Box::new(pinj060_no_dataclass_attribute_mutation::NoDataclassAttributeMutationRule::new()),
        // Add more rules here as they're implemented
        Box::new(pinj061_enforce_module_design_in_pytests::EnforceModuleDesignInPytestsRule::new()),
        Box::new(pinj062_no_duplicate_injected_instance_names::NoDuplicateInjectedInstanceNamesRule::new()),

    ]
}

/// Get rules by ID for quick lookup
pub fn get_rules_by_id() -> HashMap<String, Box<dyn LintRule>> {
    get_all_rules()
        .into_iter()
        .map(|rule| (rule.rule_id().to_string(), rule))
        .collect()
}

/// Get all available rule IDs
pub fn get_all_rule_ids() -> Vec<String> {
    get_all_rules()
        .into_iter()
        .map(|rule| rule.rule_id().to_string())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_rules_loaded() {
        let rules = get_all_rules();
        let rule_ids: Vec<_> = rules.iter().map(|r| r.rule_id()).collect();
        
        println!("Total rules: {}", rule_ids.len());
        for id in &rule_ids {
            println!("Rule: {}", id);
        }
        
        // Check specific rules exist
        assert!(rule_ids.contains(&"PINJ001"));
        assert!(rule_ids.contains(&"PINJ009"));
        assert!(rule_ids.contains(&"PINJ041"));
        assert!(rule_ids.contains(&"PINJ042"), "PINJ042 not found!");
        assert!(rule_ids.contains(&"PINJ043"), "PINJ043 not found!");
        assert!(rule_ids.contains(&"PINJ044"), "PINJ044 not found!");
        assert!(rule_ids.contains(&"PINJ045"), "PINJ045 not found!");
        assert!(rule_ids.contains(&"PINJ046"), "PINJ046 not found!");
        assert!(rule_ids.contains(&"PINJ047"), "PINJ047 not found!");
        assert!(rule_ids.contains(&"PINJ048"), "PINJ048 not found!");
        assert!(rule_ids.contains(&"PINJ049"), "PINJ049 not found!");
        assert!(rule_ids.contains(&"PINJ050"), "PINJ050 not found!");
        assert!(rule_ids.contains(&"PINJ051"), "PINJ051 not found!");
        assert!(rule_ids.contains(&"PINJ058"), "PINJ058 not found!");
        assert!(rule_ids.contains(&"PINJ060"), "PINJ060 not found!");
    }
}
