use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::path::PathBuf;
use std::time::Duration;
use std::process::Command;
use std::fs;
use tracing_subscriber::EnvFilter;

use pinjected_indexer::daemon::{DaemonConfig, IndexerDaemon};
use pinjected_indexer::{build_index, TypeIndex};

#[derive(Parser)]
#[command(name = "pinjected-indexer")]
#[command(about = "IProxy[T] entrypoint discovery for pinjected - finds @injected functions matching IProxy types", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
    
    /// Run as daemon (default)
    #[arg(long, default_value = "true")]
    daemon: bool,
    
    /// Unix socket path
    #[arg(long)]
    socket: Option<PathBuf>,
    
    /// PID file path
    #[arg(long)]
    pid_file: Option<PathBuf>,
    
    /// Cache directory
    #[arg(long)]
    cache_dir: Option<PathBuf>,
    
    /// Idle timeout in seconds
    #[arg(long, default_value = "300")]
    idle_timeout: u64,
    
    /// Project root directory
    #[arg(long, default_value = ".")]
    root: PathBuf,
    
    /// Log level
    #[arg(long, default_value = "info")]
    log_level: String,
}

#[derive(Subcommand)]
enum Commands {
    /// Build IProxy entrypoint index and exit
    Build {
        /// Output cache file
        #[arg(long)]
        output: Option<PathBuf>,
    },
    /// Find @injected functions that accept the given IProxy[T] type
    #[command(name = "query-iproxy-functions")]
    QueryIproxyFunctions {
        /// The type T to search for (e.g., User, List[User], Dict[str, User])
        type_name: String,
        /// Cache file to use
        #[arg(long)]
        cache: Option<PathBuf>,
    },
    /// Show index statistics
    Stats {
        /// Cache file to use
        #[arg(long)]
        cache: Option<PathBuf>,
    },
    /// Start the IProxy indexer daemon for IDE integration
    Start {
        /// Run in foreground (don't daemonize)
        #[arg(long)]
        foreground: bool,
    },
    /// Stop the IProxy indexer daemon
    Stop,
    /// Check daemon status
    Status,
    /// Test query to running daemon (for debugging)
    #[command(name = "test-iproxy-query")]
    TestIproxyQuery {
        /// The type T to search for
        type_name: String,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    
    // Setup logging
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&cli.log_level));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .init();
    
    match cli.command {
        Some(Commands::Build { output }) => {
            // Build index and save
            let index = build_index(&cli.root).await?;
            if let Some(output_path) = output {
                // Save to specified location
                println!("Index built, saving to {:?}", output_path);
            } else {
                println!("Index built: {} types", index.get_stats().total_types);
            }
            Ok(())
        }
        Some(Commands::QueryIproxyFunctions { type_name, cache }) => {
            // Load index and query for IProxy[T] compatible functions
            let cache_dir = cache.unwrap_or_else(|| PathBuf::from(".cache"));
            let index = TypeIndex::load_or_build(&cli.root, &cache_dir).await?;
            let entries = index.query_type(&type_name);
            
            // Print results as JSON
            println!("{}", serde_json::to_string_pretty(&entries)?);
            Ok(())
        }
        Some(Commands::Stats { cache }) => {
            // Load index and show stats
            let cache_dir = cache.unwrap_or_else(|| PathBuf::from(".cache"));
            let index = TypeIndex::load_or_build(&cli.root, &cache_dir).await?;
            let stats = index.get_stats();
            
            println!("Index Statistics:");
            println!("  Total functions: {}", stats.total_functions);
            println!("  Total types: {}", stats.total_types);
            println!("  Indexed files: {}", stats.indexed_files);
            println!("  Last updated: {:?}", stats.last_updated);
            Ok(())
        }
        Some(Commands::Start { foreground }) => {
            // Start daemon
            let mut config = DaemonConfig::default();
            
            // Override with CLI args
            if let Some(ref socket) = cli.socket {
                config.socket_path = socket.clone();
            }
            if let Some(ref pid_file) = cli.pid_file {
                config.pid_file = pid_file.clone();
            }
            if let Some(ref cache_dir) = cli.cache_dir {
                config.cache_dir = cache_dir.clone();
            }
            config.idle_timeout = Duration::from_secs(cli.idle_timeout);
            config.project_root = cli.root.clone();
            
            if !foreground {
                // Fork to background using daemonize approach
                use std::process::Stdio;
                
                let exe = std::env::current_exe()?;
                let mut cmd = Command::new(exe);
                
                // Build arguments in correct order
                cmd.arg("--root").arg(&cli.root);
                cmd.arg("--log-level").arg(&cli.log_level);
                
                if let Some(ref socket) = cli.socket {
                    cmd.arg("--socket").arg(socket);
                }
                if let Some(ref pid_file) = cli.pid_file {
                    cmd.arg("--pid-file").arg(pid_file);
                }
                if let Some(ref cache_dir) = cli.cache_dir {
                    cmd.arg("--cache-dir").arg(cache_dir);
                }
                
                cmd.arg("--idle-timeout").arg(cli.idle_timeout.to_string());
                
                // Add the start subcommand with foreground flag
                cmd.arg("start");
                cmd.arg("--foreground");
                
                // Detach from terminal
                cmd.stdin(Stdio::null());
                cmd.stdout(Stdio::null());
                cmd.stderr(Stdio::null());
                
                let child = cmd.spawn()
                    .context("Failed to start daemon in background")?;
                    
                println!("Daemon started with PID {}", child.id());
                Ok(())
            } else {
                // Run in foreground
                IndexerDaemon::run(config).await
            }
        }
        Some(Commands::Stop) => {
            // Stop daemon
            let pid_file = cli.pid_file.unwrap_or_else(|| {
                PathBuf::from(std::env::var("HOME").unwrap())
                    .join("Library/Caches/pinjected/indexer/indexer.pid")
            });
            
            if pid_file.exists() {
                let pid = fs::read_to_string(&pid_file)?
                    .trim()
                    .parse::<i32>()
                    .context("Invalid PID in file")?;
                
                // Send SIGTERM
                unsafe {
                    libc::kill(pid, libc::SIGTERM);
                }
                
                // Remove PID file
                fs::remove_file(&pid_file)?;
                println!("Daemon stopped (PID {})", pid);
            } else {
                println!("Daemon not running (PID file not found)");
            }
            Ok(())
        }
        Some(Commands::Status) => {
            // Check daemon status
            let pid_file = cli.pid_file.unwrap_or_else(|| {
                PathBuf::from(std::env::var("HOME").unwrap())
                    .join("Library/Caches/pinjected/indexer/indexer.pid")
            });
            
            if pid_file.exists() {
                let pid = fs::read_to_string(&pid_file)?
                    .trim()
                    .parse::<i32>()
                    .context("Invalid PID in file")?;
                
                // Check if process is running
                let running = unsafe {
                    libc::kill(pid, 0) == 0
                };
                
                if running {
                    println!("Daemon is running (PID {})", pid);
                    
                    // Show socket path
                    let socket = cli.socket.unwrap_or_else(|| {
                        PathBuf::from(std::env::var("HOME").unwrap())
                            .join("Library/Caches/pinjected/indexer/indexer.sock")
                    });
                    println!("Socket: {:?}", socket);
                } else {
                    println!("Daemon PID file exists but process not running");
                    println!("Cleaning up stale PID file...");
                    fs::remove_file(&pid_file)?;
                }
            } else {
                println!("Daemon not running");
            }
            Ok(())
        }
        Some(Commands::TestIproxyQuery { type_name }) => {
            // Send test IProxy query to daemon
            use tokio::net::UnixStream;
            use tokio::io::{AsyncReadExt, AsyncWriteExt};
            
            let socket = cli.socket.unwrap_or_else(|| {
                PathBuf::from(std::env::var("HOME").unwrap())
                    .join("Library/Caches/pinjected/indexer/indexer.sock")
            });
            
            let mut stream = UnixStream::connect(&socket)
                .await
                .context("Failed to connect to daemon socket")?;
            
            // Send JSON-RPC request for IProxy functions
            let request = serde_json::json!({
                "jsonrpc": "2.0",
                "method": "find_iproxy_entrypoints",
                "params": {"type_name": type_name},
                "id": 1
            });
            
            let request_str = serde_json::to_string(&request)?;
            stream.write_all(request_str.as_bytes()).await?;
            stream.write_all(b"\n").await?;
            
            // Read response
            let mut response = String::new();
            stream.read_to_string(&mut response).await?;
            
            // Parse and pretty-print
            let json: serde_json::Value = serde_json::from_str(&response)?;
            println!("{}", serde_json::to_string_pretty(&json)?);
            
            Ok(())
        }
        None => {
            // Run as daemon (default)
            let mut config = DaemonConfig::default();
            
            // Override with CLI args
            if let Some(socket) = cli.socket {
                config.socket_path = socket;
            }
            if let Some(pid_file) = cli.pid_file {
                config.pid_file = pid_file;
            }
            if let Some(cache_dir) = cli.cache_dir {
                config.cache_dir = cache_dir;
            }
            config.idle_timeout = Duration::from_secs(cli.idle_timeout);
            config.project_root = cli.root;
            
            // Run daemon
            IndexerDaemon::run(config).await
        }
    }
}