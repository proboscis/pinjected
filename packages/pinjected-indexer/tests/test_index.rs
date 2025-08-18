use pinjected_indexer::TypeIndex;
use std::path::Path;
use tempfile::TempDir;

#[tokio::test]
async fn test_build_index() {
    let fixture_dir = Path::new("tests/fixtures");
    let index = TypeIndex::build(fixture_dir).await.unwrap();
    
    let stats = index.get_stats();
    assert!(stats.total_functions > 0);
    assert!(stats.total_types > 0);
    assert!(stats.indexed_files > 0);
}

#[tokio::test]
async fn test_query_type_exact_match() {
    let fixture_dir = Path::new("tests/fixtures");
    let index = TypeIndex::build(fixture_dir).await.unwrap();
    
    // Query for User type
    let user_entries = index.query_type("User");
    assert!(user_entries.len() >= 2); // visualize_user and validate_user_data
    
    // Check that we found the right functions
    let names: Vec<String> = user_entries.iter()
        .map(|e| e.function_name.clone())
        .collect();
    assert!(names.contains(&"visualize_user".to_string()));
    assert!(names.contains(&"validate_user_data".to_string()));
}

#[tokio::test]
async fn test_query_type_case_insensitive() {
    let fixture_dir = Path::new("tests/fixtures");
    let index = TypeIndex::build(fixture_dir).await.unwrap();
    
    // Query with different case
    let entries = index.query_type("user");
    assert!(entries.len() >= 2);
    
    let entries = index.query_type("USER");
    assert!(entries.len() >= 2);
}

#[tokio::test]
async fn test_query_generic_type() {
    let fixture_dir = Path::new("tests/fixtures");
    let index = TypeIndex::build(fixture_dir).await.unwrap();
    
    // Query for List[Product]
    let entries = index.query_type("List[Product]");
    assert!(entries.len() >= 1);
    
    let function = &entries[0];
    assert_eq!(function.function_name, "process_product_list");
}

#[tokio::test]
async fn test_cache_save_and_load() {
    let fixture_dir = Path::new("tests/fixtures");
    let temp_dir = TempDir::new().unwrap();
    let cache_dir = temp_dir.path();
    
    // Build and save
    let index1 = TypeIndex::build(fixture_dir).await.unwrap();
    let stats1 = index1.get_stats();
    
    // Save to cache
    let cache_file = cache_dir.join("test_cache.bin");
    index1.save_to_cache(&cache_file).await.unwrap();
    
    // Load from cache
    let index2 = TypeIndex::load_from_cache(&cache_file).await.unwrap();
    let stats2 = index2.get_stats();
    
    // Should have same data
    assert_eq!(stats1.total_functions, stats2.total_functions);
    assert_eq!(stats1.total_types, stats2.total_types);
    
    // Query should work
    let entries = index2.query_type("User");
    assert!(entries.len() >= 2);
}

#[tokio::test]
async fn test_empty_directory() {
    let temp_dir = TempDir::new().unwrap();
    let index = TypeIndex::build(temp_dir.path()).await.unwrap();
    
    let stats = index.get_stats();
    assert_eq!(stats.total_functions, 0);
    assert_eq!(stats.total_types, 0);
    assert_eq!(stats.indexed_files, 0);
    
    // Query should return empty
    let entries = index.query_type("User");
    assert_eq!(entries.len(), 0);
}