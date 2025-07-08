//! Common patterns for detecting pinjected decorators and constructs

use rustpython_ast::{Expr, Keyword, StmtAsyncFunctionDef, StmtFunctionDef};

/// Check if an expression is an @instance decorator
pub fn is_instance_decorator(expr: &Expr) -> bool {
    match expr {
        Expr::Name(name) => name.id.as_str() == "instance",
        Expr::Attribute(attr) => {
            if let Expr::Name(name) = &*attr.value {
                name.id.as_str() == "pinjected" && attr.attr.as_str() == "instance"
            } else {
                false
            }
        }
        _ => false,
    }
}

/// Check if an expression is an @injected decorator
pub fn is_injected_decorator(expr: &Expr) -> bool {
    match expr {
        Expr::Name(name) => name.id.as_str() == "injected",
        Expr::Attribute(attr) => {
            if let Expr::Name(name) = &*attr.value {
                name.id.as_str() == "pinjected" && attr.attr.as_str() == "injected"
            } else {
                false
            }
        }
        _ => false,
    }
}

/// Check if a decorator is @instance(callable=True)
pub fn is_instance_callable_decorator(expr: &Expr) -> bool {
    match expr {
        Expr::Call(call) => {
            // Check if it's calling instance
            if let Expr::Name(name) = &*call.func {
                if name.id.as_str() == "instance" {
                    // Check for callable=True in keywords
                    return has_callable_true_keyword(&call.keywords);
                }
            } else if let Expr::Attribute(attr) = &*call.func {
                if let Expr::Name(name) = &*attr.value {
                    if name.id.as_str() == "pinjected" && attr.attr.as_str() == "instance" {
                        // Check for callable=True in keywords
                        return has_callable_true_keyword(&call.keywords);
                    }
                }
            }
        }
        _ => {}
    }
    false
}

/// Helper function to check if keywords contain callable=True
fn has_callable_true_keyword(keywords: &[Keyword]) -> bool {
    for keyword in keywords {
        if let Some(arg) = &keyword.arg {
            if arg.as_str() == "callable" {
                if let Expr::Constant(constant) = &keyword.value {
                    if let rustpython_ast::Constant::Bool(true) = &constant.value {
                        return true;
                    }
                }
            }
        }
    }
    false
}

/// Check if a function has @instance decorator
pub fn has_instance_decorator(func: &StmtFunctionDef) -> bool {
    func.decorator_list.iter().any(|d| is_instance_decorator(d))
}

/// Check if a function has @instance(callable=True) decorator
pub fn has_instance_callable_decorator(func: &StmtFunctionDef) -> bool {
    func.decorator_list
        .iter()
        .any(|d| is_instance_callable_decorator(d))
}

/// Check if an async function has @instance decorator
pub fn has_instance_decorator_async(func: &StmtAsyncFunctionDef) -> bool {
    func.decorator_list.iter().any(|d| is_instance_decorator(d))
}

/// Check if a function has @injected decorator
pub fn has_injected_decorator(func: &StmtFunctionDef) -> bool {
    func.decorator_list.iter().any(|d| is_injected_decorator(d))
}

/// Check if an async function has @instance(callable=True) decorator
pub fn has_instance_callable_decorator_async(func: &StmtAsyncFunctionDef) -> bool {
    func.decorator_list
        .iter()
        .any(|d| is_instance_callable_decorator(d))
}

/// Check if an async function has @injected decorator
pub fn has_injected_decorator_async(func: &StmtAsyncFunctionDef) -> bool {
    func.decorator_list.iter().any(|d| is_injected_decorator(d))
}

/// Check if a function name follows noun convention (for @instance)
pub fn is_noun_like(name: &str) -> bool {
    const VERB_PREFIXES: &[&str] = &[
        "get_",
        "set_",
        "create_",
        "make_",
        "build_",
        "fetch_",
        "load_",
        "save_",
        "delete_",
        "update_",
        "process_",
        "handle_",
        "parse_",
        "validate_",
        "check_",
        "compute_",
        "calculate_",
        "generate_",
        "render_",
        "execute_",
    ];

    !VERB_PREFIXES.iter().any(|prefix| name.starts_with(prefix))
}

