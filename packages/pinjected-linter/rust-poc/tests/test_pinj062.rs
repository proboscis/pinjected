use pinjected_linter::rules::pinj062_markdown_frontmatter_tags::MarkdownFrontmatterTagsRule;
use pinjected_linter::rules::base::LintRule;
use pinjected_linter::models::RuleContext;
use rustpython_parser::{parse, Mode};
use rustpython_ast::text_size::TextRange;
use rustpython_ast::Stmt;

fn ctx_for(source: &str, file_path: &str) -> RuleContext<'_> {
    let ast = parse("", Mode::Module, file_path).unwrap();
    let dummy_stmt = Box::leak(Box::new(Stmt::Pass(rustpython_ast::StmtPass { range: TextRange::default() })));
    RuleContext {
        stmt: dummy_stmt,
        file_path,
        source,
        ast: &ast,
    }
}

#[test]
fn test_pinj062_missing_frontmatter() {
    let code = "# Title\n\nSome content.";
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 1);
    assert_eq!(v[0].rule_id, "PINJ062");
}

#[test]
fn test_pinj062_missing_tags_key() {
    let code = r#"---
title: My note
---

Content
"#;
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 1);
}

#[test]
fn test_pinj062_tags_not_list() {
    let code = r#"---
tags: "influxdb"
---"#;
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 1);
}

#[test]
fn test_pinj062_empty_list() {
    let code = r#"---
tags: []
---"#;
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 1);
}

#[test]
fn test_pinj062_non_string_entries() {
    let code = r#"---
tags: [influxdb, 123, true]
---"#;
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 1);
}

#[test]
fn test_pinj062_ok_block_sequence_with_comments() {
    let code = r#"---
tags:
  - influxdb
  - database
  - network # comment here
---
Body"#;
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 0);
}

#[test]
fn test_pinj062_ok_flow_sequence() {
    let code = r#"---
tags: [influxdb, database, network]
---
Body"#;
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 0);
}

#[test]
fn test_pinj062_leading_hash_in_values_block() {
    let code = r#"---
tags:
  - #influxdb
  - #database
  - #network
---
Body"#;
    let rule = MarkdownFrontmatterTagsRule::new();
    let ctx = ctx_for(code, "note.md");
    let v = rule.check(&ctx);
    assert_eq!(v.len(), 0);
}
