pub mod line_index;

use anyhow::Result;
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::SystemTime;
use tracing::{debug, info};
use std::collections::HashMap;

use crate::parser::parse_python_file;
pub use line_index::LineIndex;

/// Information about an entrypoint function
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntrypointInfo {
    pub function_name: String,
    pub module_path: String,
    pub file_path: PathBuf,
    pub line_number: usize,
    pub parameter_name: String,
    pub parameter_type: String,
    pub docstring: Option<String>,
    pub is_async: bool,
}

/// Statistics about the index
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexStats {
    pub total_functions: usize,
    pub total_types: usize,
    pub indexed_files: usize,
    pub last_updated: SystemTime,
}

/// Main type index for fast lookups
#[derive(Clone)]
pub struct TypeIndex {
    /// Type name -> List of entrypoints
    entries: Arc<DashMap<String, Vec<EntrypointInfo>>>,
    
    /// File path -> Functions in that file (for incremental updates)
    file_index: Arc<DashMap<PathBuf, Vec<String>>>,
    
    /// Statistics
    stats: Arc<parking_lot::RwLock<IndexStats>>,
}

impl TypeIndex {
    /// Create a new empty index
    pub fn new() -> Self {
        Self {
            entries: Arc::new(DashMap::new()),
            file_index: Arc::new(DashMap::new()),
            stats: Arc::new(parking_lot::RwLock::new(IndexStats {
                total_functions: 0,
                total_types: 0,
                indexed_files: 0,
                last_updated: SystemTime::now(),
            })),
        }
    }
    
    /// Build index from a directory
    pub async fn build(root: &Path) -> Result<Self> {
        info!("Building index for {:?}", root);
        let index = Self::new();
        
        // Find all Python files
        let python_files = find_python_files(root)?;
        info!("Found {} Python files", python_files.len());
        
        // Parse each file
        for file_path in python_files {
            if let Err(e) = index.index_file(&file_path).await {
                debug!("Failed to index {:?}: {}", file_path, e);
            }
        }
        
        // Update stats
        {
            let mut stats = index.stats.write();
            stats.total_functions = index.count_functions();
            stats.total_types = index.entries.len();
            stats.last_updated = SystemTime::now();
            info!("Index built: {} types, {} functions", stats.total_types, stats.total_functions);
        }
        
        Ok(index)
    }
    
    /// Load from cache or build fresh
    pub async fn load_or_build(root: &Path, cache_dir: &Path) -> Result<Self> {
        let cache_file = cache_dir.join("index.bin");
        
        // Try to load from cache
        if cache_file.exists() {
            if let Ok(index) = Self::load_from_cache(&cache_file).await {
                info!("Loaded index from cache");
                return Ok(index);
            }
        }
        
        // Build fresh
        let index = Self::build(root).await?;
        
        // Save to cache
        if let Err(e) = index.save_to_cache(&cache_file).await {
            debug!("Failed to save cache: {}", e);
        }
        
        Ok(index)
    }
    
    /// Index a single file
    async fn index_file(&self, file_path: &Path) -> Result<()> {
        debug!("Indexing {:?}", file_path);
        
        // Parse the file
        let functions = parse_python_file(file_path).await?;
        
        // Remove old entries for this file
        if let Some((_, old_types)) = self.file_index.remove(file_path) {
            for type_name in old_types {
                if let Some(mut entries) = self.entries.get_mut(&type_name) {
                    entries.retain(|e| e.file_path != file_path);
                }
            }
        }
        
        // Add new entries
        let mut file_types = Vec::new();
        
        for func in functions {
            let entry = EntrypointInfo {
                function_name: func.name.clone(),
                module_path: func.module_path.clone(),
                file_path: file_path.to_path_buf(),
                line_number: func.line_number,
                parameter_name: func.parameter_name.clone(),
                parameter_type: func.parameter_type.clone(),
                docstring: func.docstring,
                is_async: func.is_async,
            };
            
            // Add to type index
            let type_name = func.parameter_type.clone();
            self.entries.entry(type_name.clone())
                .or_insert_with(Vec::new)
                .push(entry);
            
            file_types.push(type_name);
        }
        
        // Update file index
        if !file_types.is_empty() {
            self.file_index.insert(file_path.to_path_buf(), file_types);
        }
        
        // Update stats
        let mut stats = self.stats.write();
        stats.indexed_files = self.file_index.len();
        
        Ok(())
    }
    
    /// Query entrypoints for a type
    pub fn query_type(&self, type_name: &str) -> Vec<EntrypointInfo> {
        debug!("Querying type: {}", type_name);
        
        // Try exact match first
        if let Some(entries) = self.entries.get(type_name) {
            return entries.clone();
        }
        
        // Try case-insensitive match
        for entry in self.entries.iter() {
            if entry.key().eq_ignore_ascii_case(type_name) {
                return entry.value().clone();
            }
        }
        
        // Try suffix match (e.g., "User" matches "myapp.models.User")
        let mut results = Vec::new();
        for entry in self.entries.iter() {
            if entry.key().ends_with(&format!(".{}", type_name)) || 
               entry.key() == type_name {
                results.extend(entry.value().clone());
            }
        }
        
        results
    }
    
    /// Get index statistics
    pub fn get_stats(&self) -> IndexStats {
        self.stats.read().clone()
    }
    
    /// Count total functions
    fn count_functions(&self) -> usize {
        self.entries.iter().map(|e| e.value().len()).sum()
    }
    
    /// Save to cache file
    pub async fn save_to_cache(&self, cache_file: &Path) -> Result<()> {
        // Create cache directory if needed
        if let Some(parent) = cache_file.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        
        // Serialize entries - convert to HashMap for serialization
        let entries: HashMap<String, Vec<EntrypointInfo>> = 
            self.entries.iter().map(|e| (e.key().clone(), e.value().clone())).collect();
        
        let data = bincode::serialize(&entries)?;
        tokio::fs::write(cache_file, data).await?;
        
        Ok(())
    }
    
    /// Load from cache file
    pub async fn load_from_cache(cache_file: &Path) -> Result<Self> {
        let data = tokio::fs::read(cache_file).await?;
        let entries: HashMap<String, Vec<EntrypointInfo>> = bincode::deserialize(&data)?;
        
        let index = Self::new();
        for (type_name, funcs) in entries {
            index.entries.insert(type_name, funcs);
        }
        
        // Update stats after loading
        {
            let mut stats = index.stats.write();
            stats.total_functions = index.count_functions();
            stats.total_types = index.entries.len();
            stats.last_updated = SystemTime::now();
        }
        
        Ok(index)
    }
}

/// Find all Python files in a directory
fn find_python_files(root: &Path) -> Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    find_python_files_recursive(root, &mut files)?;
    Ok(files)
}

fn find_python_files_recursive(dir: &Path, files: &mut Vec<PathBuf>) -> Result<()> {
    if !dir.is_dir() {
        return Ok(());
    }
    
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        
        // Skip hidden directories and __pycache__
        if let Some(name) = path.file_name() {
            let name_str = name.to_string_lossy();
            if name_str.starts_with('.') || name_str == "__pycache__" {
                continue;
            }
        }
        
        if path.is_dir() {
            find_python_files_recursive(&path, files)?;
        } else if path.extension() == Some(std::ffi::OsStr::new("py")) {
            files.push(path);
        }
    }
    
    Ok(())
}