use anyhow::Result;
use rustpython_ast::{Expr, Mod, Stmt, StmtAsyncFunctionDef, StmtFunctionDef};
use rustpython_parser::{parse, Mode};
use serde::{Deserialize, Serialize};
use std::path::Path;
use tracing::debug;
use crate::index::LineIndex;

/// Represents an @injected function
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InjectedFunction {
    pub name: String,
    pub module_path: String,
    pub parameter_name: String,
    pub parameter_type: String,
    pub line_number: usize,
    pub docstring: Option<String>,
    pub is_async: bool,
}

/// Represents an IProxy[T] variable
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IProxyVariable {
    pub name: String,
    pub type_parameter: String,
    pub module_path: String,
    pub line_number: usize,
}

/// Parse a Python file and extract @injected functions
pub async fn parse_python_file(path: &Path) -> Result<Vec<InjectedFunction>> {
    let content = tokio::fs::read_to_string(path).await?;
    
    // Quick check for performance
    if !content.contains("@injected") && !content.contains("@Injected") {
        return Ok(Vec::new());
    }
    
    // Parse the AST
    let ast = parse(&content, Mode::Module, path.to_str().unwrap())?;
    
    // Extract functions
    let mut functions = Vec::new();
    extract_injected_functions(&ast, &mut functions, path, &content);
    
    debug!("Found {} @injected functions in {:?}", functions.len(), path);
    Ok(functions)
}

/// Extract @injected functions from AST
fn extract_injected_functions(module: &Mod, functions: &mut Vec<InjectedFunction>, path: &Path, content: &str) {
    let Mod::Module(module) = module else {
        return;
    };
    
    // Build module path from file path
    let module_path = path_to_module(path);
    
    // Create line index for converting offsets to line numbers
    let line_index = LineIndex::new(content);
    
    for stmt in &module.body {
        match stmt {
            Stmt::FunctionDef(func) => {
                if let Some(injected) = extract_if_injected(func, &module_path, &line_index) {
                    functions.push(injected);
                }
            }
            Stmt::AsyncFunctionDef(func) => {
                if let Some(injected) = extract_if_async_injected(func, &module_path, &line_index) {
                    functions.push(injected);
                }
            }
            _ => {}
        }
    }
}

/// Check if function has @injected decorator and extract info
fn extract_if_injected(func: &StmtFunctionDef, module_path: &str, line_index: &LineIndex) -> Option<InjectedFunction> {
    // Check for @injected decorator
    if !has_injected_decorator(&func.decorator_list) {
        return None;
    }
    
    // Find parameter after '/' separator
    let param = extract_injected_parameter(func)?;
    
    // Extract docstring
    let docstring = extract_docstring(&func.body);
    
    Some(InjectedFunction {
        name: func.name.to_string(),
        module_path: format!("{}.{}", module_path, func.name),
        parameter_name: param.0,
        parameter_type: param.1,
        line_number: line_index.line_number(func.range.start()),
        docstring,
        is_async: false,
    })
}

/// Check if async function has @injected decorator and extract info
fn extract_if_async_injected(func: &StmtAsyncFunctionDef, module_path: &str, line_index: &LineIndex) -> Option<InjectedFunction> {
    // Check for @injected decorator
    if !has_injected_decorator(&func.decorator_list) {
        return None;
    }
    
    // Find parameter after '/' separator
    let param = extract_async_injected_parameter(func)?;
    
    // Extract docstring
    let docstring = extract_docstring(&func.body);
    
    Some(InjectedFunction {
        name: func.name.to_string(),
        module_path: format!("{}.{}", module_path, func.name),
        parameter_name: param.0,
        parameter_type: param.1,
        line_number: line_index.line_number(func.range.start()),
        docstring,
        is_async: true,
    })
}

/// Check if decorator list contains @injected
fn has_injected_decorator(decorators: &[Expr]) -> bool {
    for decorator in decorators {
        if is_injected_decorator(decorator) {
            return true;
        }
    }
    false
}

/// Check if expression is @injected decorator
fn is_injected_decorator(expr: &Expr) -> bool {
    match expr {
        Expr::Name(name) => name.id.as_str() == "injected",
        Expr::Attribute(attr) => {
            if let Expr::Name(name) = &*attr.value {
                (name.id.as_str() == "pinjected" || name.id.as_str() == "Injected") 
                    && attr.attr.as_str() == "injected"
            } else {
                false
            }
        }
        Expr::Call(call) => {
            // Handle @injected(...) with arguments
            match &*call.func {
                Expr::Name(name) => name.id.as_str() == "injected",
                Expr::Attribute(attr) => {
                    if let Expr::Name(name) = &*attr.value {
                        (name.id.as_str() == "pinjected" || name.id.as_str() == "Injected")
                            && attr.attr.as_str() == "injected"
                    } else {
                        false
                    }
                }
                _ => false,
            }
        }
        _ => false,
    }
}

/// Extract the single non-default parameter after '/' in function signature
/// Valid: @injected def f(dep1,dep2,/,x:T,param=42): ...
/// Invalid: @injected def f(dep1,dep2,/,x:T,y:U): ... (2 non-default params)
fn extract_injected_parameter(func: &StmtFunctionDef) -> Option<(String, String)> {
    let args = &func.args;
    
    // We need to look at regular parameters (after '/')
    // args.args contains parameters after the positional-only separator
    // args.defaults contains default values, aligned to the END of args.args
    
    if args.args.is_empty() {
        return None;
    }
    
    // Calculate how many parameters have no defaults
    // If we have N args and M defaults, then the first (N-M) args have no defaults
    let num_args = args.args.len();
    let num_defaults = args.defaults().count();
    let num_non_default = num_args - num_defaults;
    
    // For valid @injected functions, exactly ONE parameter should have no default
    if num_non_default != 1 {
        return None;
    }
    
    // The first parameter is the one without a default (since defaults align to the end)
    let arg = &args.args[0];
    let param_name = arg.def.arg.to_string();
    let param_type = extract_type_annotation(&arg.def.annotation);
    
    Some((param_name, param_type))
}

