use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;
use rustpython_ast::{
    Arg, Arguments, Expr, ExprAttribute, ExprConstant, ExprName, ExprSubscript, Stmt, StmtAsyncFunctionDef,
    StmtFunctionDef,
};

pub struct NoOptionalDependenciesRule;

impl NoOptionalDependenciesRule {
    pub fn new() -> Self {
        Self
    }
}

impl LintRule for NoOptionalDependenciesRule {
    fn rule_id(&self) -> &str {
        "PINJ064"
    }

    fn description(&self) -> &str {
        "Dependencies in @injected/@instance functions must not be annotated as Optional[T] or Union[T, None]. Handle optionality via DI (alternate providers/overrides), not optional types."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        match context.stmt {
            Stmt::FunctionDef(func_def) => {
                if is_injected_or_instance_decorated(func_def) {
                    violations.extend(check_function_annotations(func_def, context));
                }
            }
            Stmt::AsyncFunctionDef(async_func_def) => {
                if is_async_injected_or_instance_decorated(async_func_def) {
                    violations.extend(check_async_function_annotations(async_func_def, context));
                }
            }
            _ => {}
        }

        violations
    }
}

fn is_injected_or_instance_decorated(func_def: &StmtFunctionDef) -> bool {
    func_def.decorator_list.iter().any(|decorator| match decorator {
        Expr::Name(ExprName { id, .. }) => id == "injected" || id == "instance",
        Expr::Attribute(ExprAttribute { attr, value, .. }) => {
            (attr == "injected" || attr == "instance")
                && matches!(value.as_ref(), Expr::Name(ExprName { id, .. }) if id == "pinjected")
        }
        _ => false,
    })
}

fn is_async_injected_or_instance_decorated(async_func_def: &StmtAsyncFunctionDef) -> bool {
    async_func_def.decorator_list.iter().any(|decorator| match decorator {
        Expr::Name(ExprName { id, .. }) => id == "injected" || id == "instance",
        Expr::Attribute(ExprAttribute { attr, value, .. }) => {
            (attr == "injected" || attr == "instance")
                && matches!(value.as_ref(), Expr::Name(ExprName { id, .. }) if id == "pinjected")
        }
        _ => false,
    })
}

fn is_optional_like_annotation(expr: &Expr) -> bool {
    match expr {
        Expr::Subscript(ExprSubscript { value, .. }) => {
            matches_optional_name(value) || matches_union_with_none(expr)
        }
        Expr::Constant(ExprConstant { value, .. }) => {
            if let rustpython_ast::Constant::Str(s) = value {
                let s_lower = s.to_ascii_lowercase();
                s_lower.contains("optional[") || (s_lower.contains("union[") && s_lower.contains("none"))
            } else {
                false
            }
        }
        _ => false,
    }
}

fn matches_optional_name(expr: &Expr) -> bool {
    match expr {
        Expr::Name(ExprName { id, .. }) => id == "Optional",
        Expr::Attribute(ExprAttribute { attr, value, .. }) => {
            attr == "Optional" && matches!(value.as_ref(), Expr::Name(ExprName { id, .. }) if id == "typing")
        }
        _ => false,
    }
}

fn matches_union_with_none(expr: &Expr) -> bool {
    if let Expr::Subscript(ExprSubscript { value, slice, .. }) = expr {
        let is_union_name = match value.as_ref() {
            Expr::Name(ExprName { id, .. }) => id == "Union",
            Expr::Attribute(ExprAttribute { attr, value, .. }) => {
                attr == "Union" && matches!(value.as_ref(), Expr::Name(ExprName { id, .. }) if id == "typing")
            }
            _ => false,
        };
        if !is_union_name {
            return false;
        }
        match slice.as_ref() {
            Expr::Constant(ExprConstant { value, .. }) => matches!(value, rustpython_ast::Constant::None),
            Expr::Name(ExprName { id, .. }) => id == "None",
            Expr::Tuple(t) => t.elts.iter().any(|e| match e {
                Expr::Constant(ExprConstant { value, .. }) => {
                    matches!(value, rustpython_ast::Constant::None)
                }
                Expr::Name(ExprName { id, .. }) => id == "None",
                _ => false,
            }),
            _ => false,
        }
    } else {
        false
    }
}

fn check_function_annotations(func_def: &StmtFunctionDef, context: &RuleContext) -> Vec<Violation> {
    let mut violations = Vec::new();
    let args = &func_def.args;

    let has_posonly = !args.posonlyargs.is_empty();

    if has_posonly {
        for arg in &args.posonlyargs {
            if let Some(ann) = &arg.def.annotation {
                if is_optional_like_annotation(ann) {
                    push_violation(&mut violations, context, &func_def.name, &arg.def, func_def.range.start().to_usize());
                }
            }
        }
    } else {
        for arg in &args.args {
            if let Some(ann) = &arg.def.annotation {
                if is_optional_like_annotation(ann) {
                    push_violation(&mut violations, context, &func_def.name, &arg.def, func_def.range.start().to_usize());
                }
            }
        }
    }

    violations
}

