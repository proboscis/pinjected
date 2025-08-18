//! PINJ042: No Unmarked Calls to @injected Functions
//!
//! @injected functions are designed to be used through the dependency injection system.
//! Direct calls from non-@injected contexts bypass the DI framework and should be
//! explicitly marked as intentional to prevent accidental misuse.
//!
//! This rule complements PINJ009, which handles calls within @injected functions.
//! PINJ042 handles calls from regular functions, methods, and other non-@injected contexts.
use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Expr, ExprCall, Mod, Stmt};
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex, OnceLock};

static IMPORT_CACHE: OnceLock<Arc<Mutex<HashMap<(String, String), bool>>>> = OnceLock::new();

fn get_import_cache() -> Arc<Mutex<HashMap<(String, String), bool>>> {
    IMPORT_CACHE.get_or_init(|| Arc::new(Mutex::new(HashMap::new()))).clone()
}

pub struct NoUnmarkedInjectedCallsRule {
    injected_functions: HashSet<String>,
    imported_injected_functions: HashMap<String, String>,
    in_injected_function: bool,
    function_stack: Vec<bool>,
    is_module_level: bool,
    is_iproxy_assignment: bool,
    in_pytest_function: bool,
    pytest_function_stack: Vec<bool>,
}

impl NoUnmarkedInjectedCallsRule {
    pub fn new() -> Self {
        Self {
            injected_functions: HashSet::new(),
            imported_injected_functions: HashMap::new(),
            in_injected_function: false,
            function_stack: Vec::new(),
            is_module_level: true,
            is_iproxy_assignment: false,
            in_pytest_function: false,
            pytest_function_stack: Vec::new(),
        }
    }

    fn collect_injected_functions(&mut self, module: &Mod) {
        if let Mod::Module(module) = module {
            for stmt in &module.body {
                self.collect_from_stmt(stmt);
            }
        }
    }

