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
    /// Whether we're at module level (not inside any function/class)
    is_module_level: bool,
    /// Track if current statement is an IProxy-typed assignment
    is_iproxy_assignment: bool,
    /// Whether we're currently inside a pytest test function
    in_pytest_function: bool,
    /// Stack to track nested pytest function contexts
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

    /// Check if a function is a pytest test function
    fn is_test_function(func_name: &str, decorator_list: &[Expr]) -> bool {
        // Check if function name starts with "test_"
        if func_name.starts_with("test_") {
            return true;
        }

        // Check for pytest decorators
        for decorator in decorator_list {
            if Self::is_pytest_decorator(decorator) {
                return true;
            }
        }

        false
    }

    /// Check if an expression is a pytest decorator that makes a function a test
    fn is_pytest_decorator(expr: &Expr) -> bool {
        match expr {
            Expr::Attribute(attr) => {
                // Check for pytest.mark.* decorators
                if let Expr::Attribute(inner_attr) = &*attr.value {
                    if let Expr::Name(name) = &*inner_attr.value {
                        return name.id.as_str() == "pytest" && inner_attr.attr.as_str() == "mark";
                    }
                }
                // Check for direct pytest.* decorators
                if let Expr::Name(name) = &*attr.value {
                    return name.id.as_str() == "pytest";
                }
                false
            }
            _ => false,
        }
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

    /// Check if a type annotation is IProxy with type parameter
    fn is_iproxy_annotation(&self, annotation: &Expr) -> bool {
        match annotation {
            // Reject bare IProxy - must have type parameter
            Expr::Name(_) => false,
            // Reject bare pinjected.IProxy - must have type parameter  
            Expr::Attribute(_) => false,
            Expr::Subscript(subscript) => {
                // Only accept IProxy[T] or pinjected.IProxy[T]
                if let Expr::Name(name) = &*subscript.value {
                    name.id.to_string() == "IProxy"
                } else if let Expr::Attribute(attr) = &*subscript.value {
                    // Handle pinjected.IProxy[SomeType]
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
                    // Skip if this is a module-level IProxy-typed assignment
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

                    // Context-aware error message
                    let message = if self.in_pytest_function {
                        format!(
                            "Calling @injected function '{}'{} directly in pytest test function!\n\n\
                            WHY THIS IS FORBIDDEN:\n\
                            - @injected functions return IProxy objects when called directly\n\
                            - In pytest, dependencies should be requested as fixtures, not called directly\n\
                            - Direct calls bypass pytest's dependency injection system\n\n\
                            CORRECT APPROACH FOR PYTEST:\n\
                            1. Use pytest fixtures: Declare '{}' as a fixture parameter\n\
                            2. Set up dependencies using @injected_pytest decorator\n\
                            3. Let pytest inject the resolved dependency\n\n\
                            EXAMPLE:\n\
                            # At module level:\n\
                            from pinjected import design\n\
                            from pinjected.test import injected_pytest\n\n\
                            test_design = design(\n\
                                {}={}(),\n\
                                # ... other dependencies\n\
                            )\n\n\
                            # In your test:\n\
                            @injected_pytest(test_design)\n\
                            def test_something({}, other_fixture):\n\
                                # {} is now the resolved function, not an IProxy\n\
                                result = {}(args)  # This works!\n\n\
                            NOTE ON BYPASSING THIS ERROR:\n\
                            While you can add '# pinjected: explicit-call' to suppress this error, this is PROBABLY WRONG\n\
                            and should NOT be done without supervisor's instruction. It's a complex feature that bypasses\n\
                            the dependency injection system and can lead to runtime errors.",
                            called_func,
                            source_info,
                            called_func,
                            called_func,
                            called_func,
                            called_func,
                            called_func,
                            called_func
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
                            # Or use Any if type is unknown\n\
                            my_entrypoint: IProxy[Any] = {}(\"args\")\n\n\
                            WHY TYPE PARAMETER IS REQUIRED:\n\
                            - Ensures proper type checking for dependency resolution\n\
                            - Makes the expected return type explicit\n\
                            - Prevents runtime type errors in the DI system\n\n\
                            If this is not meant to be an entrypoint, consider moving this call inside a function.\n\n\
                            NOTE ON BYPASSING THIS ERROR:\n\
                            While you can add '# pinjected: explicit-call' to suppress this error, this is PROBABLY WRONG\n\
                            and should NOT be done without supervisor's instruction. It's a complex feature that bypasses\n\
                            the dependency injection system and can lead to runtime errors.",
                            called_func,
                            source_info,
                            called_func,
                            called_func
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
                            called_func,
                            source_info,
                            called_func,
                            called_func,
                            called_func,
                            called_func,
                            called_func,
                            called_func,
                            called_func,
                            called_func
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
                let is_pytest = Self::is_test_function(&func.name, &func.decorator_list);
                
                // Push current states
                self.function_stack.push(self.in_injected_function);
                self.pytest_function_stack.push(self.in_pytest_function);
                
                // Update states
                self.in_injected_function = was_injected;
                self.in_pytest_function = is_pytest;
                let was_module_level = self.is_module_level;
                self.is_module_level = false;
                
                // Check function body
                for stmt in &func.body {
                    self.check_stmt(stmt, context, violations);
                }
                
                // Restore context
                self.in_injected_function = self.function_stack.pop().unwrap_or(false);
                self.in_pytest_function = self.pytest_function_stack.pop().unwrap_or(false);
                self.is_module_level = was_module_level;
            }
            Stmt::AsyncFunctionDef(func) => {
                let was_injected = has_injected_decorator_async(func);
                let is_pytest = Self::is_test_function(&func.name, &func.decorator_list);
                
                // Push current states
                self.function_stack.push(self.in_injected_function);
                self.pytest_function_stack.push(self.in_pytest_function);
                
                // Update states
                self.in_injected_function = was_injected;
                self.in_pytest_function = is_pytest;
                let was_module_level = self.is_module_level;
                self.is_module_level = false;
                
                // Check function body
                for stmt in &func.body {
                    self.check_stmt(stmt, context, violations);
                }
                
                // Restore context
                self.in_injected_function = self.function_stack.pop().unwrap_or(false);
                self.in_pytest_function = self.pytest_function_stack.pop().unwrap_or(false);
                self.is_module_level = was_module_level;
            }
            Stmt::ClassDef(class) => {
                let was_module_level = self.is_module_level;
                self.is_module_level = false;
                
                // Check methods
                for stmt in &class.body {
                    self.check_stmt(stmt, context, violations);
                }
                
                self.is_module_level = was_module_level;
            }
            Stmt::Expr(expr_stmt) => {
                self.check_expr(&expr_stmt.value, context, violations);
            }
            Stmt::Assign(assign) => {
                self.check_expr(&assign.value, context, violations);
            }
            Stmt::AnnAssign(ann_assign) => {
                // Check if this is an IProxy-typed assignment
                let has_iproxy_annotation = self.is_iproxy_annotation(&ann_assign.annotation);
                
                if let Some(value) = &ann_assign.value {
                    // Set the flag before checking the expression
                    let was_iproxy_assignment = self.is_iproxy_assignment;
                    self.is_iproxy_assignment = has_iproxy_annotation;
                    
                    self.check_expr(value, context, violations);
                    
                    // Restore the flag
                    self.is_iproxy_assignment = was_iproxy_assignment;
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
        assert!(violations[0].message.contains("CORRECT APPROACHES"));
        assert!(violations[0].message.contains("PROBABLY WRONG"));
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

    #[test]
    fn test_module_level_bare_iproxy_typed_assignment() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def a_ensure_namespace(namespace, /):
    return namespace

# This should be detected - bare IProxy without type parameter
run_test_ensure_namespace: IProxy = a_ensure_namespace("test-namespace2")
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("requires IProxy[T] type annotation"));
        assert!(violations[0].message.contains("IProxy[ServiceType]"));
    }

    #[test]
    fn test_module_level_iproxy_subscript_typed_assignment() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def service(db, logger, /):
    return db

# This should NOT be detected - module level with IProxy[T] type annotation
my_service: IProxy[Database] = service()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_module_level_non_iproxy_assignment() {
        let code = r#"
from pinjected import injected

@injected
def service(db, logger, /):
    return db

# This should be detected - module level without IProxy type annotation
my_service = service()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("Module-level call"));
        assert!(violations[0].message.contains("requires IProxy[T] type annotation"));
        assert!(violations[0].message.contains("IProxy[ServiceType]"));
    }

    #[test]
    fn test_module_level_with_wrong_type_annotation() {
        let code = r#"
from pinjected import injected

@injected
def service(db, logger, /):
    return db

# This should be detected - wrong type annotation (not IProxy)
my_service: str = service()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("Module-level call"));
    }

    #[test]
    fn test_module_level_pinjected_iproxy_with_type() {
        let code = r#"
from pinjected import injected
import pinjected

@injected
def service(db, logger, /):
    return db

# This should NOT be detected - pinjected.IProxy[T] is valid
my_service: pinjected.IProxy[Database] = service()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_module_level_bare_pinjected_iproxy() {
        let code = r#"
from pinjected import injected
import pinjected

@injected
def service(db, logger, /):
    return db

# This should be detected - bare pinjected.IProxy without type parameter
my_service: pinjected.IProxy = service()
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("requires IProxy[T] type annotation"));
    }

    #[test]
    fn test_non_module_level_remains_unchanged() {
        let code = r#"
from pinjected import injected, IProxy

@injected
def service(db, logger, /):
    return db

def regular_function():
    # This should still be detected - not at module level
    my_service: IProxy = service()
    return my_service
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        // Should get the non-module-level error message
        assert!(violations[0].message.contains("directly returns an IProxy"));
        assert!(violations[0].message.contains("Use dependency injection"));
        assert!(!violations[0].message.contains("Module-level call"));
    }

    #[test]
    fn test_pytest_function_call() {
        let code = r#"
from pinjected import injected

@injected
def a_create_test_backtest_config(db, logger, /):
    return {"db": db, "logger": logger}

def test_backtest_integration():
    # This should be detected with pytest-specific message
    config = a_create_test_backtest_config()
    assert config is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("directly in pytest test function"));
        assert!(violations[0].message.contains("dependencies should be requested as fixtures"));
        assert!(violations[0].message.contains("@injected_pytest"));
        assert!(violations[0].message.contains("CORRECT APPROACH FOR PYTEST"));
        assert!(violations[0].message.contains("PROBABLY WRONG"));
    }

    #[test]
    fn test_pytest_function_with_await() {
        let code = r#"
from pinjected import injected

@injected
async def a_create_test_backtest_config(db, logger, /):
    return {"db": db, "logger": logger}

async def test_async_backtest():
    # This should be detected with pytest-specific message
    config = await a_create_test_backtest_config()
    assert config is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("directly in pytest test function"));
        assert!(violations[0].message.contains("CORRECT APPROACH FOR PYTEST"));
        assert!(violations[0].message.contains("PROBABLY WRONG"));
    }

    #[test]
    fn test_pytest_function_with_explicit_call() {
        let code = r#"
from pinjected import injected

@injected
def a_create_test_backtest_config(db, logger, /):
    return {"db": db, "logger": logger}

def test_backtest_integration():
    # This should NOT be detected - has explicit marking
    config = a_create_test_backtest_config()  # pinjected: explicit-call
    assert config is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 0);
    }

    #[test]
    fn test_pytest_decorator_function() {
        let code = r#"
from pinjected import injected
import pytest

@injected
def service(db, /):
    return db

@pytest.mark.parametrize("input", [1, 2, 3])
def test_with_params(input):
    # This should be detected with pytest-specific message
    result = service()
    assert result is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        assert!(violations[0].message.contains("directly in pytest test function"));
        assert!(violations[0].message.contains("dependencies should be requested as fixtures"));
    }

    #[test]
    fn test_non_test_function_in_test_file() {
        let code = r#"
from pinjected import injected

@injected
def service(db, /):
    return db

def helper_function():
    # This should get the regular error message, not pytest-specific
    result = service()
    return result

def test_something():
    # This test doesn't directly call the injected function
    result = helper_function()
    assert result is not None
"#;
        let violations = check_code(code);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "PINJ042");
        // Should get regular error message for helper_function
        assert!(violations[0].message.contains("directly returns an IProxy"));
        assert!(!violations[0].message.contains("pytest test function"));
    }
}
