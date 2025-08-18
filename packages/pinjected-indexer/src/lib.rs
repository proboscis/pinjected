pub mod daemon;
pub mod index;
pub mod parser;
pub mod rpc;

pub use index::{EntrypointInfo, TypeIndex};
pub use parser::{InjectedFunction, IProxyVariable};

use anyhow::Result;
use std::path::Path;

/// Build a fresh index from a directory
pub async fn build_index(root: &Path) -> Result<TypeIndex> {
    TypeIndex::build(root).await
}

/// Load index from cache or build fresh
pub async fn load_or_build_index(root: &Path, cache_dir: &Path) -> Result<TypeIndex> {
    TypeIndex::load_or_build(root, cache_dir).await
}