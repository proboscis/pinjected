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

/// Global cache for imported @injected functions (shared with PINJ009)
/// Maps: (module_path, function_name) -> is_injected
static IMPORT_CACHE: OnceLock<Arc<Mutex<HashMap<(String, String), bool>>>> = OnceLock::new();

fn get_import_cache() -> Arc<Mutex<HashMap<(String, String), bool>>> {
    IMPORT_CACHE
        .get_or_init(|| Arc::new(Mutex::new(HashMap::new())))
        .clone()
}

pub struct NoUnmarkedInjectedCallsRule {
    /// All @injected function names in the module
    injected_functions: HashSet<String>,
    /// Imported functions that are @injected (name -> module_path)
    imported_injected_functions: HashMap<String, String>,
    /// Whether we're currently inside an @injected function
    in_injected_function: bool,
    /// Stack to track nested function contexts
    function_stack: Vec<bool>,
}

impl NoUnmarkedInjectedCallsRule {
    pub fn new() -> Self {
        Self {
            injected_functions: HashSet::new(),
            imported_injected_functions: HashMap::new(),
            in_injected_function: false,
            function_stack: Vec::new(),
        }
    }

    /// Collect all @injected functions in the module
    fn collect_injected_functions(&mut self, module: &Mod) {
        if let Mod::Module(module) = module {
            for stmt in &module.body {
                self.collect_from_stmt(stmt);
            }
        }
    }

