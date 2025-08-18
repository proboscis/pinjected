use pinjected_indexer::parser::parse_python_file;
use std::path::Path;

#[tokio::test]
async fn test_parameter_validation_rules() {
    let fixture_path = Path::new("tests/fixtures/parameter_validation.py");
    let functions = parse_python_file(fixture_path).await.unwrap();
    
    // Should find only the VALID functions
    let valid_names: Vec<String> = functions.iter()
        .map(|f| f.name.clone())
        .collect();
    
    // Valid functions (exactly one param without default)
    assert!(valid_names.contains(&"valid_single_param".to_string()), 
            "Should find valid_single_param");
    assert!(valid_names.contains(&"valid_with_many_defaults".to_string()),
            "Should find valid_with_many_defaults");
    assert!(valid_names.contains(&"valid_minimal".to_string()),
            "Should find valid_minimal");
    assert!(valid_names.contains(&"edge_complex_type".to_string()),
            "Should find edge_complex_type");
    assert!(valid_names.contains(&"a_valid_async".to_string()),
            "Should find a_valid_async");
    
    // Invalid functions should NOT be found
    assert!(!valid_names.contains(&"invalid_two_params".to_string()),
            "Should NOT find invalid_two_params (2 params without defaults)");
    assert!(!valid_names.contains(&"invalid_three_params".to_string()),
            "Should NOT find invalid_three_params (3 params without defaults)");
    assert!(!valid_names.contains(&"invalid_no_params".to_string()),
            "Should NOT find invalid_no_params (no params)");
    assert!(!valid_names.contains(&"invalid_all_defaults".to_string()),
            "Should NOT find invalid_all_defaults (all have defaults)");
    assert!(!valid_names.contains(&"a_invalid_async".to_string()),
            "Should NOT find a_invalid_async (2 params without defaults)");
    
    // Should find exactly 5 valid functions
    assert_eq!(functions.len(), 5, 
               "Should find exactly 5 valid functions, found: {:?}", valid_names);
}

#[tokio::test]
async fn test_extracted_parameter_types() {
    let fixture_path = Path::new("tests/fixtures/parameter_validation.py");
    let functions = parse_python_file(fixture_path).await.unwrap();
    
    // Check that we extracted the correct parameter for each valid function
    for func in &functions {
        match func.name.as_str() {
            "valid_single_param" => {
                assert_eq!(func.parameter_name, "x");
                assert_eq!(func.parameter_type, "User");
            },
            "valid_with_many_defaults" => {
                assert_eq!(func.parameter_name, "product");
                assert_eq!(func.parameter_type, "Product");
            },
            "valid_minimal" => {
                assert_eq!(func.parameter_name, "user");
                assert_eq!(func.parameter_type, "User");
            },
            "edge_complex_type" => {
                assert_eq!(func.parameter_name, "data");
                assert_eq!(func.parameter_type, "dict[str, User]");
            },
            "a_valid_async" => {
                assert_eq!(func.parameter_name, "user");
                assert_eq!(func.parameter_type, "User");
                assert!(func.is_async);
            },
            _ => panic!("Unexpected function found: {}", func.name),
        }
    }
}