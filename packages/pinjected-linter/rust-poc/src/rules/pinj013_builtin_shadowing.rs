//! PINJ013: Builtin shadowing detection
//!
//! Functions decorated with @instance or @injected should not use names
//! that shadow Python built-ins like dict, list, open, etc.

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{
    has_injected_decorator, has_injected_decorator_async, has_instance_decorator,
    has_instance_decorator_async,
};
use rustpython_ast::Stmt;

pub struct BuiltinShadowingRule;

impl BuiltinShadowingRule {
    pub fn new() -> Self {
        Self
    }

    fn get_python_builtins() -> &'static [&'static str] {
        &[
            // Types
            "dict",
            "list",
            "set",
            "tuple",
            "str",
            "int",
            "float",
            "bool",
            "type",
            "bytes",
            "bytearray",
            "memoryview",
            "complex",
            "frozenset",
            // Functions
            "print",
            "input",
            "open",
            "range",
            "len",
            "sorted",
            "reversed",
            "enumerate",
            "zip",
            "map",
            "filter",
            "all",
            "any",
            "sum",
            "min",
            "max",
            "abs",
            "round",
            "pow",
            "divmod",
            "hash",
            "id",
            "bin",
            "hex",
            "oct",
            "chr",
            "ord",
            "format",
            "repr",
            "ascii",
            "iter",
            "next",
            "callable",
            "compile",
            "eval",
            "exec",
            "globals",
            "locals",
            "vars",
            "dir",
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
            "isinstance",
            "issubclass",
            "super",
            "property",
            "classmethod",
            "staticmethod",
            "slice",
            "object",
            "help",
            "quit",
            "exit",
            "copyright",
            "credits",
            "license",
            // Exceptions
            "BaseException",
            "Exception",
            "TypeError",
            "ValueError",
            "RuntimeError",
            "KeyError",
            "IndexError",
            "AttributeError",
            "NameError",
            "ImportError",
            "SyntaxError",
            "IndentationError",
            "TabError",
            "SystemError",
            "SystemExit",
            "KeyboardInterrupt",
            "GeneratorExit",
            "StopIteration",
            "StopAsyncIteration",
            "ArithmeticError",
            "FloatingPointError",
            "OverflowError",
            "ZeroDivisionError",
            "AssertionError",
            "BufferError",
            "EOFError",
            "LookupError",
            "MemoryError",
            "OSError",
            "ReferenceError",
            "RuntimeWarning",
            "UserWarning",
            "DeprecationWarning",
            "Warning",
            // Constants
            "None",
            "True",
            "False",
            "Ellipsis",
            "NotImplemented",
            "__debug__",
            "__doc__",
            "__name__",
            "__package__",
        ]
    }

    fn get_suggestions(builtin_name: &str, is_instance: bool) -> Vec<String> {
        let suggestions: Vec<&str> = match builtin_name {
            "dict" => vec!["config_dict", "settings_dict", "data_dict", "params_dict"],
            "list" => vec!["item_list", "value_list", "result_list", "data_list"],
            "set" => vec!["item_set", "unique_set", "data_set", "value_set"],
            "tuple" => vec!["data_tuple", "result_tuple", "item_tuple", "value_tuple"],
            "str" => vec!["text_str", "value_str", "data_str", "result_str"],
            "int" => vec!["count_int", "value_int", "number_int", "id_int"],
            "float" => vec!["value_float", "number_float", "score_float", "rate_float"],
            "bool" => vec!["flag_bool", "is_enabled", "status_bool", "check_bool"],
            "type" => vec!["object_type", "data_type", "value_type", "class_type"],
            "open" => vec![
                "open_file",
                "file_opener",
                "open_resource",
                "open_connection",
            ],
            "print" => vec![
                "print_message",
                "log_message",
                "output_message",
                "display_message",
            ],
            "input" => vec!["user_input", "get_input", "read_input", "prompt_input"],
            "filter" => vec![
                "filter_items",
                "apply_filter",
                "filter_data",
                "filter_values",
            ],
            "map" => vec!["map_values", "apply_map", "transform_items", "map_data"],
            "range" => vec!["number_range", "value_range", "index_range", "item_range"],
            "len" => vec![
                "get_length",
                "count_items",
                "calculate_length",
                "item_count",
            ],
            "zip" => vec!["zip_items", "combine_lists", "zip_values", "merge_lists"],
            "hash" => vec!["compute_hash", "get_hash", "hash_value", "generate_hash"],
            "id" => vec!["get_id", "object_id", "item_id", "unique_id"],
            "compile" => vec![
                "compile_source",
                "compile_code",
                "compile_expression",
                "build_code",
            ],
            "eval" => vec![
                "evaluate_expression",
                "eval_code",
                "evaluate_string",
                "execute_expression",
            ],
            "exec" => vec!["execute_code", "exec_string", "run_code", "execute_script"],
            "format" => vec![
                "format_string",
                "format_text",
                "apply_format",
                "format_value",
            ],
            _ => vec![],
        };

        if suggestions.is_empty() {
            // Generate generic suggestions
            if is_instance {
                vec![
                    format!("{}_provider", builtin_name),
                    format!("{}_instance", builtin_name),
                    format!("get_{}", builtin_name),
                    format!("create_{}", builtin_name),
                ]
            } else {
                vec![
                    format!("{}_func", builtin_name),
                    format!("do_{}", builtin_name),
                    format!("handle_{}", builtin_name),
                    format!("process_{}", builtin_name),
                ]
            }
        } else {
            suggestions.into_iter().map(|s| s.to_string()).collect()
        }
    }
}

impl LintRule for BuiltinShadowingRule {
    fn rule_id(&self) -> &str {
        "PINJ013"
    }

    fn description(&self) -> &str {
        "Functions should not shadow Python built-in names"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();
        let builtins = Self::get_python_builtins();

        match context.stmt {
            Stmt::FunctionDef(func) => {
                let has_instance = has_instance_decorator(func);
                let has_injected = has_injected_decorator(func);

                if (has_instance || has_injected) && builtins.contains(&func.name.as_str()) {
                    let suggestions = Self::get_suggestions(&func.name, has_instance);
                    let suggestion_text = format!(
                        "Consider using a more descriptive name like '{}' or '{}'.",
                        suggestions[0], suggestions[1]
                    );

                    violations.push(Violation {
                        rule_id: self.rule_id().to_string(),
                        message: format!(
                            "Function '{}' shadows Python built-in name. {}",
                            func.name, suggestion_text
                        ),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Warning,
                    });
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                let has_instance = has_instance_decorator_async(func);
                let has_injected = has_injected_decorator_async(func);

                if (has_instance || has_injected) && builtins.contains(&func.name.as_str()) {
                    let suggestions = Self::get_suggestions(&func.name, has_instance);
                    let suggestion_text = format!(
                        "Consider using a more descriptive name like '{}' or '{}'.",
                        suggestions[0], suggestions[1]
                    );

                    violations.push(Violation {
                        rule_id: self.rule_id().to_string(),
                        message: format!(
                            "Function '{}' shadows Python built-in name. {}",
                            func.name, suggestion_text
                        ),
                        offset: func.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Warning,
                    });
                }
            }
            _ => {}
        }

        violations
    }
}
