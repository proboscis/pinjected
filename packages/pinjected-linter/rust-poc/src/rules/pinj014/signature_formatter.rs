//! Signature formatting for @injected functions in stub files

use rustpython_ast::{Arg, ArgWithDefault, Arguments, Expr, StmtAsyncFunctionDef, StmtFunctionDef};

pub struct SignatureFormatter;

impl SignatureFormatter {
    pub fn new() -> Self {
        Self
    }

    /// Format type annotation
    pub fn format_type_annotation(&self, expr: &Expr) -> String {
        match expr {
            Expr::Name(name) => name.id.to_string(),
            Expr::Subscript(sub) => {
                let base = self.format_type_annotation(&sub.value);
                let index = self.format_type_annotation(&sub.slice);
                format!("{}[{}]", base, index)
            }
            Expr::Attribute(attr) => {
                let value = self.format_type_annotation(&attr.value);
                format!("{}.{}", value, attr.attr)
            }
            Expr::BinOp(binop) => {
                // Handle union types (e.g., str | None)
                let left = self.format_type_annotation(&binop.left);
                let right = self.format_type_annotation(&binop.right);
                format!("{} | {}", left, right)
            }
            Expr::Constant(constant) => match &constant.value {
                rustpython_ast::Constant::None => "None".to_string(),
                rustpython_ast::Constant::Str(s) => format!("'{}'", s),
                _ => "Any".to_string(),
            },
            _ => "Any".to_string(),
        }
    }

    /// Format a single argument
    pub fn format_arg(&self, arg: &Arg) -> String {
        let mut result = arg.arg.to_string();
        if let Some(ann) = &arg.annotation {
            result.push_str(": ");
            result.push_str(&self.format_type_annotation(ann));
        }
        result
    }

    /// Format an argument with default value
    pub fn format_arg_with_default(&self, arg: &ArgWithDefault) -> String {
        let mut result = self.format_arg(&arg.def);
        if arg.default.is_some() {
            // For stub files, we don't show default values, just indicate it has one
            result.push_str(" = ...");
        }
        result
    }

    /// Generate function signature for stub file (only runtime args after /)
    pub fn generate_function_signature(&self, func: &StmtFunctionDef) -> String {
        let mut sig = String::new();

        // Add async if needed
        if func.name.starts_with("a_") {
            sig.push_str("async ");
        }

        sig.push_str("def ");
        sig.push_str(&func.name);
        sig.push('(');

        let runtime_args = self.extract_runtime_args(&func.args);
        sig.push_str(&runtime_args.join(", "));
        sig.push(')');

        // Return type - transform to IProxy[T] if not already wrapped
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            let return_type = self.format_type_annotation(returns);
            
            // CRITICAL FIX: Check if already wrapped with IProxy to prevent progressive wrapping
            if return_type.starts_with("IProxy[") {
                sig.push_str(&return_type);
            } else {
                sig.push_str("IProxy[");
                sig.push_str(&return_type);
                sig.push(']');
            }
        }

