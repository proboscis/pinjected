//! PINJ009: No direct calls to @injected functions
//!
//! Inside @injected functions, you're building a dependency graph (AST),
//! not executing code. Direct calls to other @injected functions are
//! fundamentally wrong - they should be declared as dependencies and
//! injected, not called directly.
//!
//! This rule replaces both the old PINJ008 and PINJ009, covering:
//! - Direct function calls to @injected functions
//! - Await calls to @injected functions  
//! - Any form of execution of @injected functions
//! - Cross-module @injected function calls (imported functions)

use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_injected_decorator, has_injected_decorator_async};
use rustpython_ast::{Expr, ExprCall, Mod, Stmt};
use rustpython_parser::{parse, Mode};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, OnceLock};

/// Global cache for imported @injected functions
/// Maps: (module_path, function_name) -> is_injected
static IMPORT_CACHE: OnceLock<Arc<Mutex<HashMap<(String, String), bool>>>> = OnceLock::new();

fn get_import_cache() -> Arc<Mutex<HashMap<(String, String), bool>>> {
    IMPORT_CACHE
        .get_or_init(|| Arc::new(Mutex::new(HashMap::new())))
        .clone()
}

pub struct NoDirectInjectedCallsRule {
    /// All @injected function names in the module
    injected_functions: HashSet<String>,
    /// Imported functions that are @injected (name -> module_path)
    imported_injected_functions: HashMap<String, String>,
    /// Current function context
    current_function: Option<String>,
    /// Dependencies of current function (parameters before /)
    current_dependencies: HashSet<String>,
    /// Whether current function is @injected
    in_injected_function: bool,
}

impl NoDirectInjectedCallsRule {
    pub fn new() -> Self {
        Self {
            injected_functions: HashSet::new(),
            imported_injected_functions: HashMap::new(),
            current_function: None,
            current_dependencies: HashSet::new(),
            in_injected_function: false,
        }
    }

    /// Resolve module path from import statement
    fn resolve_module_path(module_name: &str, current_file: &str) -> Option<PathBuf> {
        // Get the directory of the current file
        let current_dir = Path::new(current_file).parent()?;

        // Convert module name to file path (e.g., "module_a" -> "module_a.py")
        let module_file = format!("{}.py", module_name.replace('.', "/"));

        // Try to find the module relative to current file
        let relative_path = current_dir.join(&module_file);
        if relative_path.exists() {
            return Some(relative_path);
        }

        // Try parent directories (basic Python path resolution)
        let mut parent = current_dir;
        while let Some(p) = parent.parent() {
            let path = p.join(&module_file);
            if path.exists() {
                return Some(path);
            }
            parent = p;
        }

        None
    }

    /// Check if a function in a module is @injected
    fn is_function_injected(module_path: &Path, function_name: &str) -> bool {
        let cache_key = (
            module_path.to_string_lossy().to_string(),
            function_name.to_string(),
        );

        // Check cache first
        let cache = get_import_cache();
        if let Ok(cache_guard) = cache.lock() {
            if let Some(&is_injected) = cache_guard.get(&cache_key) {
                return is_injected;
            }
        }

        // Parse the module to check if function is @injected
        let is_injected = if let Ok(content) = fs::read_to_string(module_path) {
            if let Ok(ast) = parse(&content, Mode::Module, module_path.to_str().unwrap()) {
                match &ast {
                    Mod::Module(module) => {
                        for stmt in &module.body {
                            match stmt {
                                Stmt::FunctionDef(func) => {
                                    if func.name.as_str() == function_name {
                                        return has_injected_decorator(func);
                                    }
                                }
                                Stmt::AsyncFunctionDef(func) => {
                                    if func.name.as_str() == function_name {
                                        return has_injected_decorator_async(func);
                                    }
                                }
                                _ => {}
                            }
                        }
                    }
                    _ => {}
                }
            }
            false
        } else {
            false
        };

        // Cache the result
        if let Ok(mut cache_guard) = cache.lock() {
            cache_guard.insert(cache_key, is_injected);
        }

        is_injected
    }