    fn collect_from_stmt(&mut self, stmt: &Stmt) {
        match stmt {
            Stmt::Import(_) => {}
            Stmt::ImportFrom(import_from) => {
                if let Some(module) = &import_from.module {
                    for alias in &import_from.names {
                        let func_name = alias.asname.as_ref().unwrap_or(&alias.name);
                        self.imported_injected_functions
                            .insert(func_name.to_string(), module.to_string());
                    }
                }
            }
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    self.injected_functions.insert(func.name.to_string());
                }
                for stmt in &func.body {
                    self.collect_from_stmt(stmt);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    self.injected_functions.insert(func.name.to_string());
                }
                for stmt in &func.body {
                    self.collect_from_stmt(stmt);
                }
            }
            Stmt::ClassDef(class) => {
                for stmt in &class.body {
                    self.collect_from_stmt(stmt);
                }
            }
            _ => {}
        }
    }

    fn resolve_import_path(&self, module_name: &str) -> Option<String> {
        Some(module_name.to_string())
    }

    fn is_test_function(func_name: &str, decorator_list: &[Expr]) -> bool {
        if func_name.starts_with("test_") {
            return true;
        }
        for decorator in decorator_list {
            if Self::is_pytest_decorator(decorator) {
                return true;
            }
        }
        false
    }

    fn is_pytest_decorator(expr: &Expr) -> bool {
        match expr {
            Expr::Attribute(attr) => {
                if let Expr::Attribute(inner_attr) = &*attr.value {
                    if let Expr::Name(name) = &*inner_attr.value {
                        return name.id.as_str() == "pytest" && inner_attr.attr.as_str() == "mark";
                    }
                }
                if let Expr::Name(name) = &*attr.value {
                    return name.id.as_str() == "pytest";
                }
                false
            }
            _ => false,
        }
    }

    fn is_imported_function_injected(&self, func_name: &str, module: &str) -> bool {
        let cache_key = (module.to_string(), func_name.to_string());
        if let Ok(cache) = get_import_cache().lock() {
            if let Some(&is_injected) = cache.get(&cache_key) {
                return is_injected;
            }
        }
        false
    }

    fn has_explicit_marking(&self, source: &str, offset: usize) -> bool {
        let lines: Vec<&str> = source.lines().collect();
        let mut current_offset = 0;
        for line in lines {
            let line_end = current_offset + line.len() + 1;
            if offset >= current_offset && offset < line_end {
                return line.contains("# pinjected: explicit-call") || line.contains("# noqa: PINJ042");
            }
            current_offset = line_end;
        }
        false
    }

    fn is_iproxy_annotation(&self, annotation: &Expr) -> bool {
        match annotation {
            Expr::Name(_) => false,
            Expr::Attribute(_) => false,
            Expr::Subscript(subscript) => {
                if let Expr::Name(name) = &*subscript.value {
                    name.id.to_string() == "IProxy"
                } else if let Expr::Attribute(attr) = &*subscript.value {
                    if let Expr::Name(name) = &*attr.value {
                        name.id.to_string() == "pinjected" && attr.attr.to_string() == "IProxy"
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

    fn check_call(&self, call: &ExprCall, context: &RuleContext, violations: &mut Vec<Violation>) {
        if self.in_injected_function {
            return;
        }

        let func_name = match &*call.func {
            Expr::Name(name) => Some(name.id.to_string()),
            Expr::Attribute(_) => None,
            _ => None,
        };

        if let Some(called_func) = func_name {
            let is_local_injected = self.injected_functions.contains(&called_func);
            let is_imported_injected = if let Some(module) = self.imported_injected_functions.get(&called_func) {
                self.is_imported_function_injected(&called_func, module)
            } else {
                false
            };

            if is_local_injected || is_imported_injected {
                if !self.has_explicit_marking(context.source, call.range.start().to_usize()) {
                    if self.is_module_level && self.is_iproxy_assignment {
                        return;
                    }

                    let source_info = if is_imported_injected {
                        if let Some(module) = self.imported_injected_functions.get(&called_func) {
                            format!(" (imported from '{}')", module)
                        } else {
                            String::new()
                        }
                    } else {
                        String::new()
                    };

                    let message = if self.in_pytest_function {
                        format!(
                            "Calling @injected function '{}'{} directly in pytest test function!\n\n\
                            WHY THIS IS FORBIDDEN:\n\
                            - @injected functions return IProxy objects when called directly\n\
                            - In pytest, dependencies should be requested as fixtures, not called directly\n\
                            - Direct calls bypass pytest's dependency injection system\n\n\
                            CORRECT APPROACH FOR PYTEST:\n\
                            1. Use pytest fixtures: Declare '{}' as a fixture parameter\n\
                            2. Set up fixtures using register_fixtures_from_design() at module level\n\
                            3. Let pytest inject the resolved dependency\n\n\
                            EXAMPLE:\n\
                            # At module level:\n\
                            from pinjected import design\n\
                            from pinjected.test import register_fixtures_from_design\n\n\
                            test_design = design(\n\
                                {}={}(),\n\
                                # ... other dependencies\n\
                            )\n\
                            register_fixtures_from_design(test_design)\n\n\
                            # In your test:\n\
                            def test_something({}, other_fixture):\n\
                                # {} is now the resolved function, not an IProxy\n\
                                result = {}(args)  # This works!\n\n\
                            NOTE ON BYPASSING THIS ERROR:\n\
                            While you can add '# pinjected: explicit-call' to suppress this error, this is PROBABLY WRONG\n\
                            and should NOT be done without supervisor's instruction. It's a complex feature that bypasses\n\
                            the dependency injection system and can lead to runtime errors.",
                            called_func, source_info, called_func, called_func, called_func, called_func, called_func, called_func
                        )
                    } else if self.is_module_level {
                        format!(
                            "Module-level call to @injected function '{}'{} requires IProxy[T] type annotation!\n\n\
                            UNDERSTANDING MODULE-LEVEL CALLS:\n\
                            - At module level, calling @injected functions creates IProxy entrypoints\n\
                            - These are used to define module-level dependency injection entry points\n\
                            - You MUST explicitly type the variable as IProxy[T] with a type parameter\n\n\
                            CORRECT USAGE:\n\
                            # Explicitly typed as IProxy with type parameter\n\
                            my_entrypoint: IProxy[ServiceType] = {}(\"args\")\n\
                            # Avoid using Any; prefer a concrete type or a Protocol type parameter\n\
                            # IProxy[Any] remains allowed but is discouraged\n\
                            # my_entrypoint: IProxy[Any] = {}(\"args\")\n\n\
                            WHY TYPE PARAMETER IS REQUIRED:\n\
                            - Ensures proper type checking for dependency resolution\n\
                            - Makes the expected return type explicit\n\
                            - Prevents runtime type errors in the DI system\n\n\
                            If this is not meant to be an entrypoint, consider moving this call inside a function.\n\n\
                            NOTE ON BYPASSING THIS ERROR:\n\
                            While you can add '# pinjected: explicit-call' to suppress this error, this is PROBABLY WRONG\n\
                            and should NOT be done without supervisor's instruction. It's a complex feature that bypasses\n\
                            the dependency injection system and can lead to runtime errors.",
                            called_func, source_info, called_func, called_func
                        )
                    } else {
                        format!(
                            "Calling @injected function '{}'{} directly returns an IProxy, not the actual function!\n\n\
                            WHY THIS IS FORBIDDEN:\n\
                            - @injected functions return IProxy objects when called directly\n\
                            - They are NOT meant to be executed without dependency resolution\n\
                            - Only resolved functions (through DI) can be called with runtime arguments\n\n\
                            CORRECT APPROACHES:\n\
                            1. Use dependency injection: Declare '{}' as a dependency in an @injected function\n\
                            2. Convert this function to @injected and declare '{}' as a dependency\n\
                            3. Use Design().run() or similar DI execution methods\n\n\
                            EXAMPLE 1 - Using dependency injection:\n\
                            @injected\n\
                            def my_function({}, /, data):\n\
                                return {}(data)\n\n\
                            EXAMPLE 2 - Using Design:\n\
                            with design({}: {}()) as d:\n\
                                result = d.run(lambda {}: {}(data))\n\n\
                            Direct calls to @injected functions should be avoided. If you're seeing this in legacy code,\n\
                            consider refactoring to use proper dependency injection patterns.\n\n\
                            NOTE ON BYPASSING THIS ERROR:\n\
                            While you can add '# pinjected: explicit-call' to suppress this error, this is PROBABLY WRONG\n\
                            and should NOT be done without supervisor's instruction. It's a complex feature that bypasses\n\
                            the dependency injection system and can lead to runtime errors.",
                            called_func, source_info, called_func, called_func, called_func, called_func, called_func, called_func, called_func, called_func
                        )
                    };

                    violations.push(Violation {
                        rule_id: "PINJ042".to_string(),
                        message,
                        offset: call.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
            }
        }
    }

    fn check_expr(&self, expr: &Expr, context: &RuleContext, violations: &mut Vec<Violation>) {
        match expr {
            Expr::Call(call) => {
                self.check_call(call, context, violations);
                for arg in &call.args {
                    self.check_expr(arg, context, violations);
                }
            }
            Expr::BinOp(binop) => {
                self.check_expr(&binop.left, context, violations);
                self.check_expr(&binop.right, context, violations);
            }
            Expr::UnaryOp(unaryop) => {
                self.check_expr(&unaryop.operand, context, violations);
            }
            Expr::Lambda(lambda) => {
                self.check_expr(&lambda.body, context, violations);
            }
            Expr::IfExp(ifexp) => {
                self.check_expr(&ifexp.test, context, violations);
                self.check_expr(&ifexp.body, context, violations);
                self.check_expr(&ifexp.orelse, context, violations);
            }
            Expr::Dict(dict) => {
                for key in dict.keys.iter().flatten() {
                    self.check_expr(key, context, violations);
                }
                for value in &dict.values {
                    self.check_expr(value, context, violations);
                }
            }
            Expr::List(list) => {
                for elem in &list.elts {
                    self.check_expr(elem, context, violations);
                }
            }
            Expr::Await(await_expr) => {
                self.check_expr(&await_expr.value, context, violations);
            }
            _ => {}
        }
    }

    fn check_stmt(&mut self, stmt: &Stmt, context: &RuleContext, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                let was_injected = has_injected_decorator(func);
                let is_pytest = Self::is_test_function(&func.name, &func.decorator_list);

                self.function_stack.push(self.in_injected_function);
                self.pytest_function_stack.push(self.in_pytest_function);

                self.in_injected_function = was_injected;
                self.in_pytest_function = is_pytest;
                let was_module_level = self.is_module_level;
                self.is_module_level = false;

                for stmt in &func.body {
                    self.check_stmt(stmt, context, violations);
                }

                self.in_injected_function = self.function_stack.pop().unwrap_or(false);
                self.in_pytest_function = self.pytest_function_stack.pop().unwrap_or(false);
                self.is_module_level = was_module_level;
            }
            Stmt::AsyncFunctionDef(func) => {
                let was_injected = has_injected_decorator_async(func);
                let is_pytest = Self::is_test_function(&func.name, &func.decorator_list);

                self.function_stack.push(self.in_injected_function);
                self.pytest_function_stack.push(self.in_pytest_function);

                self.in_injected_function = was_injected;
                self.in_pytest_function = is_pytest;
                let was_module_level = self.is_module_level;
                self.is_module_level = false;

                for stmt in &func.body {
                    self.check_stmt(stmt, context, violations);
                }

                self.in_injected_function = self.function_stack.pop().unwrap_or(false);
                self.in_pytest_function = self.pytest_function_stack.pop().unwrap_or(false);
                self.is_module_level = was_module_level;
            }
            Stmt::ClassDef(class) => {
                let was_module_level = self.is_module_level;
                self.is_module_level = false;

                for stmt in &class.body {
                    self.check_stmt(stmt, context, violations);
                }

                self.is_module_level = was_module_level;
            }
            Stmt::AnnAssign(ann) => {
                let was_iproxy = self.is_iproxy_assignment;
                if self.is_module_level {
                    if let Some(annotation) = &ann.annotation {
                        self.is_iproxy_assignment = self.is_iproxy_annotation(annotation);
                    }
                }

                if let Some(value) = &ann.value {
                    self.check_expr(value, context, violations);
                }

                self.is_iproxy_assignment = was_iproxy;
            }
            Stmt::Assign(assign) => {
                for value in &assign.value {
                    self.check_expr(value, context, violations);
                }
            }
            Stmt::Expr(expr) => {
                self.check_expr(&expr.value, context, violations);
            }
            _ => {}
        }
    }
}

impl LintRule for NoUnmarkedInjectedCallsRule {
    fn rule_id(&self) -> &'static str {
        "PINJ042"
    }

    fn description(&self) -> &'static str {
        "No unmarked calls to @injected functions from non-@injected contexts"
    }

    fn check(&mut self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();
        self.collect_injected_functions(context.python_module);

        if let Mod::Module(module) = context.python_module {
            for stmt in &module.body {
                self.check_stmt(stmt, context, &mut violations);
            }
        }

        violations
    }
}

use crate::rules::register;
register!(NoUnmarkedInjectedCallsRule);

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::RuleContext;

    fn check_code(code: &str) -> Vec<Violation> {
        let module = rustpython_parser::parse::parse_program(code, Default::default())
            .expect("Failed to parse code");

        let python_module = Mod::Module(module);
        let context = RuleContext {
            source: code,
            file_path: "test.py",
            python_module: &python_module,
            severity: Severity::Error,
        };

        let mut rule = NoUnmarkedInjectedCallsRule::new();
        rule.check(&context)
    }

    #[test]
    fn test_unmarked_call_from_regular_function() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

def regular():
    service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_marked_call_with_explicit_comment() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

def regular():
    service("x")  # pinjected: explicit-call
"#;
        let violations = check_code(code);
        assert!(violations.is_empty());
    }

    #[test]
    fn test_marked_call_with_noqa() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

def regular():
    service("x")  # noqa: PINJ042
"#;
        let violations = check_code(code);
        assert!(violations.is_empty());
    }

    #[test]
    fn test_call_from_class_method() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

class C:
    def m(self):
        service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_call_inside_injected_function() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

@injected
def inner(service, /):
    service("x")
"#;
        let violations = check_code(code);
        assert!(violations.is_empty());
    }

    #[test]
    fn test_nested_function_call() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