        sig.push_str(": ...");
        sig
    }
    
    /// Generate function signature for non-injected functions (no IProxy wrapping)
    pub fn generate_non_injected_function_signature(&self, func: &StmtFunctionDef) -> String {
        let mut sig = String::new();

        sig.push_str("def ");
        sig.push_str(&func.name);
        sig.push('(');

        let args = self.extract_all_args(&func.args);
        sig.push_str(&args.join(", "));
        sig.push(')');

        // Return type - no IProxy wrapping
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str(&self.format_type_annotation(returns));
        }

        sig.push_str(": ...");
        sig
    }

    /// Generate async function signature for stub file (only runtime args after /)
    pub fn generate_async_function_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let mut sig = String::new();

        sig.push_str("async def ");
        sig.push_str(&func.name);
        sig.push('(');

        let runtime_args = self.extract_runtime_args(&func.args);
        sig.push_str(&runtime_args.join(", "));
        sig.push(')');

        // Return type - transform to IProxy[T] if not already wrapped
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            let return_type = self.format_type_annotation(returns);
            
            // CRITICAL FIX: Check if already wrapped with IProxy to prevent progressive wrapping
            if return_type.starts_with("IProxy[") {
                sig.push_str(&return_type);
            } else {
                sig.push_str("IProxy[");
                sig.push_str(&return_type);
                sig.push(']');
            }
        }

        sig.push_str(": ...");
        sig
    }
    
    /// Generate async function signature for non-injected functions (no IProxy wrapping)
    pub fn generate_non_injected_async_function_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let mut sig = String::new();

        sig.push_str("async def ");
        sig.push_str(&func.name);
        sig.push('(');

        let args = self.extract_all_args(&func.args);
        sig.push_str(&args.join(", "));
        sig.push(')');

        // Return type - no IProxy wrapping
        if let Some(returns) = &func.returns {
            sig.push_str(" -> ");
            sig.push_str(&self.format_type_annotation(returns));
        }

        sig.push_str(": ...");
        sig
    }

    /// Extract runtime arguments (those after the / separator)
    fn extract_runtime_args(&self, args: &Arguments) -> Vec<String> {
        let mut runtime_args = Vec::new();

        // Find if there are position-only args (which end with /)
        let has_posonly = !args.posonlyargs.is_empty();
        
        // For @injected functions, we only want args after the /
        // Position-only args are the injected dependencies
        // Regular args after the / are runtime arguments
        
        if has_posonly {
            // Skip position-only args (they are injected dependencies)
            // But include regular args (they are runtime args after /)
            
            // Regular args (these come after the /)
            for arg in &args.args {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // *args
            if let Some(vararg) = &args.vararg {
                runtime_args.push(format!("*{}", self.format_arg(vararg)));
            } else if !args.kwonlyargs.is_empty() && args.args.is_empty() {
                // If no *args but we have keyword-only args, add *
                runtime_args.push("*".to_string());
            }

            // Keyword-only args
            for arg in &args.kwonlyargs {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // **kwargs
            if let Some(kwarg) = &args.kwarg {
                runtime_args.push(format!("**{}", self.format_arg(kwarg)));
            }
        } else {
            // No position-only separator, include all args
            // This is for functions without explicit / separator
            
            // Regular args
            for arg in &args.args {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // *args
            if let Some(vararg) = &args.vararg {
                runtime_args.push(format!("*{}", self.format_arg(vararg)));
            } else if !args.kwonlyargs.is_empty() && args.args.is_empty() {
                // If no *args but we have keyword-only args, add *
                runtime_args.push("*".to_string());
            }

            // Keyword-only args
            for arg in &args.kwonlyargs {
                runtime_args.push(self.format_arg_with_default(arg));
            }

            // **kwargs
            if let Some(kwarg) = &args.kwarg {
                runtime_args.push(format!("**{}", self.format_arg(kwarg)));
            }
        }

        runtime_args
    }
    
    /// Extract all arguments (for non-injected functions)
    fn extract_all_args(&self, args: &Arguments) -> Vec<String> {
        let mut all_args = Vec::new();
        
        // Regular args
        for arg in &args.args {
            all_args.push(self.format_arg_with_default(arg));
        }
        
        // *args
        if let Some(vararg) = &args.vararg {
            all_args.push(format!("*{}", self.format_arg(vararg)));
        } else if !args.kwonlyargs.is_empty() {
            // If no *args but we have keyword-only args, add *
            all_args.push("*".to_string());
        }
        
        // Keyword-only args
        for arg in &args.kwonlyargs {
            all_args.push(self.format_arg_with_default(arg));
        }
        
        // **kwargs
        if let Some(kwarg) = &args.kwarg {
            all_args.push(format!("**{}", self.format_arg(kwarg)));
        }
        
        all_args
    }
}