/// Extract the single non-default parameter after '/' in async function signature
/// Same rules as sync version - exactly one parameter without default after '/'
fn extract_async_injected_parameter(func: &StmtAsyncFunctionDef) -> Option<(String, String)> {
    let args = &func.args;
    
    // We need to look at regular parameters (after '/')
    // args.args contains parameters after the positional-only separator
    // args.defaults contains default values, aligned to the END of args.args
    
    if args.args.is_empty() {
        return None;
    }
    
    // Calculate how many parameters have no defaults
    // If we have N args and M defaults, then the first (N-M) args have no defaults
    let num_args = args.args.len();
    let num_defaults = args.defaults().count();
    let num_non_default = num_args - num_defaults;
    
    // For valid @injected functions, exactly ONE parameter should have no default
    if num_non_default != 1 {
        return None;
    }
    
    // The first parameter is the one without a default (since defaults align to the end)
    let arg = &args.args[0];
    let param_name = arg.def.arg.to_string();
    let param_type = extract_type_annotation(&arg.def.annotation);
    
    Some((param_name, param_type))
}

/// Extract type annotation as string
fn extract_type_annotation(annotation: &Option<Box<Expr>>) -> String {
    match annotation {
        Some(expr) => expr_to_type_string(&**expr),
        None => "Any".to_string(),
    }
}

/// Convert expression to type string
fn expr_to_type_string(expr: &Expr) -> String {
    match expr {
        Expr::Name(name) => name.id.to_string(),
        Expr::Attribute(attr) => {
            format!("{}.{}", expr_to_type_string(&attr.value), attr.attr)
        }
        Expr::Subscript(sub) => {
            // Handle generic types like List[User], Dict[str, User], etc.
            let base = expr_to_type_string(&sub.value);
            let slice = match &*sub.slice {
                Expr::Tuple(tuple) => {
                    // Multiple type parameters: Dict[str, User]
                    tuple.elts.iter()
                        .map(|e| expr_to_type_string(e))
                        .collect::<Vec<_>>()
                        .join(", ")
                }
                expr => expr_to_type_string(expr)
            };
            format!("{}[{}]", base, slice)
        }
        Expr::Constant(c) => {
            format!("{:?}", c.value)
        }
        _ => "Any".to_string(),
    }
}

/// Extract docstring from function body
fn extract_docstring(body: &[Stmt]) -> Option<String> {
    if let Some(Stmt::Expr(expr_stmt)) = body.first() {
        if let Expr::Constant(c) = &*expr_stmt.value {
            if let rustpython_ast::Constant::Str(s) = &c.value {
                return Some(s.to_string());
            }
        }
    }
    None
}

/// Convert file path to module path
fn path_to_module(path: &Path) -> String {
    let path_str = path.to_string_lossy();
    let path_str = path_str.trim_end_matches(".py");
    path_str.replace('/', ".").replace('\\', ".")
}

/// Parse IProxy[T] variables from a Python file
pub async fn parse_iproxy_variables(path: &Path) -> Result<Vec<IProxyVariable>> {
    let content = tokio::fs::read_to_string(path).await?;
    
    // Quick check for performance
    if !content.contains("IProxy") {
        return Ok(Vec::new());
    }
    
    // Parse the AST
    let ast = parse(&content, Mode::Module, path.to_str().unwrap())?;
    
    // Extract IProxy variables
    let mut variables = Vec::new();
    extract_iproxy_variables(&ast, &mut variables, path, &content);
    
    debug!("Found {} IProxy variables in {:?}", variables.len(), path);
    Ok(variables)
}

/// Extract IProxy[T] variables from AST
fn extract_iproxy_variables(module: &Mod, variables: &mut Vec<IProxyVariable>, path: &Path, content: &str) {
    let Mod::Module(module) = module else {
        return;
    };
    
    let module_path = path_to_module(path);
    
    // Create line index for converting offsets to line numbers
    let line_index = LineIndex::new(content);
    
    for stmt in &module.body {
        if let Stmt::AnnAssign(ann_assign) = stmt {
            if let Some(type_param) = extract_iproxy_type(&*ann_assign.annotation) {
                if let Expr::Name(name) = &*ann_assign.target {
                    variables.push(IProxyVariable {
                        name: name.id.to_string(),
                        type_parameter: type_param,
                        module_path: module_path.clone(),
                        line_number: line_index.line_number(ann_assign.range.start()),
                    });
                }
            }
        }
    }
}

/// Extract T from IProxy[T] annotation
fn extract_iproxy_type(annotation: &Expr) -> Option<String> {
    if let Expr::Subscript(sub) = annotation {
        // Check if it's IProxy
        if let Expr::Name(name) = &*sub.value {
            if name.id.as_str() == "IProxy" {
                return Some(expr_to_type_string(&sub.slice));
            }
        } else if let Expr::Attribute(attr) = &*sub.value {
            // Handle pinjected.IProxy[T]
            if attr.attr.as_str() == "IProxy" {
                return Some(expr_to_type_string(&sub.slice));
            }
        }
    }
    None
}