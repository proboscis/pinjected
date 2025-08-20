use pinjected_indexer::project::ProjectConfig;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_discover_with_pyproject_toml() {
    let temp_dir = TempDir::new().unwrap();
    let root = temp_dir.path();
    
    // Create pyproject.toml
    let pyproject_content = r#"
[project]
name = "test-package"

[tool.uv]
sources = {}
"#;
    fs::write(root.join("pyproject.toml"), pyproject_content).unwrap();
    
    // Create src directory structure
    let src_dir = root.join("src");
    fs::create_dir(&src_dir).unwrap();
    let src_dir = src_dir.canonicalize().unwrap();  // Canonicalize for comparison
    let package_dir = src_dir.join("test_package");
    fs::create_dir(&package_dir).unwrap();
    
    // Test discovery
    let config = ProjectConfig::discover(root).unwrap();
    
    assert_eq!(config.package_name, Some("test-package".to_string()));
    assert!(config.source_dirs.contains(&src_dir), "Expected src_dir {:?} in source_dirs {:?}", src_dir, config.source_dirs);
}

#[test]
fn test_path_to_module_with_src_directory() {
    let temp_dir = TempDir::new().unwrap();
    let root = temp_dir.path();
    
    // Create src directory structure
    let src_dir = root.join("src");
    fs::create_dir(&src_dir).unwrap();
    let package_dir = src_dir.join("mypackage");
    fs::create_dir(&package_dir).unwrap();
    let submodule_dir = package_dir.join("submodule");
    fs::create_dir(&submodule_dir).unwrap();
    
    // Create Python file
    let file_path = submodule_dir.join("foo.py");
    fs::write(&file_path, "# test file").unwrap();
    
    // Test module path conversion
    let config = ProjectConfig::discover(root).unwrap();
    let module_path = config.path_to_module(&file_path);
    
    assert_eq!(module_path, "mypackage.submodule.foo");
}

#[test]
fn test_path_to_module_without_src_directory() {
    let temp_dir = TempDir::new().unwrap();
    let root = temp_dir.path();
    
    // Create package directly in root
    let package_dir = root.join("mypackage");
    fs::create_dir(&package_dir).unwrap();
    let submodule_dir = package_dir.join("submodule");
    fs::create_dir(&submodule_dir).unwrap();
    
    // Create Python file
    let file_path = submodule_dir.join("module.py");
    fs::write(&file_path, "# test file").unwrap();
    
    // Test module path conversion
    let config = ProjectConfig::discover(root).unwrap();
    let module_path = config.path_to_module(&file_path);
    
    assert_eq!(module_path, "mypackage.submodule.module");
}

#[test]
fn test_path_to_module_strips_py_extension() {
    let temp_dir = TempDir::new().unwrap();
    let root = temp_dir.path();
    
    // Create simple structure
    let file_path = root.join("test_module.py");
    fs::write(&file_path, "# test").unwrap();
    
    let config = ProjectConfig::discover(root).unwrap();
    let module_path = config.path_to_module(&file_path);
    
    assert_eq!(module_path, "test_module");
}

#[test]
fn test_path_to_module_handles_nested_paths() {
    let temp_dir = TempDir::new().unwrap();
    let root = temp_dir.path();
    
    // Create pyproject.toml with package name
    let pyproject_content = r#"
[project]
name = "sge-hub"
"#;
    fs::write(root.join("pyproject.toml"), pyproject_content).unwrap();
    
    // Create src/sge_hub structure (typical UV project)
    let src_dir = root.join("src");
    fs::create_dir(&src_dir).unwrap();
    let package_dir = src_dir.join("sge_hub");
    fs::create_dir(&package_dir).unwrap();
    let services_dir = package_dir.join("services");
    fs::create_dir(&services_dir).unwrap();
    let auth_dir = services_dir.join("auth");
    fs::create_dir(&auth_dir).unwrap();
    
    // Create a deeply nested file
    let file_path = auth_dir.join("token_manager.py");
    fs::write(&file_path, "# token manager").unwrap();
    
    let config = ProjectConfig::discover(root).unwrap();
    let module_path = config.path_to_module(&file_path);
    
    assert_eq!(module_path, "sge_hub.services.auth.token_manager");
}

#[test]
fn test_fallback_detection_without_pyproject() {
    let temp_dir = TempDir::new().unwrap();
    let root = temp_dir.path();
    
    // No pyproject.toml, but has src directory
    let src_dir = root.join("src");
    fs::create_dir(&src_dir).unwrap();
    let src_dir = src_dir.canonicalize().unwrap();  // Canonicalize for comparison
    
    let config = ProjectConfig::discover(root).unwrap();
    
    assert!(config.source_dirs.contains(&src_dir), "Expected src_dir {:?} in source_dirs {:?}", src_dir, config.source_dirs);
    assert_eq!(config.package_name, None);
}

#[test]
fn test_module_path_with_init_file() {
    let temp_dir = TempDir::new().unwrap();
    let root = temp_dir.path();
    
    let package_dir = root.join("mypackage");
    fs::create_dir(&package_dir).unwrap();
    
    // Test __init__.py
    let init_file = package_dir.join("__init__.py");
    fs::write(&init_file, "# init").unwrap();
    
    let config = ProjectConfig::discover(root).unwrap();
    let module_path = config.path_to_module(&init_file);
    
    assert_eq!(module_path, "mypackage.__init__");
}