//! Support for # noqa comment directives to suppress linter violations
//!
//! Supports the following formats:
//! - `# noqa` - suppress all violations on this line
//! - `# noqa: PINJ001` - suppress specific rule PINJ001 on this line
//! - `# noqa: PINJ001,PINJ002` - suppress multiple specific rules

use std::collections::HashSet;

/// Parsed noqa directive
#[derive(Debug, Clone)]
pub struct NoqaDirective {
    /// Line number (1-based)
    pub line: usize,
    /// Rule IDs to suppress (empty means suppress all)
    pub rule_ids: HashSet<String>,
}

/// Parse noqa directives from source code
pub fn parse_noqa_directives(source: &str) -> Vec<NoqaDirective> {
    let mut directives = Vec::new();

    for (line_idx, line) in source.lines().enumerate() {
        if let Some(directive) = parse_line_for_noqa(line) {
            let mut noqa = directive;
            noqa.line = line_idx + 1; // Convert to 1-based
            directives.push(noqa);
        }
    }

    directives
}

/// Parse a single line for noqa directive
fn parse_line_for_noqa(line: &str) -> Option<NoqaDirective> {
    // Look for # noqa in the line
    let comment_start = line.find('#')?;
    let comment = &line[comment_start..];

    // Check if it contains noqa
    if !comment.to_lowercase().contains("noqa") {
        return None;
    }

    // Find the noqa part
    let noqa_start = comment.to_lowercase().find("noqa")?;
    let noqa_part = &comment[noqa_start..];

    // Check if it's just "noqa" or has specific rules
    if noqa_part.len() == 4 || !noqa_part[4..].trim_start().starts_with(':') {
        // Generic noqa - suppress all
        return Some(NoqaDirective {
            line: 0, // Will be set by caller
            rule_ids: HashSet::new(),
        });
    }

    // Parse specific rules after the colon
    let colon_idx = noqa_part.find(':')?;
    let rules_part = &noqa_part[colon_idx + 1..];

    // Split by comma and trim
    let rule_ids: HashSet<String> = rules_part
        .split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(|s| {
            // Take only the part before any whitespace or end of line
            s.split_whitespace().next().unwrap_or(s).to_string()
        })
        .collect();

    if rule_ids.is_empty() {
        // If colon present but no rules, treat as generic noqa
        Some(NoqaDirective {
            line: 0,
            rule_ids: HashSet::new(),
        })
    } else {
        Some(NoqaDirective { line: 0, rule_ids })
    }
}

/// Check if a violation at a specific line is suppressed by noqa directives
pub fn is_violation_suppressed(line: usize, rule_id: &str, directives: &[NoqaDirective]) -> bool {
    for directive in directives {
        if directive.line == line {
            // If no specific rules, suppress all
            if directive.rule_ids.is_empty() {
                return true;
            }
            // Otherwise check if this specific rule is suppressed
            if directive.rule_ids.contains(rule_id) {
                return true;
            }
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_generic_noqa() {
        let source = r#"
def foo():  # noqa
    pass
"#;
        let directives = parse_noqa_directives(source);
        assert_eq!(directives.len(), 1);
        assert_eq!(directives[0].line, 2);
        assert!(directives[0].rule_ids.is_empty());
    }

    #[test]
    fn test_parse_specific_rule() {
        let source = r#"
def foo():  # noqa: PINJ001
    pass
"#;
        let directives = parse_noqa_directives(source);
        assert_eq!(directives.len(), 1);
        assert_eq!(directives[0].line, 2);
        assert!(directives[0].rule_ids.contains("PINJ001"));
    }

    #[test]
    fn test_parse_multiple_rules() {
        let source = r#"
def foo():  # noqa: PINJ001, PINJ002, PINJ003
    pass
"#;
        let directives = parse_noqa_directives(source);
        assert_eq!(directives.len(), 1);
        assert_eq!(directives[0].line, 2);
        assert_eq!(directives[0].rule_ids.len(), 3);
        assert!(directives[0].rule_ids.contains("PINJ001"));
        assert!(directives[0].rule_ids.contains("PINJ002"));
        assert!(directives[0].rule_ids.contains("PINJ003"));
    }

    #[test]
    fn test_case_insensitive() {
        let source = r#"
def foo():  # NOQA: PINJ001
def bar():  # NoQa
"#;
        let directives = parse_noqa_directives(source);
        assert_eq!(directives.len(), 2);
    }

    #[test]
    fn test_is_violation_suppressed() {
        let directives = vec![
            NoqaDirective {
                line: 5,
                rule_ids: HashSet::new(), // Generic noqa
            },
            NoqaDirective {
                line: 10,
                rule_ids: ["PINJ001".to_string()].into_iter().collect(),
            },
        ];

        // Line 5 suppresses all violations
        assert!(is_violation_suppressed(5, "PINJ001", &directives));
        assert!(is_violation_suppressed(5, "PINJ999", &directives));

        // Line 10 only suppresses PINJ001
        assert!(is_violation_suppressed(10, "PINJ001", &directives));
        assert!(!is_violation_suppressed(10, "PINJ002", &directives));

        // Other lines not suppressed
        assert!(!is_violation_suppressed(1, "PINJ001", &directives));
    }

    #[test]
    fn test_noqa_with_trailing_text() {
        let source = r#"
def foo():  # noqa: PINJ001 - this is okay
def bar():  # noqa - suppress all
"#;
        let directives = parse_noqa_directives(source);
        assert_eq!(directives.len(), 2);
        assert!(directives[0].rule_ids.contains("PINJ001"));
        assert!(!directives[0].rule_ids.contains("-"));
        assert!(directives[1].rule_ids.is_empty());
    }
}
