use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::fs;
use tracing::{debug, warn};

/// pyproject.toml structure for UV projects
#[derive(Debug, Deserialize)]
struct PyProject {
    project: Option<ProjectSection>,
    tool: Option<ToolSection>,
}

#[derive(Debug, Deserialize)]
struct ProjectSection {
    name: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ToolSection {
    uv: Option<UvSection>,
}

#[derive(Debug, Deserialize)]
struct UvSection {
    sources: Option<toml::Value>,
}

/// Represents a Python project configuration
#[derive(Debug, Clone)]
pub struct ProjectConfig {
    pub root_dir: PathBuf,
    pub source_dirs: Vec<PathBuf>,
    pub package_name: Option<String>,
}

impl ProjectConfig {
    /// Discover project configuration from a directory
    pub fn discover(root: &Path) -> Result<Self> {
        let root_dir = root.canonicalize().context("Failed to canonicalize root path")?;
        
        // Look for pyproject.toml
        let pyproject_path = root_dir.join("pyproject.toml");
        
        if pyproject_path.exists() {
            debug!("Found pyproject.toml at {:?}", pyproject_path);
            Self::from_pyproject(&pyproject_path)
        } else {
            // Fallback: look for common source directories
            debug!("No pyproject.toml found, using fallback detection");
            Self::fallback_detection(&root_dir)
        }
    }
    
    /// Parse configuration from pyproject.toml
    fn from_pyproject(path: &Path) -> Result<Self> {
        let content = fs::read_to_string(path)?;
        let pyproject: PyProject = toml::from_str(&content)?;
        
        let root_dir = path.parent().unwrap().to_path_buf();
        let package_name = pyproject.project.and_then(|p| p.name);
        
        // Determine source directories
        let mut source_dirs = Vec::new();
        
        // Check if there's a src directory
        let src_dir = root_dir.join("src");
        if src_dir.exists() && src_dir.is_dir() {
            source_dirs.push(src_dir);
        }
        
        // Check for packages/* monorepo structure
        let packages_dir = root_dir.join("packages");
        if packages_dir.exists() && packages_dir.is_dir() {
            // Add each package's src directory
            if let Ok(entries) = fs::read_dir(&packages_dir) {
                for entry in entries {
                    if let Ok(entry) = entry {
                        let pkg_path = entry.path();
                        if pkg_path.is_dir() {
                            let pkg_src = pkg_path.join("src");
                            if pkg_src.exists() && pkg_src.is_dir() {
                                source_dirs.push(pkg_src);
                            }
                        }
                    }
                }
            }
        }
        
        // Add tests directory if it exists (for test modules)
        let tests_dir = root_dir.join("tests");
        if tests_dir.exists() && tests_dir.is_dir() {
            source_dirs.push(tests_dir);
        }
        
        // Check if package exists in root
        if let Some(ref pkg_name) = package_name {
            let pkg_dir = root_dir.join(pkg_name.replace('-', "_"));
            if pkg_dir.exists() && pkg_dir.is_dir() {
                source_dirs.push(root_dir.clone());
            }
        }
        
        // If no source directories found, use root
        if source_dirs.is_empty() {
            source_dirs.push(root_dir.clone());
        }
        
        debug!("Detected source directories: {:?}", source_dirs);
        
        Ok(ProjectConfig {
            root_dir,
            source_dirs,
            package_name,
        })
    }
    
    /// Fallback detection when no pyproject.toml exists
    fn fallback_detection(root_dir: &PathBuf) -> Result<Self> {
        let mut source_dirs = Vec::new();
        
        // Check for src directory
        let src_dir = root_dir.join("src");
        if src_dir.exists() && src_dir.is_dir() {
            source_dirs.push(src_dir);
        } else {
            // Use root directory as source
            source_dirs.push(root_dir.clone());
        }
        
        Ok(ProjectConfig {
            root_dir: root_dir.clone(),
            source_dirs,
            package_name: None,
        })
    }
    
    /// Convert a file path to a Python module path
    pub fn path_to_module(&self, file_path: &Path) -> String {
        let file_path = match file_path.canonicalize() {
            Ok(p) => p,
            Err(_) => file_path.to_path_buf(),
        };
        
        // Try each source directory
        for source_dir in &self.source_dirs {
            if let Ok(source_canonical) = source_dir.canonicalize() {
                if let Ok(relative) = file_path.strip_prefix(&source_canonical) {
                    // Convert path to module notation
                    let module = relative
                        .to_string_lossy()
                        .trim_end_matches(".py")
                        .replace(std::path::MAIN_SEPARATOR, ".")
                        .replace('/', ".")
                        .replace('\\', ".");
                    
                    debug!("Converted {:?} to module: {}", file_path, module);
                    return module;
                }
            }
        }
        
        // Fallback: try to strip common prefixes
        let path_str = file_path.to_string_lossy();
        
        // Strip common development paths
        let module = path_str
            .trim_end_matches(".py")
            .split("/src/")
            .last()
            .unwrap_or(&path_str)
            .replace(std::path::MAIN_SEPARATOR, ".")
            .replace('/', ".")
            .replace('\\', ".");
        
        warn!("Using fallback module path for {:?}: {}", file_path, module);
        module
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;
    
    #[test]
    fn test_path_to_module_with_src() {
        let temp_dir = TempDir::new().unwrap();
        let root = temp_dir.path();
        
        // Create src directory
        let src_dir = root.join("src");
        fs::create_dir(&src_dir).unwrap();
        
        // Create a fake Python file
        let module_path = src_dir.join("mypackage").join("submodule");
        fs::create_dir_all(&module_path).unwrap();
        let file_path = module_path.join("foo.py");
        fs::write(&file_path, "").unwrap();
        
        let config = ProjectConfig::discover(root).unwrap();
        let module = config.path_to_module(&file_path);
        
        assert_eq!(module, "mypackage.submodule.foo");
    }
    
    #[test]
    fn test_path_to_module_with_pyproject() {
        let temp_dir = TempDir::new().unwrap();
        let root = temp_dir.path();
        
        // Create pyproject.toml
        let pyproject = r#"
[project]
name = "test-package"
"#;
        fs::write(root.join("pyproject.toml"), pyproject).unwrap();
        
        // Create src directory
        let src_dir = root.join("src");
        fs::create_dir(&src_dir).unwrap();
        
        let file_path = src_dir.join("test_package").join("main.py");
        fs::create_dir_all(file_path.parent().unwrap()).unwrap();
        fs::write(&file_path, "").unwrap();
        
        let config = ProjectConfig::discover(root).unwrap();
        let module = config.path_to_module(&file_path);
        
        assert_eq!(module, "test_package.main");
    }
}