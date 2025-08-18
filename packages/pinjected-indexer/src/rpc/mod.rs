use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::{UnixListener, UnixStream};
use tracing::{debug, error, info};

use crate::index::TypeIndex;

/// JSON-RPC request
#[derive(Debug, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub method: String,
    pub params: Option<Value>,
    pub id: Option<Value>,
}

/// JSON-RPC response
#[derive(Debug, Serialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub result: Option<Value>,
    pub error: Option<JsonRpcError>,
    pub id: Option<Value>,
}

/// JSON-RPC error
#[derive(Debug, Serialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    pub data: Option<Value>,
}

/// RPC server for handling requests
pub struct RpcServer {
    index: Arc<TypeIndex>,
}

impl RpcServer {
    /// Create a new RPC server
    pub fn new(index: Arc<TypeIndex>) -> Self {
        Self { index }
    }
    
    /// Start listening on Unix socket
    pub async fn listen_unix(self: Arc<Self>, socket_path: &std::path::Path) -> Result<()> {
        // Remove old socket if exists
        if socket_path.exists() {
            std::fs::remove_file(socket_path)?;
        }
        
        let listener = UnixListener::bind(socket_path)?;
        info!("RPC server listening on {:?}", socket_path);
        
        loop {
            match listener.accept().await {
                Ok((stream, _)) => {
                    let server = self.clone();
                    tokio::spawn(async move {
                        if let Err(e) = server.handle_connection(stream).await {
                            error!("Error handling connection: {}", e);
                        }
                    });
                }
                Err(e) => {
                    error!("Failed to accept connection: {}", e);
                }
            }
        }
    }
    
    /// Handle a single connection
    async fn handle_connection(&self, stream: UnixStream) -> Result<()> {
        let (reader, mut writer) = stream.into_split();
        let mut reader = BufReader::new(reader);
        let mut line = String::new();
        
        while reader.read_line(&mut line).await? > 0 {
            debug!("Received request: {}", line.trim());
            
            // Parse request
            let request: JsonRpcRequest = match serde_json::from_str(&line) {
                Ok(req) => req,
                Err(e) => {
                    let response = JsonRpcResponse {
                        jsonrpc: "2.0".to_string(),
                        result: None,
                        error: Some(JsonRpcError {
                            code: -32700,
                            message: format!("Parse error: {}", e),
                            data: None,
                        }),
                        id: None,
                    };
                    let response_str = serde_json::to_string(&response)?;
                    writer.write_all(response_str.as_bytes()).await?;
                    writer.write_all(b"\n").await?;
                    writer.flush().await?;
                    line.clear();
                    continue;
                }
            };
            
            // Process request
            let response = self.process_request(request).await;
            
            // Send response
            let response_str = serde_json::to_string(&response)?;
            writer.write_all(response_str.as_bytes()).await?;
            writer.write_all(b"\n").await?;
            writer.flush().await?;
            
            line.clear();
        }
        
        Ok(())
    }
    
    /// Process a JSON-RPC request
    async fn process_request(&self, request: JsonRpcRequest) -> JsonRpcResponse {
        let result = match request.method.as_str() {
            "ping" => Ok(json!({"status": "ok"})),
            "find_iproxy_entrypoints" => self.find_iproxy_entrypoints(request.params),
            "find_entrypoints" => self.find_iproxy_entrypoints(request.params), // Legacy support
            "get_stats" => self.get_stats(),
            "query_type" => self.find_iproxy_entrypoints(request.params), // Legacy support
            _ => Err(JsonRpcError {
                code: -32601,
                message: format!("Method not found: {}", request.method),
                data: None,
            }),
        };
        
        match result {
            Ok(value) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                result: Some(value),
                error: None,
                id: request.id,
            },
            Err(error) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                result: None,
                error: Some(error),
                id: request.id,
            },
        }
    }
    
    /// Find IProxy[T] compatible @injected functions for a type
    fn find_iproxy_entrypoints(&self, params: Option<Value>) -> Result<Value, JsonRpcError> {
        let params = params.ok_or_else(|| JsonRpcError {
            code: -32602,
            message: "Invalid params: missing params".to_string(),
            data: None,
        })?;
        
        let type_name = params["type_name"]
            .as_str()
            .ok_or_else(|| JsonRpcError {
                code: -32602,
                message: "Invalid params: missing type_name".to_string(),
                data: None,
            })?;
        
        let entries = self.index.query_type(type_name);
        Ok(json!(entries))
    }
    
    /// Get index statistics
    fn get_stats(&self) -> Result<Value, JsonRpcError> {
        let stats = self.index.get_stats();
        Ok(json!(stats))
    }
    
    /// Query type (deprecated alias for find_iproxy_entrypoints)
    fn query_type(&self, params: Option<Value>) -> Result<Value, JsonRpcError> {
        self.find_iproxy_entrypoints(params)
    }
}