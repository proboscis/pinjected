use anyhow::Result;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use tracing::{info, warn};

use crate::index::TypeIndex;
use crate::rpc::RpcServer;

/// Configuration for the daemon
#[derive(Clone)]
pub struct DaemonConfig {
    pub socket_path: PathBuf,
    pub pid_file: PathBuf,
    pub cache_dir: PathBuf,
    pub idle_timeout: Duration,
    pub project_root: PathBuf,
}

impl Default for DaemonConfig {
    fn default() -> Self {
        let runtime_dir = dirs::cache_dir()
            .unwrap_or_else(|| PathBuf::from(".cache"))
            .join("pinjected")
            .join("indexer");
        
        Self {
            socket_path: runtime_dir.join("indexer.sock"),
            pid_file: runtime_dir.join("indexer.pid"),
            cache_dir: runtime_dir.join("cache"),
            idle_timeout: Duration::from_secs(300), // 5 minutes
            project_root: PathBuf::from("."),
        }
    }
}

/// Main daemon that manages the indexer lifecycle
pub struct IndexerDaemon {
    config: DaemonConfig,
    index: Arc<TypeIndex>,
    last_activity: Arc<RwLock<Instant>>,
}

impl IndexerDaemon {
    /// Create and run the daemon
    pub async fn run(config: DaemonConfig) -> Result<()> {
        info!("Starting indexer daemon");
        
        // Create runtime directory
        if let Some(parent) = config.socket_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        
        // Write PID file
        tokio::fs::write(&config.pid_file, std::process::id().to_string()).await?;
        info!("PID file written to {:?}", config.pid_file);
        
        // Setup cleanup on exit
        let pid_file = config.pid_file.clone();
        let socket_path = config.socket_path.clone();
        ctrlc::set_handler(move || {
            let _ = std::fs::remove_file(&pid_file);
            let _ = std::fs::remove_file(&socket_path);
            info!("Cleaned up PID and socket files");
            std::process::exit(0);
        })?;
        
        // Load or build index
        info!("Loading index from {:?}", config.project_root);
        let index = Arc::new(
            TypeIndex::load_or_build(&config.project_root, &config.cache_dir).await?
        );
        
        let daemon = Arc::new(IndexerDaemon {
            config: config.clone(),
            index: index.clone(),
            last_activity: Arc::new(RwLock::new(Instant::now())),
        });
        
        // Start idle checker
        let daemon_clone = daemon.clone();
        tokio::spawn(async move {
            daemon_clone.idle_checker().await;
        });
        
        // Start RPC server
        let server = Arc::new(RpcServer::new(index));
        
        // Start listening
        server.listen_unix(&config.socket_path).await?;
        
        Ok(())
    }
    
    /// Check for idle timeout and shutdown if needed
    async fn idle_checker(&self) {
        loop {
            tokio::time::sleep(Duration::from_secs(30)).await;
            
            let last_activity = *self.last_activity.read().await;
            let idle_duration = last_activity.elapsed();
            
            if idle_duration > self.config.idle_timeout {
                info!("Idle timeout reached ({:?}), shutting down", idle_duration);
                
                // Save cache
                if let Err(e) = self.save_and_cleanup().await {
                    warn!("Error during cleanup: {}", e);
                }
                
                // Exit gracefully
                std::process::exit(0);
            }
        }
    }
    
    /// Save cache and clean up files
    async fn save_and_cleanup(&self) -> Result<()> {
        // Cache is automatically saved by TypeIndex
        info!("Saving cache to {:?}", self.config.cache_dir);
        
        // Remove PID file
        if self.config.pid_file.exists() {
            tokio::fs::remove_file(&self.config.pid_file).await?;
        }
        
        // Remove socket file
        if self.config.socket_path.exists() {
            tokio::fs::remove_file(&self.config.socket_path).await?;
        }
        
        info!("Cleanup completed");
        Ok(())
    }
}

// Note: Activity tracking is handled in the idle_checker
// In production, we'd integrate activity tracking into RpcServer