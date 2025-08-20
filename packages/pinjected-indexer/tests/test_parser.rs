use pinjected_indexer::parser::{parse_python_file, parse_iproxy_variables};
use pinjected_indexer::project::ProjectConfig;
use std::path::Path;

#[tokio::test]
async fn test_parse_injected_functions() {
    let fixture_path = Path::new("tests/fixtures/simple_app.py");
    let project_config = ProjectConfig::discover(Path::new(".")).unwrap();
    let functions = parse_python_file(fixture_path, &project_config).await.unwrap();
    
    // Should find 5 @injected functions
    assert_eq!(functions.len(), 5);
    
    // Check first function
    let visualize = &functions[0];
    assert_eq!(visualize.name, "visualize_user");
    assert_eq!(visualize.parameter_name, "user");
    assert_eq!(visualize.parameter_type, "User");
    assert_eq!(visualize.is_async, false);
    assert!(visualize.docstring.is_some());
    
    // Check async function
    let export = functions.iter()
        .find(|f| f.name == "a_export_user_json")
        .unwrap();
    assert_eq!(export.is_async, true);
    assert_eq!(export.parameter_type, "User");
    
    // Check complex type
    let process = functions.iter()
        .find(|f| f.name == "process_product_list")
        .unwrap();
    assert_eq!(process.parameter_type, "List[Product]");
}

#[tokio::test]
async fn test_parse_iproxy_variables() {
    let fixture_path = Path::new("tests/fixtures/simple_app.py");
    let project_config = ProjectConfig::discover(Path::new(".")).unwrap();
    let variables = parse_iproxy_variables(fixture_path, &project_config).await.unwrap();
    
    // Should find 3 IProxy variables
    assert_eq!(variables.len(), 3);
    
    // Check user_proxy
    let user_proxy = variables.iter()
        .find(|v| v.name == "user_proxy")
        .unwrap();
    assert_eq!(user_proxy.type_parameter, "User");
    
    // Check product_proxy
    let product_proxy = variables.iter()
        .find(|v| v.name == "product_proxy")
        .unwrap();
    assert_eq!(product_proxy.type_parameter, "Product");
    
    // Check items_proxy with generic type
    let items_proxy = variables.iter()
        .find(|v| v.name == "items_proxy")
        .unwrap();
    assert_eq!(items_proxy.type_parameter, "List[Product]");
}

#[tokio::test]
async fn test_no_injected_functions() {
    // Create a temp file without @injected
    let content = r#"
def regular_function():
    return "hello"
    
class MyClass:
    def method(self):
        pass
"#;
    
    let temp_dir = tempfile::tempdir().unwrap();
    let temp_file = temp_dir.path().join("no_injected.py");
    std::fs::write(&temp_file, content).unwrap();
    
    let project_config = ProjectConfig::discover(temp_dir.path()).unwrap();
    let functions = parse_python_file(&temp_file, &project_config).await.unwrap();
    assert_eq!(functions.len(), 0);
}

#[tokio::test]
async fn test_no_iproxy_variables() {
    // Create a temp file without IProxy
    let content = r#"
from typing import List

user: User = User()
items: List[str] = []
"#;
    
    let temp_dir = tempfile::tempdir().unwrap();
    let temp_file = temp_dir.path().join("no_iproxy.py");
    std::fs::write(&temp_file, content).unwrap();
    
    let project_config = ProjectConfig::discover(temp_dir.path()).unwrap();
    let variables = parse_iproxy_variables(&temp_file, &project_config).await.unwrap();
    assert_eq!(variables.len(), 0);
}