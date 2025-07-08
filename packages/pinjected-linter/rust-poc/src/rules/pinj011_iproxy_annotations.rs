//! PINJ011: IProxy type annotations
//! 
//! IProxy[T] should be used for:
//! 1. Return types of @instance functions when they are entry points
//! 
//! IProxy[T] should NOT be used for:
//! 1. Injected dependencies (parameters before / in @injected functions)
//! 2. Regular function parameters or return types

use rustpython_ast::{Mod, Stmt, Expr};
use crate::models::{Violation, RuleContext, Severity};
use crate::rules::base::LintRule;
use crate::utils::pinjected_patterns::{has_instance_decorator, has_instance_decorator_async};

pub struct IProxyAnnotationsRule {
    /// Track if IProxy is imported and its alias
    has_iproxy_import: bool,
    iproxy_alias: Option<String>,
}

impl IProxyAnnotationsRule {
    pub fn new() -> Self {
        Self {
            has_iproxy_import: false,
            iproxy_alias: None,
        }
    }
    
    /// Track IProxy imports
    fn track_imports(&mut self, ast: &Mod) {
        match ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    if let Stmt::ImportFrom(import) = stmt {
                        if let Some(module) = &import.module {
                            if module.as_str() == "pinjected" {
                                for alias in &import.names {
                                    if alias.name.as_str() == "IProxy" {
                                        self.has_iproxy_import = true;
                                        self.iproxy_alias = alias.asname.as_ref().map(|s| s.to_string());
                                    }
                                }
                            }
                        }
                    }
                }
            }
            _ => {}
        }
    }
    
    /// Check if the annotation is IProxy[T] or just IProxy
    fn is_iproxy_annotation(&self, annotation: &Expr) -> bool {
        match annotation {
            Expr::Name(name) => {
                // Check for bare IProxy
                let iproxy_name = self.iproxy_alias.as_deref().unwrap_or("IProxy");
                name.id.as_str() == iproxy_name
            }
            Expr::Subscript(subscript) => {
                // Check for IProxy[T]
                if let Expr::Name(name) = &*subscript.value {
                    let iproxy_name = self.iproxy_alias.as_deref().unwrap_or("IProxy");
                    name.id.as_str() == iproxy_name
                } else {
                    false
                }
            }
            _ => false
        }
    }
    
    /// Check if the type looks like a service/component
    fn is_service_type(&self, annotation: &Expr) -> bool {
        let annotation_str = self.get_annotation_string(annotation);
        
        let service_patterns = [
            "Service", "Client", "Repository", "Manager",
            "Handler", "Controller", "Gateway", "Adapter", "Provider",
        ];
        
        service_patterns.iter().any(|pattern| annotation_str.contains(pattern))
    }
    
    /// Get string representation of annotation
    fn get_annotation_string(&self, annotation: &Expr) -> String {
        match annotation {
            Expr::Name(name) => name.id.to_string(),
            Expr::Subscript(subscript) => {
                // For subscripted types like List[int], get the base type
                self.get_annotation_string(&subscript.value)
            }
            Expr::Attribute(attr) => {
                let value = self.get_annotation_string(&attr.value);
                format!("{}.{}", value, attr.attr)
            }
            _ => "Any".to_string()
        }
    }
    
    /// Check @instance function return types
    fn check_instance_function(&self, func: &rustpython_ast::StmtFunctionDef, file_path: &str, violations: &mut Vec<Violation>) {
        if let Some(return_annotation) = &func.returns {
            // Check if it's a service type that should use IProxy
            if self.is_service_type(return_annotation) && !self.is_iproxy_annotation(return_annotation) {
                let annotation_str = self.get_annotation_string(return_annotation);
                
                violations.push(Violation {
                    rule_id: "PINJ011".to_string(),
                    message: format!(
                        "@instance function '{}' returns a service type but doesn't use IProxy. \
                        Entry point services should return IProxy[T] for proper dependency tracking. \
                        Change return type to IProxy[{}]",
                        func.name,
                        annotation_str
                    ),
                    offset: func.range.start().to_usize(),
                    file_path: file_path.to_string(),
                    severity: Severity::Warning,
                });
            }
        }
    }
    
    /// Check async @instance function return types
    fn check_instance_function_async(&self, func: &rustpython_ast::StmtAsyncFunctionDef, file_path: &str, violations: &mut Vec<Violation>) {
        if let Some(return_annotation) = &func.returns {
            // Check if it's a service type that should use IProxy
            if self.is_service_type(return_annotation) && !self.is_iproxy_annotation(return_annotation) {
                let annotation_str = self.get_annotation_string(return_annotation);
                
                violations.push(Violation {
                    rule_id: "PINJ011".to_string(),
                    message: format!(
                        "@instance function '{}' returns a service type but doesn't use IProxy. \
                        Entry point services should return IProxy[T] for proper dependency tracking. \
                        Change return type to IProxy[{}]",
                        func.name,
                        annotation_str
                    ),
                    offset: func.range.start().to_usize(),
                    file_path: file_path.to_string(),
                    severity: Severity::Warning,
                });
            }
        }
    }
    
    /// Check statements
    fn check_stmt(&self, stmt: &Stmt, file_path: &str, violations: &mut Vec<Violation>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                // Only check @instance functions
                if has_instance_decorator(func) {
                    self.check_instance_function(func, file_path, violations);
                }
                // Check nested functions
                for stmt in &func.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                // Only check @instance functions
                if has_instance_decorator_async(func) {
                    self.check_instance_function_async(func, file_path, violations);
                }
                // Check nested functions
                for stmt in &func.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.check_stmt(stmt, file_path, violations);
                }
            }
            _ => {}
        }
    }
}

impl LintRule for IProxyAnnotationsRule {
    fn rule_id(&self) -> &str {
        "PINJ011"
    }
    
    fn description(&self) -> &str {
        "Dependencies should use IProxy[T] type annotations"
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();
        
        // Create a mutable instance for stateful tracking
        let mut checker = IProxyAnnotationsRule::new();
        
        // First track imports
        checker.track_imports(context.ast);
        
        // Then check the current statement
        checker.check_stmt(context.stmt, context.file_path, &mut violations);
        
        violations
    }
}