    fn collect_from_stmt(&mut self, stmt: &Stmt) {
        match stmt {
            Stmt::Import(import) => {
                for alias in &import.names {
                    // Handle imports like "from module import func"
                    if let Some(module_path) = self.resolve_import_path(&alias.name) {
                        // We'll check if imported functions are @injected when we see them called
                        // For now, just note the import
                    }
                }
            }
            Stmt::ImportFrom(import_from) => {
                if let Some(module) = &import_from.module {
                    for alias in &import_from.names {
                        let func_name = alias.asname.as_ref().unwrap_or(&alias.name);
                        // Store potential @injected imports for later checking
                        self.imported_injected_functions
                            .insert(func_name.to_string(), module.to_string());
                    }
                }
            }
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

    /// Resolve module path from import statement
    fn resolve_import_path(&self, module_name: &str) -> Option<String> {
        // Simplified - in real implementation would resolve actual paths
        Some(module_name.to_string())
    }

    /// Check if imported function is @injected (simplified version)
    fn is_imported_function_injected(&self, func_name: &str, module: &str) -> bool {
        // In a real implementation, this would check the actual module file
        // For now, we'll use a cache and assume checking is done elsewhere
        let cache_key = (module.to_string(), func_name.to_string());
        
        if let Ok(cache) = get_import_cache().lock() {
            if let Some(&is_injected) = cache.get(&cache_key) {
                return is_injected;
            }
        }
        
        // Default to false if we can't determine
        false
    }

    /// Check if a line has explicit marking for @injected call
    fn has_explicit_marking(&self, source: &str, offset: usize) -> bool {
        // Find the line containing this offset
        let lines: Vec<&str> = source.lines().collect();
        let mut current_offset = 0;
        
        for line in lines {
            let line_end = current_offset + line.len() + 1; // +1 for newline
            if offset >= current_offset && offset < line_end {
                // Check for explicit markings
                return line.contains("# pinjected: explicit-call") 
                    || line.contains("# noqa: PINJ042");
            }
            current_offset = line_end;
        }
        
        false
    }

    /// Check if a call is to an @injected function and not properly marked
    fn check_call(&self, call: &ExprCall, context: &RuleContext, violations: &mut Vec<Violation>) {
        // Skip if we're inside an @injected function (PINJ009 handles this)
        if self.in_injected_function {
            return;
        }

        // Get the function name being called
        let func_name = match &*call.func {
            Expr::Name(name) => Some(name.id.to_string()),
            Expr::Attribute(attr) => {
                // Handle method calls - we don't check these for now
                None
            }
            _ => None,
        };

        if let Some(called_func) = func_name {
            // Check if this is a call to an @injected function
            let is_local_injected = self.injected_functions.contains(&called_func);
            let is_imported_injected = if let Some(module) = self.imported_injected_functions.get(&called_func) {
                self.is_imported_function_injected(&called_func, module)
            } else {
                false
            };

            if is_local_injected || is_imported_injected {
                // Check if the call has explicit marking
                if !self.has_explicit_marking(context.source, call.range.start().to_usize()) {
                    let source_info = if is_imported_injected {
                        if let Some(module) = self.imported_injected_functions.get(&called_func) {
                            format!(" (imported from '{}')", module)
                        } else {
                            String::new()
                        }
                    } else {
                        String::new()
                    };

                    violations.push(Violation {
                        rule_id: "PINJ042".to_string(),
                        message: format!(
                            "Calling @injected function '{}'{} directly returns an IProxy, not the actual function!\n\n\
                            WHY THIS IS FORBIDDEN:\n\
                            - @injected functions return IProxy objects when called directly\n\
                            - They are NOT meant to be executed without dependency resolution\n\
                            - Only resolved functions (through DI) can be called with runtime arguments\n\n\
                            CORRECT APPROACH:\n\
                            1. Use dependency injection: Declare '{}' as a dependency in an @injected function\n\
                            2. Use Design().run() or similar DI execution methods\n\n\
                            ONLY IF ABSOLUTELY NECESSARY (rare cases like tests/migration):\n\
                            Add this comment to the line: # pinjected: explicit-call\n\
                            Example: result = {}(args)  # pinjected: explicit-call",
                            called_func,
                            source_info,
                            called_func,
                            called_func
                        ),
                        offset: call.range.start().to_usize(),
                        file_path: context.file_path.to_string(),
                        severity: Severity::Error,
                        fix: None,
                    });
                }
            }
        }
    }

    /// Check expressions recursively for function calls
    fn check_expr(&self, expr: &Expr, context: &RuleContext, violations: &mut Vec<Violation>) {
        match expr {
            Expr::Call(call) => {
                self.check_call(call, context, violations);
                // Check arguments
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

    /// Check a statement and track function context
    fn check_stmt(&mut self, stmt: &Stmt, context: &RuleContext, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                let was_injected = has_injected_decorator(func);
                self.function_stack.push(self.in_injected_function);
                self.in_injected_function = was_injected;
                
                // Check function body
                for stmt in &func.body {
                    self.check_stmt(stmt, context, violations);
                }
                
                // Restore context
                self.in_injected_function = self.function_stack.pop().unwrap_or(false);
            }
            Stmt::AsyncFunctionDef(func) => {
                let was_injected = has_injected_decorator_async(func);
                self.function_stack.push(self.in_injected_function);
                self.in_injected_function = was_injected;
                
                // Check function body
                for stmt in &func.body {
                    self.check_stmt(stmt, context, violations);
                }
                
                // Restore context
                self.in_injected_function = self.function_stack.pop().unwrap_or(false);
            }
            Stmt::ClassDef(class) => {
                // Check methods
                for stmt in &class.body {
                    self.check_stmt(stmt, context, violations);
                }
            }
            Stmt::Expr(expr_stmt) => {
                self.check_expr(&expr_stmt.value, context, violations);
            }
            Stmt::Assign(assign) => {
                self.check_expr(&assign.value, context, violations);
            }
            Stmt::AnnAssign(ann_assign) => {
                if let Some(value) = &ann_assign.value {
                    self.check_expr(value, context, violations);
                }
            }
            Stmt::Return(ret) => {
                if let Some(value) = &ret.value {
                    self.check_expr(value, context, violations);
                }
            }
            Stmt::If(if_stmt) => {
                self.check_expr(&if_stmt.test, context, violations);
                for stmt in &if_stmt.body {
                    self.check_stmt(stmt, context, violations);
                }
                for stmt in &if_stmt.orelse {
                    self.check_stmt(stmt, context, violations);
                }
            }
            Stmt::For(for_stmt) => {
                self.check_expr(&for_stmt.iter, context, violations);
                for stmt in &for_stmt.body {
                    self.check_stmt(stmt, context, violations);
                }
            }
            _ => {}
        }
    }
}

impl LintRule for NoUnmarkedInjectedCallsRule {
    fn rule_id(&self) -> &str {
        "PINJ042"
    }

    fn description(&self) -> &str {
        "Forbid unmarked calls to @injected functions from non-@injected contexts"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        // Create a mutable instance to track state
        let mut checker = NoUnmarkedInjectedCallsRule::new();
        
        // First pass: collect all @injected functions from the entire module
        checker.collect_injected_functions(context.ast);
        
        // Process imported functions to check if they're @injected
        // For now, we'll check the specific imports we know about
        let mut imports_to_check = Vec::new();
        for (func_name, module) in &checker.imported_injected_functions {
            imports_to_check.push((func_name.clone(), module.clone()));
        }
        
        // Mark known @injected imports (simplified for now)
        for (func_name, _module) in imports_to_check {
            // In a real implementation, we'd check the actual module
            // For testing, assume imports from current module are @injected
            if func_name == "external_service" {
                // Keep it in imported_injected_functions
            }
        }
        
        // If no @injected functions (local or imported), nothing to check
        if checker.injected_functions.is_empty() && checker.imported_injected_functions.is_empty() {
            return violations;
        }
        
        
        // Second pass: check the current statement for violations
        checker.check_stmt(context.stmt, context, &mut violations);
        
        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_parser::{parse, Mode};

    fn check_code(code: &str) -> Vec<Violation> {
        let ast = parse(code, Mode::Module, "test.py").unwrap();
        let rule = NoUnmarkedInjectedCallsRule::new();
        let mut violations = Vec::new();

        if let Mod::Module(module) = &ast {
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

        violations
    }

    #[test]
    fn test_unmarked_call_from_regular_function() {
        let code = r#"
from pinjected import injected

@injected
def service(logger, /, data):
    return data.upper()

def regular_function(data):
    # This should be detected - no marking
    result = service(data)
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("service"));
        assert!(violations[0].message.contains("returns an IProxy"));
        assert!(violations[0].message.contains("WHY THIS IS FORBIDDEN"));
        assert!(violations[0].message.contains("explicit-call"));
    }

    #[test]
    fn test_marked_call_with_explicit_comment() {
        let code = r#"
from pinjected import injected

@injected
def service(logger, /, data):
    return data.upper()

def regular_function(data):
    # This should be OK - has explicit marking
    result = service(data)  # pinjected: explicit-call
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_marked_call_with_noqa() {
        let code = r#"
from pinjected import injected

@injected
def service(logger, /, data):
    return data.upper()

def regular_function(data):
    # This should be OK - has noqa
    result = service(data)  # noqa: PINJ042
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_call_from_class_method() {
        let code = r#"
from pinjected import injected

@injected
def processor(logger):
    # pinjected: dependency is logger
    def inner(data):
        return data
    return inner

class Handler:
    def process(self, data):
        # This should be detected
        return processor(data)
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
    }

    #[test]
    fn test_call_inside_injected_function() {
        let code = r#"
from pinjected import injected

@injected
def service_a(logger):
    # pinjected: dependency is logger
    return lambda data: data.upper()

@injected
def service_b(service_a):
    # This should NOT be detected by PINJ042 (PINJ009 handles this)
    # Direct call in @injected function body
    result = service_a("test")
    return result
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0); // PINJ042 should not trigger
    }

    #[test]
    fn test_nested_function_call() {
        let code = r#"
from pinjected import injected

@injected
def service(logger):
    # pinjected: dependency is logger
    def inner(data):
        return data
    return inner

def outer():
    def inner(data):
        # This should be detected
        return service(data)
    return inner
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
    }

    #[test]
    fn test_lambda_call() {
        let code = r#"
from pinjected import injected

@injected
def transform(multiplier):
    # pinjected: dependency is multiplier
    def inner(x):
        return x * multiplier
    return inner

# This should be detected
data = list(map(lambda x: transform(x), [1, 2, 3]))
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
    }
}