/// Check if a function name follows verb convention (for @injected)
pub fn is_verb_like(name: &str) -> bool {
    // Common verb prefixes that indicate actions
    const VERB_PREFIXES: &[&str] = &[
        "get_",
        "set_",
        "create_",
        "build_",
        "setup_",
        "initialize_",
        "make_",
        "fetch_",
        "load_",
        "save_",
        "delete_",
        "update_",
        "process_",
        "handle_",
        "execute_",
        "run_",
        "start_",
        "stop_",
        "open_",
        "close_",
        "connect_",
        "disconnect_",
        "prepare_",
        "generate_",
        "compute_",
        "calculate_",
        "validate_",
        "check_",
        "send_",
        "receive_",
        "parse_",
        "format_",
        "convert_",
        "transform_",
        "register_",
        "unregister_",
        "enable_",
        "disable_",
        "configure_",
        "mount_",
        "unmount_",
        "bind_",
        "unbind_",
        "attach_",
        "detach_",
        "compile_",
        "render_",
        "draw_",
        "write_",
        "read_",
        "scan_",
        "authenticate_",
        "authorize_",
        "verify_",
        "sign_",
        "encrypt_",
        "decrypt_",
    ];

    // Check if it starts with a verb prefix
    for prefix in VERB_PREFIXES {
        if name.starts_with(prefix) {
            return true;
        }
    }

    // Common verbs that might appear alone or at the start
    const STANDALONE_VERBS: &[&str] = &[
        "init",
        "initialize",
        "setup",
        "build",
        "create",
        "make",
        "get",
        "fetch",
        "load",
        "process",
        "execute",
        "run",
        "validate",
        "check",
        "verify",
        "authenticate",
        "authorize",
        "parse",
        "format",
        "render",
        "compile",
        "transform",
        "start",
        "stop",
        "pause",
        "resume",
        "reset",
        "refresh",
        "handle",
        "manage",
        "control",
        "operate",
        "perform",
        "workflow",
        "pipeline",
        "orchestrate",
        "coordinate",
        "filter",
        "sort",
        "group",
        "aggregate",
        "reduce",
        "publish",
        "subscribe",
        "broadcast",
        "notify",
        "alert",
    ];

    // Check if it's a standalone verb
    if STANDALONE_VERBS.contains(&name) {
        return true;
    }

    // Check if first word (before underscore) is a verb
    if let Some(first_word) = name.split('_').next() {
        if STANDALONE_VERBS.contains(&first_word) {
            return true;
        }
    }

    // Common noun suffixes that indicate non-verb form
    const NOUN_SUFFIXES: &[&str] = &[
        "_data",
        "_info",
        "_config",
        "_configuration",
        "_result",
        "_response",
        "_request",
        "_state",
        "_status",
        "_context",
        "_manager",
        "_handler",
        "_service",
        "_client",
        "_provider",
        "_factory",
        "_builder",
        "_validator",
        "_processor",
        "_controller",
    ];

    // Check if it has noun suffixes (indicates non-verb form)
    for suffix in NOUN_SUFFIXES {
        if name.ends_with(suffix) {
            return false;
        }
    }

    // Additional heuristic: if it's a single word that's not in our verb list,
    // it's likely a noun
    if !name.contains('_') && !STANDALONE_VERBS.contains(&name) {
        return false;
    }

    false
}

/// Check if a function name has async prefix
pub fn has_async_prefix(name: &str) -> bool {
    name.starts_with("a_")
}

/// Find the position of slash separator in function arguments
pub fn find_slash_position(func: &StmtFunctionDef) -> Option<usize> {
    if func.args.posonlyargs.is_empty() {
        None
    } else {
        Some(func.args.posonlyargs.len())
    }
}

/// Find the position of slash separator in async function arguments
pub fn find_slash_position_async(func: &StmtAsyncFunctionDef) -> Option<usize> {
    if func.args.posonlyargs.is_empty() {
        None
    } else {
        Some(func.args.posonlyargs.len())
    }
}
