//! Stub file generation and merging for @injected functions

use rustpython_ast::{Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
use rustpython_parser::{parse, Mode};
use std::collections::HashSet;

use super::ast_formatter::AstFormatter;
use super::injected_function_analyzer::InjectedFunctionInfo;
use super::signature_formatter::SignatureFormatter;

pub struct StubFileGenerator {
    ast_formatter: AstFormatter,
    sig_formatter: SignatureFormatter,
}

impl StubFileGenerator {
    pub fn new() -> Self {
        Self {
            ast_formatter: AstFormatter::new(),
            sig_formatter: SignatureFormatter::new(),
        }
    }

    /// Generate stub file content for @injected functions
    pub fn generate_stub_content(&self, functions: &[InjectedFunctionInfo]) -> String {
        let mut lines = Vec::new();

        // Add imports
        lines.push("from typing import overload".to_string());
        lines.push("from pinjected import IProxy".to_string());
        lines.push(String::new());

        // Add @overload decorated function signatures
        for func in functions {
            lines.push("@overload".to_string());
            lines.push(func.signature.clone());
            lines.push(String::new());
        }

        // Remove trailing empty line
        if lines.last() == Some(&String::new()) {
            lines.pop();
        }

        lines.join("\n")
    }

    pub fn merge_stub_content(&self, existing_content: &str, functions: &[InjectedFunctionInfo]) -> String {
        // Parse the existing content to extract its AST
        let existing_ast = match parse(existing_content, Mode::Module, "<stub>") {
            Ok(ast) => ast,
            Err(_) => {
                // If we can't parse the existing content, fall back to generating new content
                return self.generate_stub_content(functions);
            }
        };

        let mut result_lines = Vec::new();
        let mut processed_functions = HashSet::new();
        let mut has_overload_import = false;
        let mut has_iproxy_import = false;
        let mut import_section_ended = false;

        // First pass: process imports and track what we have
        if let Mod::Module(module) = &existing_ast {
            for stmt in &module.body {
                match stmt {
                    Stmt::Import(_import) => {
                        // Preserve import statements
                        let import_str = self.ast_formatter.format_import_stmt(stmt);
                        result_lines.push(import_str);
                    }
                    Stmt::ImportFrom(import_from) => {
                        // Check for necessary imports
                        if let Some(module) = &import_from.module {
                            match module.as_str() {
                                "typing" => {
                                    for alias in &import_from.names {
                                        if alias.name.as_str() == "overload" {
                                            has_overload_import = true;
                                        }
                                    }
                                }
                                "pinjected" => {
                                    for alias in &import_from.names {
                                        if alias.name.as_str() == "IProxy" {
                                            has_iproxy_import = true;
                                        }
                                    }
                                }
                                _ => {}
                            }
                        }
                        let import_str = self.ast_formatter.format_import_from_stmt(stmt);
                        result_lines.push(import_str);
                    }
                    _ => {
                        // Mark end of import section
                        if !import_section_ended && !result_lines.is_empty() {
                            import_section_ended = true;
                            result_lines.push(String::new()); // Add blank line after imports
                        }
                        break;
                    }
                }
            }
        }

        // Add missing imports at the beginning
        let mut missing_imports = Vec::new();
        if !has_overload_import {
            missing_imports.push("from typing import overload".to_string());
        }
        if !has_iproxy_import {
            missing_imports.push("from pinjected import IProxy".to_string());
        }
        
        if !missing_imports.is_empty() {
            // Insert missing imports at the beginning
            for import in missing_imports.iter().rev() {
                result_lines.insert(0, import.clone());
            }
            if !import_section_ended {
                result_lines.push(String::new()); // Add blank line after imports
            }
        }

        // Second pass: process the rest of the content
        if let Mod::Module(module) = &existing_ast {
            let mut _in_imports = true;
            for stmt in &module.body {
                match stmt {
                    Stmt::Import(_) | Stmt::ImportFrom(_) => {
                        // Already processed in first pass
                        continue;
                    }
                    Stmt::FunctionDef(func) => {
                        _in_imports = false;
                        // Check if this is an @overload decorated function
                        let has_overload = func.decorator_list.iter().any(|dec| {
                            if let Expr::Name(name) = dec {
                                name.id.as_str() == "overload"
                            } else {
                                false
                            }
                        });

                        if has_overload {
                            // Check if this function needs to be updated
                            if let Some(expected) = functions.iter().find(|f| f.name == func.name.as_str()) {
                                // Compare signatures to see if update is needed
                                let current_sig = self.format_stub_signature(func);
                                let expected_sig = expected.signature.trim_end_matches(": ...").to_string();
                                
                                if current_sig.trim() != expected_sig.trim() {
                                    // Signature needs updating
                                    result_lines.push("@overload".to_string());
                                    result_lines.push(expected.signature.clone());
                                } else {
                                    // Signature is already correct, preserve as-is
                                    result_lines.push(self.ast_formatter.format_function_def(func));
                                }
                                processed_functions.insert(expected.name.clone());
                            } else {
                                // Preserve non-injected overloads
                                result_lines.push(self.ast_formatter.format_function_def(func));
                            }
                            result_lines.push(String::new()); // Add blank line after function
                        } else {
                            // CRITICAL FIX: Check if this is an @injected function that should have @overload
                            if functions.iter().any(|f| f.name == func.name.as_str()) {
                                // This function should have @overload, skip it to avoid duplicates
                                // It will be added later in the missing functions section
                            } else {
                                // Preserve non-overload functions exactly as they are
                                result_lines.push(self.ast_formatter.format_function_def(func));
                                result_lines.push(String::new()); // Add blank line after function
                            }
                        }
                    }
                    Stmt::AsyncFunctionDef(func) => {
                        _in_imports = false;
                        // Check if this is an @overload decorated function
                        let has_overload = func.decorator_list.iter().any(|dec| {
                            if let Expr::Name(name) = dec {
                                name.id.as_str() == "overload"
                            } else {
                                false
                            }
                        });

                        if has_overload {
                            // Check if this function needs to be updated
                            if let Some(expected) = functions.iter().find(|f| f.name == func.name.as_str()) {
                                // Compare signatures to see if update is needed
                                let current_sig = self.format_async_stub_signature(func);
                                let expected_sig = expected.signature.trim_end_matches(": ...").to_string();
                                
                                if current_sig.trim() != expected_sig.trim() {
                                    // Signature needs updating
                                    result_lines.push("@overload".to_string());
                                    result_lines.push(expected.signature.clone());
                                } else {
                                    // Signature is already correct, preserve as-is
                                    result_lines.push(self.ast_formatter.format_async_function_def(func));
                                }
                                processed_functions.insert(expected.name.clone());
                            } else {
                                // Preserve non-injected overloads
                                result_lines.push(self.ast_formatter.format_async_function_def(func));
                            }
                            result_lines.push(String::new()); // Add blank line after function
                        } else {
                            // CRITICAL FIX: Check if this is an @injected function that should have @overload
                            if functions.iter().any(|f| f.name == func.name.as_str()) {
                                // This function should have @overload, skip it to avoid duplicates
                                // It will be added later in the missing functions section
                            } else {
                                // Preserve non-overload functions exactly as they are
                                result_lines.push(self.ast_formatter.format_async_function_def(func));
                                result_lines.push(String::new()); // Add blank line after function
                            }
                        }
                    }
                    _ => {
                        _in_imports = false;
                        // CRITICAL: Preserve all other statements exactly as they appear in the original file
                        // We should not try to reformat them since we might lose important information
                        
                        // Just use the formatter - we've already improved it to preserve classes
                        result_lines.push(self.ast_formatter.format_other_stmt(stmt));
                        
                        // Don't add extra blank lines if the statement already includes them
                        if !result_lines.last().map_or(false, |s| s.trim().is_empty()) {
                            result_lines.push(String::new()); // Add blank line
                        }
                    }
                }
            }
        }

        // Add any missing @overload functions
        for func in functions {
            if !processed_functions.contains(&func.name) {
                result_lines.push("@overload".to_string());
                result_lines.push(func.signature.clone());
                result_lines.push(String::new()); // Add blank line
            }
        }

        // Join all lines, removing trailing blank lines
        let mut final_content = result_lines.join("\n");
        while final_content.ends_with("\n\n") {
            final_content.pop();
        }
        if !final_content.ends_with('\n') {
            final_content.push('\n');
        }

        final_content
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
}