def outer():
    def inner():
        service("x")
    inner()
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_lambda_call() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

f = lambda x: service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_module_level_bare_iproxy_typed_assignment() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def service(dep, /, arg): ...

x: IProxy = service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_module_level_iproxy_subscript_typed_assignment() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def service(dep, /, arg): ...

x: IProxy[str] = service("x")
"#;
        let violations = check_code(code);
        assert!(violations.is_empty());
    }

    #[test]
    fn test_module_level_non_iproxy_assignment() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

x = service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_module_level_with_wrong_type_annotation() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def service(dep, /, arg): ...

x: OtherProxy[int] = service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_module_level_pinjected_iproxy_with_type() {
        let code = r#"
import pinjected
from pinjected import injected

@injected
def service(dep, /, arg): ...

x: pinjected.IProxy[int] = service("x")
"#;
        let violations = check_code(code);
        assert!(violations.is_empty());
    }

    #[test]
    fn test_module_level_bare_pinjected_iproxy() {
        let code = r#"
import pinjected
from pinjected import injected

@injected
def service(dep, /, arg): ...

x: pinjected.IProxy = service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_non_module_level_remains_unchanged() {
        let code = r#"
from pinjected import injected

@injected
def service(dep, /, arg): ...

def wrapper():
    x: IProxy[int] = service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_pytest_function_call() {
        let code = r#"
import pytest
from pinjected import injected

@injected
def service(dep, /, arg): ...

@pytest.mark.asyncio
def test_service():
    service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_pytest_function_with_await() {
        let code = r#"
import pytest
from pinjected import injected

@injected
def service(dep, /, arg): ...

@pytest.mark.asyncio
async def test_service():
    service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_pytest_function_with_explicit_call() {
        let code = r#"
import pytest
from pinjected import injected

@injected
def service(dep, /, arg): ...

def test_service():
    service("x")  # pinjected: explicit-call
"#;
        let violations = check_code(code);
        assert!(violations.is_empty());
    }

    #[test]
    fn test_pytest_decorator_function() {
        let code = r#"
import pytest
from pinjected import injected

@injected
def service(dep, /, arg): ...

@pytest.mark.parametrize("x", [1, 2, 3])
def test_service(x):
    service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }

    #[test]
    fn test_non_test_function_in_test_file() {
        let code = r#"
# test file but function doesn't start with test_
from pinjected import injected

@injected
def service(dep, /, arg): ...

def not_a_test():
    service("x")
"#;
        let violations = check_code(code);
        assert!(!violations.is_empty());
    }
}