    /// Process import statements to track imported @injected functions
    fn process_imports(&mut self, ast: &Mod, file_path: &str) {
        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    match stmt {
                        Stmt::ImportFrom(import_from) => {
                            if let Some(module_name) = &import_from.module {
                                // Resolve the module path
                                if let Some(module_path) =
                                    Self::resolve_module_path(module_name.as_str(), file_path)
                                {
                                    // Check each imported name
                                    for alias in &import_from.names {
                                        let imported_name = alias.name.as_str();
                                        let local_name = alias
                                            .asname
                                            .as_ref()
                                            .map(|s| s.as_str())
                                            .unwrap_or(imported_name);

                                        // Check if this function is @injected
                                        if Self::is_function_injected(&module_path, imported_name) {
                                            self.imported_injected_functions.insert(
                                                local_name.to_string(),
                                                module_name.to_string(),
                                            );
                                        }
                                    }
                                }
                            }
                        }
                        _ => {}
                    }
                }
            }
            _ => {}
        }
    }

    /// Collect all @injected functions in the module
    fn collect_injected_functions(&mut self, ast: &Mod) {
        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.collect_from_stmt(stmt);
                }
            }
            _ => {}
        }
    }

    fn collect_from_stmt(&mut self, stmt: &Stmt) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    self.injected_functions.insert(func.name.to_string());
                }
                // Check nested functions
                for stmt in &func.body {
                    self.collect_from_stmt(stmt);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    self.injected_functions.insert(func.name.to_string());
                }
                // Check nested functions
                for stmt in &func.body {
                    self.collect_from_stmt(stmt);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.collect_from_stmt(stmt);
                }
            }
            _ => {}
        }
    }

    /// Extract dependency names from function (parameters before slash)
    fn extract_dependencies(&self, func: &rustpython_ast::StmtFunctionDef) -> HashSet<String> {
        let mut dependencies = HashSet::new();

        // In Python AST, posonlyargs are the parameters before the slash
        for arg in &func.args.posonlyargs {
            dependencies.insert(arg.def.arg.to_string());
        }

        dependencies
    }

    /// Extract dependency names from async function
    fn extract_dependencies_async(
        &self,
        func: &rustpython_ast::StmtAsyncFunctionDef,
    ) -> HashSet<String> {
        let mut dependencies = HashSet::new();

        // In Python AST, posonlyargs are the parameters before the slash
        for arg in &func.args.posonlyargs {
            dependencies.insert(arg.def.arg.to_string());
        }

        dependencies
    }

    /// Check if a call is to an @injected function
    fn check_call(&self, call: &ExprCall, file_path: &str, violations: &mut Vec<Violation>) {
        // Skip if we're not inside an @injected function
        if !self.in_injected_function {
            return;
        }

        // Get the function name being called
        let func_name = match &*call.func {
            Expr::Name(name) => Some(name.id.to_string()),
            Expr::Attribute(attr) => {
                // Handle cases like obj.method()
                if let Expr::Name(name) = &*attr.value {
                    Some(name.id.to_string())
                } else {
                    None
                }
            }
            _ => None,
        };

        if let Some(called_func) = func_name {
            // Check if this is a call to an @injected function (local or imported)
            let is_injected = self.injected_functions.contains(&called_func)
                || self.imported_injected_functions.contains_key(&called_func);

            if is_injected {
                // Check if it's declared as a dependency
                if !self.current_dependencies.contains(&called_func) {
                    let source =
                        if let Some(module) = self.imported_injected_functions.get(&called_func) {
                            format!(" (imported from '{}')", module)
                        } else {
                            String::new()
                        };

                    violations.push(Violation {
                        rule_id: "PINJ009".to_string(),
                        message: format!(
                            "@injected function '{}' makes a direct call to @injected function '{}{}'. Inside @injected functions, you're building a dependency graph, not executing code. Declare '{}' as a dependency (before '/') instead.",
                            self.current_function.as_ref().unwrap(),
                            called_func,
                            source,
                            called_func
                        ),
                        offset: call.range.start().to_usize(),
                        file_path: file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
            }
        }
    }

    /// Check expressions for calls
    fn check_expr(&self, expr: &Expr, file_path: &str, violations: &mut Vec<Violation>) {
        match expr {
            Expr::Call(call) => {
                self.check_call(call, file_path, violations);
                // Check arguments
                for arg in &call.args {
                    self.check_expr(arg, file_path, violations);
                }
            }
            // Check await expressions specifically
            Expr::Await(await_expr) => {
                // Special handling for await of @injected functions
                if let Expr::Call(call) = &*await_expr.value {
                    // Get the function name being awaited
                    let func_name = match &*call.func {
                        Expr::Name(name) => Some(name.id.to_string()),
                        _ => None,
                    };

                    if let Some(called_func) = func_name {
                        let is_injected = self.injected_functions.contains(&called_func)
                            || self.imported_injected_functions.contains_key(&called_func);

                        if is_injected && self.in_injected_function {
                            if !self.current_dependencies.contains(&called_func) {
                                let source = if let Some(module) =
                                    self.imported_injected_functions.get(&called_func)
                                {
                                    format!(" (imported from '{}')", module)
                                } else {
                                    String::new()
                                };

                                violations.push(Violation {
                                    rule_id: "PINJ009".to_string(),
                                    message: format!(
                                        "@injected function '{}' uses 'await' on a call to @injected function '{}{}'. Inside @injected functions, you're building a dependency graph, not executing code. Declare '{}' as a dependency (before '/') instead.",
                                        self.current_function.as_ref().unwrap(),
                                        called_func,
                                        source,
                                        called_func
                                    ),
                                    offset: await_expr.range.start().to_usize(),
                                    file_path: file_path.to_string(),
                                    severity: Severity::Error,
                                    fix: None,
                                });
                            }
                        }
                    }
                }
                self.check_expr(&await_expr.value, file_path, violations);
            }
            // Recurse into other expression types
            Expr::BinOp(binop) => {
                self.check_expr(&binop.left, file_path, violations);
                self.check_expr(&binop.right, file_path, violations);
            }
            Expr::UnaryOp(unaryop) => {
                self.check_expr(&unaryop.operand, file_path, violations);
            }
            Expr::Lambda(lambda) => {
                self.check_expr(&lambda.body, file_path, violations);
            }
            Expr::IfExp(ifexp) => {
                self.check_expr(&ifexp.test, file_path, violations);
                self.check_expr(&ifexp.body, file_path, violations);
                self.check_expr(&ifexp.orelse, file_path, violations);
            }
            Expr::Dict(dict) => {
                for key in &dict.keys {
                    if let Some(k) = key {
                        self.check_expr(k, file_path, violations);
                    }
                }
                for value in &dict.values {
                    self.check_expr(value, file_path, violations);
                }
            }
            Expr::Set(set) => {
                for elem in &set.elts {
                    self.check_expr(elem, file_path, violations);
                }
            }
            Expr::ListComp(comp) => {
                self.check_expr(&comp.elt, file_path, violations);
            }
            Expr::SetComp(comp) => {
                self.check_expr(&comp.elt, file_path, violations);
            }
            Expr::DictComp(comp) => {
                self.check_expr(&comp.key, file_path, violations);
                self.check_expr(&comp.value, file_path, violations);
            }
            Expr::GeneratorExp(comp) => {
                self.check_expr(&comp.elt, file_path, violations);
            }
            Expr::Yield(yield_expr) => {
                if let Some(value) = &yield_expr.value {
                    self.check_expr(value, file_path, violations);
                }
            }
            Expr::YieldFrom(yieldfrom) => {
                self.check_expr(&yieldfrom.value, file_path, violations);
            }
            Expr::Compare(compare) => {
                self.check_expr(&compare.left, file_path, violations);
                for comp in &compare.comparators {
                    self.check_expr(comp, file_path, violations);
                }
            }
            Expr::List(list) => {
                for elem in &list.elts {
                    self.check_expr(elem, file_path, violations);
                }
            }
            Expr::Tuple(tuple) => {
                for elem in &tuple.elts {
                    self.check_expr(elem, file_path, violations);
                }
            }
            Expr::Subscript(subscript) => {
                self.check_expr(&subscript.value, file_path, violations);
                self.check_expr(&subscript.slice, file_path, violations);
            }
            Expr::Starred(starred) => {
                self.check_expr(&starred.value, file_path, violations);
            }
            Expr::Attribute(attr) => {
                self.check_expr(&attr.value, file_path, violations);
            }
            _ => {}
        }
    }

    /// Check statements for calls
    fn check_stmt(&mut self, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                if has_injected_decorator(func) {
                    // Enter @injected function context
                    let old_func = self.current_function.take();
                    let old_deps = self.current_dependencies.clone();
                    let old_in_injected = self.in_injected_function;

                    self.current_function = Some(func.name.to_string());
                    self.current_dependencies = self.extract_dependencies(func);
                    self.in_injected_function = true;

                    // Check function body
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }

                    // Restore context
                    self.current_function = old_func;
                    self.current_dependencies = old_deps;
                    self.in_injected_function = old_in_injected;
                } else {
                    // Check nested functions
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if has_injected_decorator_async(func) {
                    // Enter @injected function context
                    let old_func = self.current_function.take();
                    let old_deps = self.current_dependencies.clone();
                    let old_in_injected = self.in_injected_function;

                    self.current_function = Some(func.name.to_string());
                    self.current_dependencies = self.extract_dependencies_async(func);
                    self.in_injected_function = true;

                    // Check function body
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }

                    // Restore context
                    self.current_function = old_func;
                    self.current_dependencies = old_deps;
                    self.in_injected_function = old_in_injected;
                } else {
                    // Check nested functions
                    for stmt in &func.body {
                        self.check_stmt(stmt, file_path, violations);
                    }
                }
            }
            Stmt::ClassDef(class) => {
                for stmt in &class.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::Return(ret) => {
                if let Some(value) = &ret.value {
                    self.check_expr(value, file_path, violations);
                }
            }
            Stmt::Delete(del) => {
                for target in &del.targets {
                    self.check_expr(target, file_path, violations);
                }
            }
            Stmt::Assign(assign) => {
                self.check_expr(&assign.value, file_path, violations);
                for target in &assign.targets {
                    self.check_expr(target, file_path, violations);
                }
            }
            Stmt::AugAssign(augassign) => {
                self.check_expr(&augassign.value, file_path, violations);
                self.check_expr(&augassign.target, file_path, violations);
            }
            Stmt::AnnAssign(annassign) => {
                if let Some(value) = &annassign.value {
                    self.check_expr(value, file_path, violations);
                }
            }
            Stmt::For(for_stmt) => {
                self.check_expr(&for_stmt.iter, file_path, violations);
                for stmt in &for_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::AsyncFor(for_stmt) => {
                self.check_expr(&for_stmt.iter, file_path, violations);
                for stmt in &for_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &for_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::While(while_stmt) => {
                self.check_expr(&while_stmt.test, file_path, violations);
                for stmt in &while_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &while_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::If(if_stmt) => {
                self.check_expr(&if_stmt.test, file_path, violations);
                for stmt in &if_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &if_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::With(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(&item.context_expr, file_path, violations);
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::AsyncWith(with_stmt) => {
                for item in &with_stmt.items {
                    self.check_expr(&item.context_expr, file_path, violations);
                }
                for stmt in &with_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::Raise(raise_stmt) => {
                if let Some(exc) = &raise_stmt.exc {
                    self.check_expr(exc, file_path, violations);
                }
                if let Some(cause) = &raise_stmt.cause {
                    self.check_expr(cause, file_path, violations);
                }
            }
            Stmt::Try(try_stmt) => {
                for stmt in &try_stmt.body {
                    self.check_stmt(stmt, file_path, violations);
                }
                for handler in &try_stmt.handlers {
                    match handler {
                        rustpython_ast::ExceptHandler::ExceptHandler(h) => {
                            for stmt in &h.body {
                                self.check_stmt(stmt, file_path, violations);
                            }
                        }
                    }
                }
                for stmt in &try_stmt.orelse {
                    self.check_stmt(stmt, file_path, violations);
                }
                for stmt in &try_stmt.finalbody {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::Assert(assert_stmt) => {
                self.check_expr(&assert_stmt.test, file_path, violations);
                if let Some(msg) = &assert_stmt.msg {
                    self.check_expr(msg, file_path, violations);
                }
            }
            Stmt::Expr(expr_stmt) => {
                self.check_expr(&expr_stmt.value, file_path, violations);
            }
            _ => {}
        }
    }
}

impl LintRule for NoDirectInjectedCallsRule {
    fn rule_id(&self) -> &str {
        "PINJ009"
    }

    fn description(&self) -> &str {
        "No direct calls to @injected functions inside other @injected functions"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        // Create a mutable instance for stateful tracking
        let mut checker = NoDirectInjectedCallsRule::new();

        // First pass: collect all @injected functions and process imports
        checker.collect_injected_functions(context.ast);
        checker.process_imports(context.ast, context.file_path);

        // If no @injected functions (local or imported), nothing to check
        if checker.injected_functions.is_empty() && checker.imported_injected_functions.is_empty() {
            return violations;
        }

        // Second pass: check the current statement
        checker.check_stmt(context.stmt, context.file_path, &mut violations);

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_ast::Mod;
    use rustpython_parser::{parse, Mode};
    use std::fs;
    use tempfile::TempDir;

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = NoDirectInjectedCallsRule::new();
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
    fn test_direct_call_without_dependency() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data: str) -> str:
    # pinjected: no dependencies
    return data.upper()

@injected
def analyze_results(results):
    # pinjected: no dependencies
    # Direct call without declaring as dependency
    processed = process_data(results)
    return processed
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ009");
        assert!(violations[0].message.contains("direct call"));
        assert_eq!(violations[0].severity, Severity::Error);
    }

    #[test]
    fn test_await_call_without_dependency() {
        let code = r#"
from pinjected import injected

@injected
async def a_process_data(data: str) -> str:
    # pinjected: no dependencies
    return data.upper()

@injected
async def a_analyze_results(results):
    # pinjected: no dependencies
    # Await call without declaring as dependency
    processed = await a_process_data(results)
    return processed
"#;
        let violations = check_code(code);
        // Should have 2 violations: one for direct call, one for await
        assert_eq!(violations.len(), 2);

        // Check that we have both types of violations
        let has_await_violation = violations
            .iter()
            .any(|v| v.message.contains("uses 'await'"));
        let has_direct_call_violation =
            violations.iter().any(|v| v.message.contains("direct call"));

        assert!(has_await_violation, "Should have await violation");
        assert!(
            has_direct_call_violation,
            "Should have direct call violation"
        );

        // All violations should be PINJ009 errors
        for v in &violations {
            assert_eq!(v.rule_id, "PINJ009");
            assert_eq!(v.severity, Severity::Error);
        }
    }

    #[test]
    fn test_call_with_dependency_declared() {
        let code = r#"
from pinjected import injected

@injected
def process_data(data: str) -> str:
    # pinjected: no dependencies
    return data.upper()

@injected
def analyze_results(process_data, /, results):
    # OK - process_data is declared as dependency
    return process_data(results)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_await_with_dependency_declared() {
        let code = r#"
from pinjected import injected

@injected
async def a_process_data(data: str) -> str:
    # pinjected: no dependencies
    return data.upper()

@injected
async def a_analyze_results(a_process_data, /, results):
    # This is still wrong - shouldn't await even with dependency
    # But if we're checking for declaration, this passes
    return a_process_data(results)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_non_injected_function_calls() {
        let code = r#"
from pinjected import injected

def regular_function(data):
    return data.upper()

@injected
def process_data(data):
    # pinjected: no dependencies
    # OK - regular_function is not @injected
    result = regular_function(data)
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_nested_calls() {
        let code = r#"
from pinjected import injected

@injected
def helper(data):
    # pinjected: no dependencies
    return data

@injected
def process(data):
    # pinjected: no dependencies
    # Nested call expression
    result = len(helper(data))
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ009");
    }

    #[test]
    fn test_cross_module_injected_call() {
        // Create a temporary directory for test files
        let temp_dir = TempDir::new().unwrap();

        // Create module_a.py with @injected function
        let module_a_path = temp_dir.path().join("module_a.py");
        fs::write(
            &module_a_path,
            r#"
from pinjected import injected

@injected
def helper_function():
    return "helper result"

@injected
async def a_async_helper():
    return "async helper result"

def regular_function():
    return "regular result"
"#,
        )
        .unwrap();

        // Create module_b.py that imports and calls functions from module_a
        let module_b_path = temp_dir.path().join("module_b.py");
        let module_b_content = r#"
from pinjected import injected
from module_a import helper_function, a_async_helper, regular_function

@injected
def process_data():
    # ERROR: Direct call to imported @injected function
    result = helper_function()
    return result

@injected
async def a_process_async():
    # ERROR: Await call to imported @injected function
    result = await a_async_helper()
    return result

@injected
def correct_usage(helper_function, /):
    # OK: helper_function is declared as dependency
    return helper_function()

@injected
def call_regular():
    # OK: regular_function is not @injected
    return regular_function()
"#;
        fs::write(&module_b_path, module_b_content).unwrap();

        // Parse and check module_b
        let ast = parse(
            module_b_content,
            Mode::Module,
            module_b_path.to_str().unwrap(),
        )
        .unwrap();
        let rule = NoDirectInjectedCallsRule::new();
        let mut violations = Vec::new();

        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    let context = RuleContext {
                        stmt,
                        file_path: module_b_path.to_str().unwrap(),
                        source: module_b_content,
                        ast: &ast,
                    };
                    violations.extend(rule.check(&context));
                }
            }
            _ => {}
        }

        // Should have violations for cross-module calls
        assert!(
            violations.len() >= 2,
            "Should detect cross-module @injected calls"
        );

        // Check that violations mention the imported module
        let has_import_mention = violations
            .iter()
            .any(|v| v.message.contains("imported from"));
        assert!(
            has_import_mention,
            "Violations should mention the import source"
        );
    }
}
