//! Configuration loading for pinjected-linter
//!
//! Loads configuration from pyproject.toml [tool.pinjected-linter] section

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use toml;

#[derive(Debug, Deserialize, Serialize, Default)]
pub struct Config {
    #[serde(default)]
    pub enable: Vec<String>,

    #[serde(default)]
    pub disable: Vec<String>,

    #[serde(default)]
    pub exclude: Vec<String>,

    #[serde(default)]
    pub max_line_length: Option<usize>,

    #[serde(default)]
    pub check_docstrings: Option<bool>,

    #[serde(default)]
    pub rules: HashMap<String, RuleConfig>,
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub struct RuleConfig {
    // PINJ014 specific
    pub min_injected_functions: Option<usize>,
    pub stub_search_paths: Option<Vec<String>>,
    pub ignore_patterns: Option<Vec<String>>,
}

/// Find pyproject.toml file starting from a path and walking up
pub fn find_pyproject_toml(start_path: &Path) -> Option<PathBuf> {
    let mut current = if start_path.is_file() {
        start_path.parent()?
    } else {
        start_path
    };

    loop {
        let pyproject = current.join("pyproject.toml");
        if pyproject.exists() {
            return Some(pyproject);
        }

        current = current.parent()?;
    }
}

/// Load configuration from pyproject.toml
pub fn load_config(path: Option<&Path>) -> Option<Config> {
    // If specific path provided, use it
    let config_path = if let Some(p) = path {
        if p.exists() {
            p.to_path_buf()
        } else {
            return None;
        }
    } else {
        // Otherwise, search for pyproject.toml with config starting from current directory
        find_config_pyproject_toml(&std::env::current_dir().ok()?)?
    };

    // Read and parse the file
    let content = std::fs::read_to_string(&config_path).ok()?;
    let value: toml::Value = toml::from_str(&content).ok()?;

    // Extract [tool.pinjected-linter] section
    let tool = value.get("tool")?;
    let pinjected_linter = tool.get("pinjected-linter")?;

    // Deserialize into Config
    let config: Config = pinjected_linter.clone().try_into().ok()?;

    Some(config)
}

/// Find pyproject.toml with [tool.pinjected-linter] section
pub fn find_config_pyproject_toml(start_path: &Path) -> Option<PathBuf> {
    let mut current = if start_path.is_file() {
        start_path.parent()?
    } else {
        start_path
    };

    loop {
        let pyproject = current.join("pyproject.toml");
        if pyproject.exists() {
            // Check if this pyproject.toml has [tool.pinjected-linter] section
            if let Ok(content) = std::fs::read_to_string(&pyproject) {
                if let Ok(value) = toml::from_str::<toml::Value>(&content) {
                    if let Some(tool) = value.get("tool") {
                        if tool.get("pinjected-linter").is_some() {
                            return Some(pyproject);
                        }
                    }
                }
            }
        }

        current = current.parent()?;
    }
}

/// Merge command line arguments with config file settings
/// Command line arguments take precedence
pub fn merge_config(
    config: Option<&Config>,
    cli_enable: &[String],
    cli_disable: &[String],
    cli_skip: &[String],
) -> (Option<Vec<String>>, Vec<String>) {
    let mut enable = None;
    let mut exclude = vec![];

    // Start with config file settings
    if let Some(cfg) = config {
        if !cfg.enable.is_empty() && cli_enable.is_empty() && cli_disable.is_empty() {
            enable = Some(cfg.enable.clone());
        }

        if !cfg.disable.is_empty() && cli_enable.is_empty() && cli_disable.is_empty() {
            // Convert disable to enable by filtering
            let all_rules = vec![
                "PINJ001", "PINJ002", "PINJ003", "PINJ004", "PINJ005", "PINJ006", "PINJ007",
                "PINJ009", "PINJ010", "PINJ011", "PINJ012", "PINJ013", "PINJ014", "PINJ015",
                "PINJ016", "PINJ017", "PINJ018",
            ];
            let enabled: Vec<String> = all_rules
                .into_iter()
                .filter(|r| !cfg.disable.contains(&r.to_string()))
                .map(|s| s.to_string())
                .collect();
            enable = Some(enabled);
        }

        exclude = cfg.exclude.clone();
    }

    // Apply CLI overrides
    if !cli_enable.is_empty() {
        enable = Some(cli_enable.to_vec());
    } else if !cli_disable.is_empty() {
        let all_rules = vec![
            "PINJ001", "PINJ002", "PINJ003", "PINJ004", "PINJ005", "PINJ006", "PINJ007", "PINJ008",
            "PINJ009", "PINJ010", "PINJ011", "PINJ012", "PINJ013", "PINJ014", "PINJ015",
        ];
        let enabled: Vec<String> = all_rules
            .into_iter()
            .filter(|r| !cli_disable.contains(&r.to_string()))
            .map(|s| s.to_string())
            .collect();
        enable = Some(enabled);
    }

    // Add CLI skip patterns
    exclude.extend(cli_skip.iter().cloned());

    // Add default excludes if not already present
    let defaults = vec![
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".tox",
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
    ];
    for default in defaults {
        if !exclude.contains(&default.to_string()) {
            exclude.push(default.to_string());
        }
    }

    (enable, exclude)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_find_pyproject_toml() {
        let dir = TempDir::new().unwrap();
        let pyproject_path = dir.path().join("pyproject.toml");
        fs::write(
            &pyproject_path,
            "[tool.pinjected-linter]\nexclude = [\"test\"]",
        )
        .unwrap();

        // From the same directory
        assert_eq!(
            find_pyproject_toml(dir.path()),
            Some(pyproject_path.clone())
        );

        // From a subdirectory
        let subdir = dir.path().join("subdir");
        fs::create_dir(&subdir).unwrap();
        assert_eq!(find_pyproject_toml(&subdir), Some(pyproject_path));
    }

    #[test]
    fn test_find_config_pyproject_toml() {
        let dir = TempDir::new().unwrap();

        // Create a pyproject.toml without [tool.pinjected-linter]
        let subdir = dir.path().join("subproject");
        fs::create_dir(&subdir).unwrap();
        let subproject_toml = subdir.join("pyproject.toml");
        fs::write(&subproject_toml, "[tool.other]\nkey = \"value\"").unwrap();

        // Create parent pyproject.toml with [tool.pinjected-linter]
        let parent_toml = dir.path().join("pyproject.toml");
        fs::write(
            &parent_toml,
            "[tool.pinjected-linter]\nexclude = [\"test\"]",
        )
        .unwrap();

        // Should skip the subproject toml and find parent
        assert_eq!(find_config_pyproject_toml(&subdir), Some(parent_toml));
    }

    #[test]
    fn test_load_config() {
        let dir = TempDir::new().unwrap();
        let pyproject_path = dir.path().join("pyproject.toml");

        let content = r#"
[tool.pinjected-linter]
enable = ["PINJ001", "PINJ002"]
exclude = ["venv", "build"]

[tool.pinjected-linter.rules.PINJ014]
min_injected_functions = 5
"#;
        fs::write(&pyproject_path, content).unwrap();

        let config = load_config(Some(&pyproject_path)).unwrap();
        assert_eq!(config.enable, vec!["PINJ001", "PINJ002"]);
        assert_eq!(config.exclude, vec!["venv", "build"]);
        assert_eq!(config.rules["PINJ014"].min_injected_functions, Some(5));
    }

    #[test]
    fn test_merge_config() {
        let config = Config {
            enable: vec!["PINJ001".to_string()],
            disable: vec![],
            exclude: vec!["custom_dir".to_string()],
            ..Default::default()
        };

        // CLI overrides config
        let (enable, exclude) = merge_config(
            Some(&config),
            &["PINJ002".to_string()],
            &[],
            &["skip_me".to_string()],
        );

        assert_eq!(enable, Some(vec!["PINJ002".to_string()]));
        assert!(exclude.contains(&"custom_dir".to_string()));
        assert!(exclude.contains(&"skip_me".to_string()));
        assert!(exclude.contains(&".venv".to_string())); // Default added
    }
}
