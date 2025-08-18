use crate::models::{RuleContext, Severity, Violation};
use crate::rules::base::LintRule;

pub struct MarkdownFrontmatterTagsRule;

impl MarkdownFrontmatterTagsRule {
    pub fn new() -> Self {
        Self
    }

    fn is_markdown(file_path: &str) -> bool {
        std::path::Path::new(file_path)
            .extension()
            .and_then(|s| s.to_str())
            == Some("md")
    }

    fn extract_frontmatter(source: &str) -> Option<&str> {
        let mut lines = source.lines();

        let first = lines.next()?;
        if first.trim() != "---" {
            return None;
        }

        let mut start_idx = first.len() + 1; // include newline
        let mut end_idx = None;
        let mut offset = start_idx;

        for line in source[start_idx..].lines() {
            if line.trim() == "---" {
                end_idx = Some(offset - 1); // end before this line break
                break;
            }
            offset += line.len() + 1;
        }

        end_idx.and_then(|e| source.get(start_idx..e))
    }

    fn strip_inline_comment(token: &str) -> String {
        let mut in_single = false;
        let mut in_double = false;
        let mut out = String::new();
        for c in token.chars() {
            match c {
                '\'' if !in_double => {
                    in_single = !in_single;
                    out.push(c);
                }
                '"' if !in_single => {
                    in_double = !in_double;
                    out.push(c);
                }
                '#' if !in_single && !in_double => {
                    break;
                }
                _ => out.push(c),
            }
        }
        out.trim().to_string()
    }

    fn unquote(s: &str) -> (String, bool) {
        let st = s.trim();
        if (st.starts_with('"') && st.ends_with('"')) || (st.starts_with('\'') && st.ends_with('\'')) {
            (st[1..st.len() - 1].to_string(), true)
        } else {
            (st.to_string(), false)
        }
    }

    fn is_scalar_non_string(raw: &str, was_quoted: bool) -> bool {
        if was_quoted {
            return false;
        }
        let s = raw.trim();
        let lower = s.to_ascii_lowercase();
        if lower == "true" || lower == "false" || lower == "null" {
            return true;
        }
        let is_int = s.chars().all(|c| c.is_ascii_digit()) || (s.starts_with('-') && s[1..].chars().all(|c| c.is_ascii_digit()));
        if is_int {
            return true;
        }
        let mut dot_seen = false;
        let mut digits_seen = false;
        for (i, c) in s.chars().enumerate() {
            if c == '-' && i == 0 {
                continue;
            }
            if c == '.' && !dot_seen {
                dot_seen = true;
                continue;
            }
            if !c.is_ascii_digit() {
                return false;
            }
            digits_seen = true;
        }
        if digits_seen && dot_seen {
            return true;
        }
        false
    }

    fn parse_flow_list(after_colon: &str) -> Option<Vec<String>> {
        let mut s = after_colon.trim().to_string();
        if !s.starts_with('[') || !s.ends_with(']') {
            return None;
        }
        s = s[1..s.len() - 1].to_string();
        let mut items = Vec::new();
        let mut current = String::new();
        let mut in_single = false;
        let mut in_double = false;
        for c in s.chars() {
            match c {
                '\'' if !in_double => {
                    in_single = !in_single;
                    current.push(c);
                }
                '"' if !in_single => {
                    in_double = !in_double;
                    current.push(c);
                }
                ',' if !in_single && !in_double => {
                    let token = Self::strip_inline_comment(&current);
                    if !token.is_empty() {
                        let (val, quoted) = Self::unquote(&token);
                        let mut val = val.trim().to_string();
                        if let Some(rest) = val.strip_prefix('#') {
                            val = rest.trim().to_string();
                        }
                        if val.is_empty() || Self::is_scalar_non_string(&token, quoted) {
                            return None;
                        }
                        items.push(val);
                    }
                    current.clear();
                }
                _ => current.push(c),
            }
        }
        let token = Self::strip_inline_comment(&current);
        if !token.is_empty() {
            let (val, quoted) = Self::unquote(&token);
            let mut val = val.trim().to_string();
            if let Some(rest) = val.strip_prefix('#') {
                val = rest.trim().to_string();
            }
            if val.is_empty() || Self::is_scalar_non_string(&token, quoted) {
                return None;
            }
            items.push(val);
        }
        if items.is_empty() {
            None
        } else {
            Some(items)
        }
    }

    fn parse_block_list(lines: &[&str], start_idx: usize) -> Option<Vec<String>> {
        let mut items = Vec::new();
        for &line in &lines[start_idx..] {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            if !trimmed.starts_with('-') {
                break;
            }
            let after_dash = trimmed[1..].trim();
            let token = Self::strip_inline_comment(after_dash);
            if token.is_empty() {
                return None;
            }
            let (val, quoted) = Self::unquote(&token);
            let mut val = val.trim().to_string();
            if let Some(rest) = val.strip_prefix('#') {
                val = rest.trim().to_string();
            }
            if val.is_empty() || Self::is_scalar_non_string(&token, quoted) {
                return None;
            }
            items.push(val);
        }
        if items.is_empty() { None } else { Some(items) }
    }

    fn parse_tags(frontmatter: &str) -> Option<Vec<String>> {
        let lines: Vec<&str> = frontmatter.lines().collect();
        for (i, &line) in lines.iter().enumerate() {
            let trimmed = line.trim();
            if !trimmed.starts_with("tags:") {
                continue;
            }
            let after = trimmed["tags:".len()..].trim();
            if after.is_empty() {
                return Self::parse_block_list(&lines, i + 1);
            } else {
                if let Some(items) = Self::parse_flow_list(after) {
                    return Some(items);
                } else {
                    return None;
                }
            }
        }
        None
    }

    fn message(file_path: &str) -> String {
        format!(
r#"Markdown file '{}' must start with YAML frontmatter containing a non-empty 'tags' list (Obsidian Properties).

Examples (block sequence):
---
tags:
  - influxdb
  - database
  - network # inline comment allowed
---

Flow sequence:
---
tags: [influxdb, database, network]
---"#,
            file_path
        )
    }
}

impl LintRule for MarkdownFrontmatterTagsRule {
    fn rule_id(&self) -> &str {
        "PINJ062"
    }

    fn description(&self) -> &str {
        "Markdown files (.md) must have Obsidian-style YAML frontmatter at the top with a non-empty 'tags' list."
    }

    fn check(&self, context: &RuleContext) -> Vec<Violation> {
        let mut violations = Vec::new();

        if !Self::is_markdown(context.file_path) {
            return violations;
        }

        match Self::extract_frontmatter(context.source)
            .and_then(Self::parse_tags)
        {
            Some(tags) if !tags.is_empty() => {}
            _ => {
                violations.push(Violation {
                    rule_id: "PINJ062".to_string(),
                    message: Self::message(context.file_path),
                    offset: 0,
                    file_path: context.file_path.to_string(),
                    severity: Severity::Error,
                    fix: None,
                });
            }
        }

        violations
    }
}