fn check_async_function_annotations(async_func_def: &StmtAsyncFunctionDef, context: &RuleContext) -> Vec<Violation> {
    let mut violations = Vec::new();
    let args = &async_func_def.args;

    let has_posonly = !args.posonlyargs.is_empty();

    if has_posonly {
        for arg in &args.posonlyargs {
            if let Some(ann) = &arg.def.annotation {
                if is_optional_like_annotation(ann) {
                    push_violation(
                        &mut violations,
                        context,
                        &async_func_def.name,
                        &arg.def,
                        async_func_def.range.start().to_usize(),
                    );
                }
            }
        }
    } else {
        for arg in &args.args {
            if let Some(ann) = &arg.def.annotation {
                if is_optional_like_annotation(ann) {
                    push_violation(
                        &mut violations,
                        context,
                        &async_func_def.name,
                        &arg.def,
                        async_func_def.range.start().to_usize(),
                    );
                }
            }
        }
    }

    violations
}

fn push_violation(
    violations: &mut Vec<Violation>,
    context: &RuleContext,
    func_name: &str,
    arg_def: &Arg,
    offset: usize,
) {
    violations.push(Violation {
        rule_id: "PINJ064".to_string(),
        message: format!(
            "Dependency '{}' in @injected/@instance function '{}' must not be annotated as Optional[...] or Union[..., None]. Handle optionality via DI (alternate providers or overrides) instead.",
            &arg_def.arg, func_name
        ),
        file_path: context.file_path.to_string(),
        offset,
        severity: Severity::Error,
        fix: None,
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustpython_parser::{parse, Mode};

    fn first_func_stmt(ast: &rustpython_ast::Mod) -> &rustpython_ast::Stmt {
        match ast {
            rustpython_ast::Mod::Module(m) => m
                .body
                .iter()
                .find(|s| matches!(s, rustpython_ast::Stmt::FunctionDef(_) | rustpython_ast::Stmt::AsyncFunctionDef(_)))
                .expect("Expected a function definition"),
            _ => panic!("Expected module"),
        }
    }

    #[test]
    fn injected_dep_optional_flagged() {
        let code = r#"
from typing import Optional
@injected
def f(x: Optional[int], /):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let stmt = first_func_stmt(&ast);
        let ctx = RuleContext { stmt, file_path: "t.py", source: code, ast: &ast };
        let rule = NoOptionalDependenciesRule::new();
        let v = rule.check(&ctx);
        assert_eq!(v.len(), 1);
        assert!(v[0].message.contains("must not be annotated as Optional"));
    }

    #[test]
    fn instance_dep_union_none_flagged() {
        let code = r#"
from typing import Union
@instance
def g(x: Union[str, None], /):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let stmt = first_func_stmt(&ast);
        let ctx = RuleContext { stmt, file_path: "t.py", source: code, ast: &ast };
        let rule = NoOptionalDependenciesRule::new();
        let v = rule.check(&ctx);
        assert_eq!(v.len(), 1);
        assert!(v[0].message.contains("Union"));
    }

    #[test]
    fn async_injected_optional_flagged() {
        let code = r#"
from typing import Optional
@injected
async def h(x: Optional[str], /):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let stmt = first_func_stmt(&ast);
        let ctx = RuleContext { stmt, file_path: "t.py", source: code, ast: &ast };
        let rule = NoOptionalDependenciesRule::new();
        let v = rule.check(&ctx);
        assert_eq!(v.len(), 1);
    }

    #[test]
    fn no_slash_all_args_as_deps() {
        let code = r#"
from typing import Optional
@injected
def k(x: Optional[int]):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let stmt = first_func_stmt(&ast);
        let ctx = RuleContext { stmt, file_path: "t.py", source: code, ast: &ast };
        let rule = NoOptionalDependenciesRule::new();
        let v = rule.check(&ctx);
        assert_eq!(v.len(), 1);
    }

    #[test]
    fn non_dep_after_slash_not_flagged() {
        let code = r#"
from typing import Optional
@injected
def ok(x, /, y: Optional[int] = None):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let stmt = first_func_stmt(&ast);
        let ctx = RuleContext { stmt, file_path: "t.py", source: code, ast: &ast };
        let rule = NoOptionalDependenciesRule::new();
        let v = rule.check(&ctx);
        assert_eq!(v.len(), 0);
    }

    #[test]
    fn string_annotation_optional_flagged() {
        let code = r#"
@instance
def s(x: "Optional[int]", /):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let stmt = first_func_stmt(&ast);
        let ctx = RuleContext { stmt, file_path: "t.py", source: code, ast: &ast };
        let rule = NoOptionalDependenciesRule::new();
        let v = rule.check(&ctx);
        assert_eq!(v.len(), 1);
    }

    #[test]
    fn good_non_optional_dep_ok() {
        let code = r#"
@injected
def good(x: int, /):
    pass
"#;
        let ast = parse(code, Mode::Module, "<test>").unwrap();
        let stmt = first_func_stmt(&ast);
        let ctx = RuleContext { stmt, file_path: "t.py", source: code, ast: &ast };
        let rule = NoOptionalDependenciesRule::new();
        let v = rule.check(&ctx);
        assert_eq!(v.len(), 0);
    }
}
