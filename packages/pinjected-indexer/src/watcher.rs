use anyhow::Result;
use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::mpsc;
use tracing::{debug, error, info, warn};

use crate::index::TypeIndex;

/// File watcher that monitors Python files and triggers reindexing
pub struct FileWatcher {
    project_root: PathBuf,
    index: Arc<TypeIndex>,
    watcher: RecommendedWatcher,
    rx: mpsc::UnboundedReceiver<WatchEvent>,
}

#[derive(Debug)]
enum WatchEvent {
    FileChanged(PathBuf),
    FileCreated(PathBuf),
    FileRemoved(PathBuf),
}

impl FileWatcher {
    /// Create a new file watcher
    pub fn new(project_root: PathBuf, index: Arc<TypeIndex>) -> Result<Self> {
        let (tx, rx) = mpsc::unbounded_channel();
        
        // Create notify watcher
        let tx_clone = tx.clone();
        let watcher = RecommendedWatcher::new(
            move |result: Result<Event, notify::Error>| {
                match result {
                    Ok(event) => {
                        if let Some(watch_event) = process_event(event) {
                            let _ = tx_clone.send(watch_event);
                        }
                    }
                    Err(e) => error!("Watch error: {}", e),
                }
            },
            Config::default().with_poll_interval(Duration::from_secs(1)),
        )?;
        
        Ok(FileWatcher {
            project_root,
            index,
            watcher,
            rx,
        })
    }
    
    /// Start watching for file changes
    pub async fn start(mut self) -> Result<()> {
        // Start watching the project root
        self.watcher.watch(&self.project_root, RecursiveMode::Recursive)?;
        info!("Started watching {:?} for Python file changes", self.project_root);
        
        // Process events
        while let Some(event) = self.rx.recv().await {
            match event {
                WatchEvent::FileChanged(path) | WatchEvent::FileCreated(path) => {
                    if is_python_file(&path) {
                        debug!("Python file changed/created: {:?}", path);
                        if let Err(e) = self.index.reindex_file(&path).await {
                            warn!("Failed to reindex {:?}: {}", path, e);
                        } else {
                            info!("Reindexed {:?}", path);
                        }
                    }
                }
                WatchEvent::FileRemoved(path) => {
                    if is_python_file(&path) {
                        debug!("Python file removed: {:?}", path);
                        self.index.remove_file(&path).await;
                        info!("Removed {:?} from index", path);
                    }
                }
            }
        }
        
        Ok(())
    }
}

/// Process notify events into our watch events
fn process_event(event: Event) -> Option<WatchEvent> {
    match event.kind {
        EventKind::Create(_) => {
            event.paths.first().map(|p| WatchEvent::FileCreated(p.clone()))
        }
        EventKind::Modify(_) => {
            event.paths.first().map(|p| WatchEvent::FileChanged(p.clone()))
        }
        EventKind::Remove(_) => {
            event.paths.first().map(|p| WatchEvent::FileRemoved(p.clone()))
        }
        _ => None,
    }
}

/// Check if a path is a Python file
fn is_python_file(path: &Path) -> bool {
    path.extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| ext == "py")
        .unwrap_or(false)
        && !is_ignored_path(path)
}

/// Check if path should be ignored
fn is_ignored_path(path: &Path) -> bool {
    // Ignore common directories
    for component in path.components() {
        if let Some(name) = component.as_os_str().to_str() {
            if name.starts_with('.')
                || name == "__pycache__"
                || name == "venv"
                || name == "env"
                || name == ".venv"
                || name == "node_modules"
                || name == "build"
                || name == "dist"
            {
                return true;
            }
        }
    }
    false
}