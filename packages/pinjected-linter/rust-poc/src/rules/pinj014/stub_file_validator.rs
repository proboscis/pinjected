//! Stub file validation for @injected functions

use rustpython_ast::{Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
use rustpython_parser::{parse, Mode};
use std::collections::HashMap;
use std::path::Path;

use super::injected_function_analyzer::InjectedFunctionInfo;
use super::signature_formatter::SignatureFormatter;

pub struct StubFileValidator {
    sig_formatter: SignatureFormatter,
}

impl StubFileValidator {
    pub fn new() -> Self {
        Self {
            sig_formatter: SignatureFormatter::new(),
        }
    }

    /// Extract function signatures from a stub file
    pub fn extract_stub_signatures(&self, stub_path: &Path) -> Result<HashMap<String, String>, String> {
        let content = std::fs::read_to_string(stub_path)
            .map_err(|e| format!("Failed to read stub file: {}", e))?;
        
        let ast = parse(&content, Mode::Module, stub_path.to_str().unwrap())
            .map_err(|e| format!("Failed to parse stub file: {}", e))?;
        
        let mut signatures = HashMap::new();
        
        match &ast {
            Mod::Module(module) => {
                for stmt in &module.body {
                    self.extract_function_signatures(stmt, &mut signatures);
                }
            }
            _ => {}
        }
        
        Ok(signatures)
    }
    
    /// Extract function signatures from statements (handles nested functions)
    fn extract_function_signatures(&self, stmt: &Stmt, signatures: &mut HashMap<String, String>) {
        match stmt {
            Stmt::FunctionDef(func) => {
                // Check if it has @overload decorator
                let has_overload = func.decorator_list.iter().any(|dec| {
                    if let Expr::Name(name) = dec {
                        name.id.as_str() == "overload"
                    } else {
                        false
                    }
                });
                
                if has_overload {
                    signatures.insert(func.name.to_string(), self.format_stub_signature(func));
                }
                
                // Check nested functions
                for stmt in &func.body {
                    self.extract_function_signatures(stmt, signatures);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                // Check if it has @overload decorator
                let has_overload = func.decorator_list.iter().any(|dec| {
                    if let Expr::Name(name) = dec {
                        name.id.as_str() == "overload"
                    } else {
                        false
                    }
                });
                
                if has_overload {
                    signatures.insert(func.name.to_string(), self.format_async_stub_signature(func));
                }
                
                // Check nested functions
                for stmt in &func.body {
                    self.extract_function_signatures(stmt, signatures);
                }
            }
            Stmt::ClassDef(class) => {
                // Check methods in classes
                for stmt in &class.body {
                    self.extract_function_signatures(stmt, signatures);
                }
            }
            _ => {}
        }
    }

    /// Format a function signature from stub file for comparison
    fn format_stub_signature(&self, func: &StmtFunctionDef) -> String {
        let sig = self.sig_formatter.generate_function_signature(func);
        // Remove trailing ": ..." for comparison
        sig.trim_end_matches(": ...").to_string()
    }
    
    /// Format an async function signature from stub file for comparison
    fn format_async_stub_signature(&self, func: &StmtAsyncFunctionDef) -> String {
        let sig = self.sig_formatter.generate_async_function_signature(func);
        // Remove trailing ": ..." for comparison
        sig.trim_end_matches(": ...").to_string()
    }

    /// Validate stub file signatures against expected signatures
    pub fn validate_stub_signatures(
        &self, 
        stub_path: &Path, 
        expected_functions: &[InjectedFunctionInfo]
    ) -> Vec<String> {
        let mut errors = Vec::new();
        
        // Try to parse the stub file
        let actual_signatures = match self.extract_stub_signatures(stub_path) {
            Ok(sigs) => sigs,
            Err(e) => {
                errors.push(format!("Failed to parse stub file: {}", e));
                return errors;
            }
        };
        
        // Check each expected function
        for expected in expected_functions {
            let expected_sig = expected.signature.trim_end_matches(": ...").to_string();
            
            match actual_signatures.get(&expected.name) {
                Some(actual_sig) => {
                    if actual_sig.trim() != expected_sig.trim() {
                        errors.push(format!(
                            "Function '{}' has incorrect signature in stub file.\nExpected: {}\nActual: {}",
                            expected.name,
                            expected_sig,
                            actual_sig
                        ));
                    }
                }
                None => {
                    errors.push(format!(
                        "Function '{}' is missing from stub file.\nExpected: {}",
                        expected.name,
                        expected_sig
                    ));
                }
            }
        }
        
        // Check for extra functions in stub file that shouldn't be there
        for (name, sig) in &actual_signatures {
            if !expected_functions.iter().any(|f| &f.name == name) {
                errors.push(format!(
                    "Unexpected function '{}' in stub file with signature: {}",
                    name,
                    sig
                ));
            }
        }
        
        errors
    }
}